"""API REST para cuentas de acceso a la plataforma (auth.User)."""
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PerfilPlataforma
from .modulos_plataforma import MODULOS_PLATAFORMA
from .permisos import SoloAdministrador
from .serializers import (
    ROLES_PLATAFORMA,
    UsuarioPlataformaSerializer,
    UsuarioPlataformaWriteSerializer,
    _es_ultimo_admin,
    actualizar_usuario_plataforma,
    crear_usuario_plataforma,
)


class UsuarioPlataformaViewSet(viewsets.ModelViewSet):
    """Gestión de cuentas de login — solo Administrador."""

    permission_classes = [SoloAdministrador]
    queryset = User.objects.all().order_by("username")
    search_fields = [
        "username", "first_name", "last_name", "email", "perfil_plataforma__area",
    ]
    filterset_fields = ["is_active"]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UsuarioPlataformaWriteSerializer
        return UsuarioPlataformaSerializer

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("perfil_plataforma")
            .prefetch_related("groups")
        )
        area = self.request.query_params.get("area", "").strip()
        rol = self.request.query_params.get("rol", "").strip()
        if area:
            qs = qs.filter(perfil_plataforma__area__icontains=area)
        if rol:
            qs = qs.filter(groups__name=rol)
        return qs.distinct()

    def _verificar_puede_gestionar(self, objetivo):
        actor = self.request.user
        if objetivo.is_superuser and not actor.is_superuser:
            return Response(
                {"detail": "Solo un superusuario puede modificar otra cuenta de superusuario."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def _responder(self, user, code=status.HTTP_200_OK):
        user = (
            User.objects.select_related("perfil_plataforma")
            .prefetch_related("groups")
            .get(pk=user.pk)
        )
        return Response(UsuarioPlataformaSerializer(user).data, status=code)

    @action(detail=False, methods=["get"])
    def meta(self, request):
        areas = list(
            PerfilPlataforma.objects.exclude(area="")
            .values_list("area", flat=True)
            .distinct()
            .order_by("area")
        )
        return Response({"roles": list(ROLES_PLATAFORMA), "areas": areas, "modulos": list(MODULOS_PLATAFORMA)})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        ser = UsuarioPlataformaWriteSerializer(
            data=request.data, context={"view": self, "instance": None},
        )
        ser.is_valid(raise_exception=True)
        user = crear_usuario_plataforma(dict(ser.validated_data))
        return self._responder(user, status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        bloqueo = self._verificar_puede_gestionar(user)
        if bloqueo:
            return bloqueo
        parcial = kwargs.pop("partial", False)
        ser = UsuarioPlataformaWriteSerializer(
            data=request.data,
            partial=parcial,
            context={"view": self, "instance": user},
        )
        ser.is_valid(raise_exception=True)
        actualizar_usuario_plataforma(user, dict(ser.validated_data))
        return self._responder(user)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        bloqueo = self._verificar_puede_gestionar(user)
        if bloqueo:
            return bloqueo
        if user.pk == request.user.pk:
            return Response(
                {"detail": "No puede eliminar su propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _es_ultimo_admin(user):
            return Response(
                {"detail": "No puede eliminar al último Administrador activo."},
                status=status.HTTP_409_CONFLICT,
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

"""
Permisos basados en roles (grupos de Django) para el SGSI SUIIN.

Roles:
  - Consultor:      solo lectura.
  - Dinamizador:    lectura + crear/editar activos, diagramas y hoja de vida.
  - Administrador:  control total (incluye eliminar y gestionar catalogos).

Los superusuarios tienen siempre control total.

Política de lectura (Ola 1 — opción C del roadmap de seguridad):
  KPIs agregados públicos en vistas marcadas explícitamente con AllowAny
  (p. ej. /api/dashboard-ejecutivo/). El resto del API exige sesión
  autenticada, aunque sea Consultor en modo solo lectura.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

ROL_CONSULTOR = "Consultor"
ROL_DINAMIZADOR = "Dinamizador"
ROL_ADMIN = "Administrador"


def roles_de(user):
    # No usar solo is_authenticated: en subpeticiones nginx (auth_request) el
    # usuario se reconstituye desde _auth_user_id y sigue siendo un User válido.
    if user is None or not getattr(user, "pk", None):
        return set()
    if user.is_superuser:
        return {ROL_CONSULTOR, ROL_DINAMIZADOR, ROL_ADMIN}
    return set(user.groups.values_list("name", flat=True))


class RolPermiso(BasePermission):
    """
    Lectura: cualquier usuario autenticado (Consultor incluido).
    Escritura (POST/PUT/PATCH): Dinamizador o Administrador.
    Eliminacion (DELETE): solo Administrador.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        roles = roles_de(request.user)
        if request.method == "DELETE":
            return ROL_ADMIN in roles
        return bool(roles & {ROL_DINAMIZADOR, ROL_ADMIN})


class SoloAdministrador(BasePermission):
    """Solo Administrador o superusuario — p. ej. auditoría unificada."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return user_es_admin(request.user)


def user_es_admin(user):
    if user.is_superuser:
        return True
    return ROL_ADMIN in roles_de(user)

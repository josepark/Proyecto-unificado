# -*- coding: utf-8 -*-
"""
Verificación del JWT de plataforma emitido por el Inventario (ver
inventario/inventario/jwt_plataforma.py en ese proyecto).

Se valida la firma localmente con JWT_SHARED_SECRET — riesgos NO llama de
vuelta al inventario en cada petición (eso lo haría depender de que el
inventario esté arriba para que riesgos funcione, incluso para operaciones
que no lo necesitan). El usuario se aprovisiona en la base de datos de
riesgos "just-in-time" la primera vez que se ve su JWT (mismo username que en
el inventario), y sus roles (Consultor/Dinamizador/Administrador, definidos
allá) se usan aquí para decidir permisos de escritura — ver
RolPlataformaOEscrituraLibre en este mismo módulo.

Sin JWT_SHARED_SECRET configurado, esta autenticación queda inactiva sin
error (devuelve None en vez de fallar) — el login por token propio de
riesgos sigue funcionando igual, para cuando el módulo corre de forma
independiente sin el resto de la plataforma.
"""
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .jwt_version_inventario import jwt_version_vigente

ROLES_CON_ESCRITURA = {"Dinamizador", "Administrador"}

User = get_user_model()


class JWTPlataformaAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # deja que TokenAuthentication (u otra) lo intente

        if not settings.JWT_SHARED_SECRET:
            return None  # JWT de plataforma no habilitado en este despliegue

        token = auth_header[len("Bearer "):].strip()
        try:
            payload = jwt.decode(
                token, settings.JWT_SHARED_SECRET, algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("El token de sesión expiró — vuelva a iniciar sesión.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Token de sesión inválido.")

        username = payload.get("username")
        if not username:
            raise exceptions.AuthenticationFailed("Token de sesión sin usuario.")

        roles = payload.get("roles", [])
        modulos = payload.get("modulos")
        if modulos is not None and "riesgos" not in modulos:
            raise exceptions.AuthenticationFailed(
                "Su cuenta no tiene acceso al módulo de Gestión de Riesgos.")

        ver_token = payload.get("ver", 0)
        ver_actual = jwt_version_vigente(username)
        if ver_actual is not None and ver_token < ver_actual:
            raise exceptions.AuthenticationFailed(
                "El token de sesión fue revocado — vuelva a iniciar sesión.")

        user, _ = User.objects.get_or_create(username=username)
        # is_staff se deriva del rol de plataforma en cada request — si a alguien
        # le retiran el rol Administrador en el inventario, pierde acceso al
        # admin de riesgos en su siguiente petición, sin paso manual aparte.
        es_admin = "Administrador" in roles
        if user.is_staff != es_admin:
            user.is_staff = es_admin
            user.save(update_fields=["is_staff"])

        return (user, payload)

    def authenticate_header(self, request):
        return "Bearer"


class EscrituraSegunRolDePlataforma(BasePermission):
    """
    Lectura: siempre libre (igual que antes).
    Escritura: si el usuario se autenticó con el JWT de plataforma, exige rol
    Dinamizador o Administrador (mismo criterio que ya usa el inventario para
    RBAC — ver permisos.py:RolPermiso allá). Si se autenticó con el token
    propio de riesgos (modo independiente, sin plataforma), el comportamiento
    NO cambia: cualquier usuario autenticado puede escribir, como siempre.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if isinstance(request.auth, dict):  # vino del JWT de plataforma
            return bool(set(request.auth.get("roles", [])) & ROLES_CON_ESCRITURA)
        return True  # token propio de riesgos — comportamiento sin cambios

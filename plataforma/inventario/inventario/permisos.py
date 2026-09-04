"""
Permisos basados en roles (grupos de Django) para el SGSI SUIIN.

Roles:
  - Consultor:      solo lectura.
  - Dinamizador:    lectura + crear/editar activos, diagramas y hoja de vida.
  - Administrador:  control total (incluye eliminar y gestionar catalogos).

Los superusuarios tienen siempre control total.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

ROL_CONSULTOR = "Consultor"
ROL_DINAMIZADOR = "Dinamizador"
ROL_ADMIN = "Administrador"


def roles_de(user):
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {ROL_CONSULTOR, ROL_DINAMIZADOR, ROL_ADMIN}
    return set(user.groups.values_list("name", flat=True))


class RolPermiso(BasePermission):
    """
    Lectura: cualquier usuario (incluye anonimo, para el tablero de consulta).
    Escritura (POST/PUT/PATCH): Dinamizador o Administrador.
    Eliminacion (DELETE): solo Administrador.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        roles = roles_de(request.user)
        if request.method == "DELETE":
            return ROL_ADMIN in roles
        return bool(roles & {ROL_DINAMIZADOR, ROL_ADMIN})

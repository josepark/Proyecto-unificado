"""Módulos (proyectos) de la plataforma unificada SUIIN-SGSI."""
from .permisos import ROL_ADMIN, user_es_admin

MODULO_INVENTARIO = "inventario"
MODULO_RBAC = "rbac"
MODULO_RIESGOS = "riesgos"

MODULOS_PLATAFORMA = (MODULO_INVENTARIO, MODULO_RBAC, MODULO_RIESGOS)

ETIQUETAS_MODULO = {
    MODULO_INVENTARIO: "Inventario de activos",
    MODULO_RBAC: "Matriz RBAC",
    MODULO_RIESGOS: "Gestión de Riesgos y PTR",
}

# Rutas API del Inventario accesibles aunque el usuario no tenga módulo inventario
# (sesión, login, puerta RBAC, JWT para otros módulos, gestión de cuentas).
RUTAS_API_SIN_MODULO_INVENTARIO = (
    "/api/sesion/",
    "/api/auth/login/",
    "/api/auth-rbac/",
    "/api/token-jwt/",
    "/api/usuarios-plataforma/",
    "/api/auth/jwt-version/",
)


def normalizar_modulos(valores):
    """Lista única y ordenada de módulos válidos."""
    if not valores:
        return []
    vistos = set()
    resultado = []
    for m in valores:
        if m in MODULOS_PLATAFORMA and m not in vistos:
            vistos.add(m)
            resultado.append(m)
    return resultado


def modulos_de(user):
    """Módulos permitidos para el usuario. Vacío en perfil = acceso a todos (compat)."""
    if user is None or not getattr(user, "pk", None):
        return []
    if user.is_superuser or user_es_admin(user):
        return list(MODULOS_PLATAFORMA)
    perfil = getattr(user, "perfil_plataforma", None)
    if perfil is None:
        from .models import PerfilPlataforma
        perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    raw = perfil.modulos_acceso or []
    normalizados = normalizar_modulos(raw)
    return normalizados if normalizados else list(MODULOS_PLATAFORMA)


def tiene_modulo(user, modulo):
    return modulo in modulos_de(user)


def ruta_exenta_modulo_inventario(path):
    return any(path.startswith(prefix) for prefix in RUTAS_API_SIN_MODULO_INVENTARIO)

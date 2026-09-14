"""Espacios de datos por usuario — aísla el inventario de cuentas nuevas."""

ESPACIO_ORGANIZACION = "organizacion"

# Cuentas de demostración / administración que comparten el inventario de ejemplo.
USUARIOS_ESPACIO_ORGANIZACION = frozenset({
    "admin",
    "dinamizador",
    "consultor",
})


def get_espacio_organizacion():
    from .models import EspacioDatos

    espacio, _ = EspacioDatos.objects.get_or_create(
        codigo=ESPACIO_ORGANIZACION,
        defaults={
            "nombre": "Organización CRIC (demostración)",
            "es_compartido": True,
        },
    )
    return espacio


def crea_espacio_personal(user):
    from .models import EspacioDatos

    codigo = f"usuario-{user.username}"[:60]
    espacio, _ = EspacioDatos.objects.get_or_create(
        codigo=codigo,
        defaults={
            "nombre": f"Espacio de {user.get_full_name() or user.username}",
            "es_compartido": False,
            "propietario": user,
        },
    )
    return espacio


def usuario_usa_espacio_organizacion(user):
    """Solo cuentas demo explícitas (y superusuario) comparten el inventario de ejemplo."""
    if user.is_superuser:
        return True
    return user.username.lower() in USUARIOS_ESPACIO_ORGANIZACION


def _reparar_espacio_demo_indevido(user, perfil):
    """Usuarios no demo que quedaron en 'organizacion' (p. ej. migración 0016) → espacio personal."""
    import sys

    if "test" in sys.argv:
        return perfil.espacio_datos
    espacio = perfil.espacio_datos
    if (
        espacio
        and espacio.codigo == ESPACIO_ORGANIZACION
        and not usuario_usa_espacio_organizacion(user)
    ):
        espacio = crea_espacio_personal(user)
        perfil.espacio_datos = espacio
        perfil.save(update_fields=["espacio_datos"])
    return perfil.espacio_datos


def espacio_datos_de(user, crear_si_falta=True):
    if user is None or not getattr(user, "pk", None):
        return None
    perfil = getattr(user, "perfil_plataforma", None)
    if perfil is None:
        from .models import PerfilPlataforma

        perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    if perfil.espacio_datos_id:
        return _reparar_espacio_demo_indevido(user, perfil)
    if not crear_si_falta:
        return None
    espacio = (
        get_espacio_organizacion()
        if usuario_usa_espacio_organizacion(user)
        else crea_espacio_personal(user)
    )
    perfil.espacio_datos = espacio
    perfil.save(update_fields=["espacio_datos"])
    return espacio


def activos_espacio_organizacion():
    from .models import Activo

    return Activo.objects.filter(espacio__codigo=ESPACIO_ORGANIZACION)


def queryset_activos(request):
    from .models import Activo
    from .permisos import es_peticion_servicio_interno

    if es_peticion_servicio_interno(request):
        codigo = (request.headers.get("X-Espacio-Datos") or "").strip()
        if codigo:
            return Activo.objects.filter(espacio__codigo=codigo)
        return Activo.objects.filter(espacio__codigo=ESPACIO_ORGANIZACION)
    from .permisos import usuario_efectivo

    user = usuario_efectivo(request)
    if user is None or not getattr(user, "is_authenticated", False):
        return Activo.objects.none()
    espacio = espacio_datos_de(user)
    if espacio is None:
        return Activo.objects.none()
    return Activo.objects.filter(espacio=espacio)


def asignar_espacio_usuario_nuevo(user):
    """Espacio personal vacío para cuentas creadas desde la interfaz."""
    from .models import PerfilPlataforma

    perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    if perfil.espacio_datos_id:
        return perfil.espacio_datos
    espacio = crea_espacio_personal(user)
    perfil.espacio_datos = espacio
    perfil.save(update_fields=["espacio_datos"])
    return espacio


def codigo_espacio_request(request):
    """Slug del espacio del usuario autenticado (p. ej. organizacion, usuario-pruebas)."""
    from .permisos import usuario_efectivo

    user = usuario_efectivo(request) if request is not None else None
    if user is None or not getattr(user, "is_authenticated", False):
        return ESPACIO_ORGANIZACION
    espacio = espacio_datos_de(user)
    return espacio.codigo if espacio else ESPACIO_ORGANIZACION

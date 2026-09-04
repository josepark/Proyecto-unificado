from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from simple_history.signals import post_create_historical_record

from .models import RegistroAcceso
from . import integridad

_ENTIDADES_CON_INTEGRIDAD = (
    "Activo", "ActivoInfraestructura", "SistemaInformacion",
    "EquipoComputo", "Datacenter",
)
_ACCION_POR_TIPO_HISTORIAL = {"+": "ALTA", "~": "MODIFICACION", "-": "ELIMINACION"}


def _identificar(instance):
    """Identificador y nombre legibles para el detalle del registro de
    integridad — sea el propio Activo o uno de sus modelos de detalle 1:1
    (que no tienen id_activo/nombre propios, solo vía su FK 'activo')."""
    if hasattr(instance, "id_activo"):
        return instance.id_activo, instance.nombre
    if hasattr(instance, "activo_id"):
        try:
            a = instance.activo
            return a.id_activo, a.nombre
        except Exception:
            return f"activo #{instance.activo_id}", ""
    if hasattr(instance, "codigo"):
        return instance.codigo, getattr(instance, "nombre", "")
    return str(instance.pk), ""


@receiver(post_create_historical_record)
def registrar_integridad_historica(sender, history_instance, instance,
                                   history_user=None, **kwargs):
    """Se dispara cada vez que django-simple-history crea una fila de
    historial (en creación, edición o eliminación) de cualquier modelo con
    HistoricalRecords(). Solo nos interesan los cinco modelos del SGSI
    (no HistoricalUser ni nada de terceros); para esos, se agrega una fila
    a la cadena de integridad con lo mínimo necesario para detectar
    alteraciones — el detalle campo por campo ya vive en el propio
    historial de simple_history, no se duplica aquí."""
    modelo = instance.__class__.__name__
    if modelo not in _ENTIDADES_CON_INTEGRIDAD:
        return
    accion = _ACCION_POR_TIPO_HISTORIAL.get(history_instance.history_type, "MODIFICACION")
    responsable = history_user.get_username() if history_user else "sistema"
    identificador, nombre = _identificar(instance)

    if accion == "MODIFICACION":
        campos = "N/D"
        try:
            prev = history_instance.prev_record
            if prev:
                delta = history_instance.diff_against(prev)
                if delta.changes:
                    campos = ", ".join(c.field for c in delta.changes)
        except Exception:
            pass
        detalle = f"{modelo} {identificador} ({nombre}) modificado. Campos: {campos}"
    elif accion == "ALTA":
        detalle = f"{modelo} {identificador} ({nombre}) creado"
    else:
        detalle = f"{modelo} {identificador} ({nombre}) eliminado"

    integridad.registrar(modelo, accion, detalle, responsable)


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    RegistroAcceso.objects.create(usuario=user.get_username(),
                                  accion="LOGIN", ip=_ip(request))


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        RegistroAcceso.objects.create(usuario=user.get_username(),
                                      accion="LOGOUT", ip=_ip(request))

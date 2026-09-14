"""Metadatos del inventario para la SPA — fuente única de clases, enums y colores."""
from .models import Activo, ClaseActivo, Datacenter

COLORES_TIPO_DC = {
    "PRIN": "#3fa87f",
    "MINI": "#c9a94e",
    "DR": "#8b5cf6",
    "CLOUD": "#0ea5e9",
}


def _choices(model, field_name):
    field = model._meta.get_field(field_name)
    return [{"codigo": c[0], "nombre": c[1]} for c in field.choices]


def catalogo_clases_activo(solo_activas=True):
    qs = ClaseActivo.objects.all()
    if solo_activas:
        qs = qs.filter(activo=True)
    return list(qs.order_by("orden", "codigo").values(
        "id", "codigo", "nombre", "prefijo_id", "color", "orden",
        "activo", "modelo_detalle", "detalle_schema",
    ))


def meta_inventario():
    clases = catalogo_clases_activo()
    return {
        "clases": clases,
        "colores_clase": {c["codigo"]: c["color"] for c in clases},
        "datacenter": {
            "tipos": _choices(Datacenter, "tipo"),
            "tiers": _choices(Datacenter, "nivel_tier"),
            "colores_tipo": COLORES_TIPO_DC,
        },
        "activo": {
            "clasificacion_si": _choices(Activo, "clasificacion_si"),
            "nivel_riesgo": _choices(Activo, "nivel_riesgo"),
            "estado": _choices(Activo, "estado"),
            "ciclo_vida": _choices(Activo, "ciclo_vida"),
            "nivel_cid": _choices(Activo, "confidencialidad"),
        },
    }

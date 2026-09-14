from django.db import migrations

MAPEO = {
    "SIN CONTROL": "PENDIENTE",
    "SIN_CONTROL": "PENDIENTE",
    "PENDIENTE": "PENDIENTE",
    "EN PROGRESO": "EN_PROGRESO",
    "EN_PROGRESO": "EN_PROGRESO",
    "CERRADO": "CERRADO",
    "MITIGADO": "CERRADO",
    "ACEPTADO": "ACEPTADO",
}


def poblar_estado(apps, schema_editor):
    RiesgoContextual = apps.get_model("riesgos", "RiesgoContextual")
    for r in RiesgoContextual.objects.all():
        nuevo = MAPEO.get((r.estado_actual or "").strip().upper(), "PENDIENTE")
        if r.estado != nuevo:
            r.estado = nuevo
            r.save(update_fields=["estado"])


def revertir(apps, schema_editor):
    pass  # 'estado' es aditivo — no hay nada que deshacer en estado_actual


class Migration(migrations.Migration):

    dependencies = [
        ("riesgos", "0009_historicalriesgocontextual_estado_and_more"),
    ]

    operations = [
        migrations.RunPython(poblar_estado, revertir),
    ]

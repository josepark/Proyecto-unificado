from django.db import migrations


def backfill_importado_en(apps, schema_editor):
    """
    Los registros que ya existían antes de agregar `importado_en` no tienen forma
    de saber cuándo los tocó el importador por última vez. Como (a la fecha de esta
    migración) todos los datos reales del sistema vienen de una importación de
    Excel y no se han editado manualmente, se establece `importado_en = actualizado_en`
    para reflejar correctamente que están "al día" con su última importación — de lo
    contrario, `fue_editado_tras_importacion()` los trataría como protegidos
    (editados manualmente) desde el primer momento, y una reimportación legítima de
    datos corregidos en el Excel nunca podría actualizarlos.

    Si esta migración corre sobre una base de datos que YA tiene ediciones manuales
    reales hechas antes de este cambio, el efecto es conservador en la dirección
    seguridad-primero: esos registros quedan marcados como "recién importados" y
    una futura reimportación SÍ podría sobrescribirlos una vez. Dado que este campo
    se agrega en el mismo despliegue que introduce la protección, no hay ninguna
    ventana real donde eso pueda ocurrir con datos ya editados por un usuario.
    """
    modelos = [
        "Activo", "Vulnerabilidad", "RiesgoActivo", "RiesgoContextual",
        "CampanaRedTeam", "PlanTratamientoRiesgos", "AccionTratamiento",
    ]
    for nombre_modelo in modelos:
        Modelo = apps.get_model("riesgos", nombre_modelo)
        for obj in Modelo.objects.filter(importado_en__isnull=True):
            obj.importado_en = obj.actualizado_en
            obj.save(update_fields=["importado_en"])


def revertir(apps, schema_editor):
    pass  # no hay nada que deshacer de forma significativa


class Migration(migrations.Migration):

    dependencies = [
        ("riesgos", "0005_acciontratamiento_importado_en_activo_importado_en_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_importado_en, revertir),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("riesgos", "0015_acciontratamiento_origen_riesgo_contextual_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalplantratamientoriesgos",
            name="estado_plan",
            field=models.CharField(
                choices=[("ACTIVO", "Activo"), ("ARCHIVADO", "Archivado"), ("CERRADO", "Cerrado")],
                default="ACTIVO",
                help_text="Planes archivados o cerrados quedan fuera del selector operativo pero conservan historial y evidencia.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="plantratamientoriesgos",
            name="estado_plan",
            field=models.CharField(
                choices=[("ACTIVO", "Activo"), ("ARCHIVADO", "Archivado"), ("CERRADO", "Cerrado")],
                default="ACTIVO",
                help_text="Planes archivados o cerrados quedan fuera del selector operativo pero conservan historial y evidencia.",
                max_length=20,
            ),
        ),
    ]

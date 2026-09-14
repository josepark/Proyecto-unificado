# Generated manually — aislamiento por espacio_codigo
from django.db import migrations, models


ESPACIO = "organizacion"


class Migration(migrations.Migration):

    dependencies = [
        ("riesgos", "0016_plantratamientoriesgos_estado_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="activo",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="historicalactivo",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="campanaredteam",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="historicalcampanaredteam",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="riesgocontextual",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="historicalriesgocontextual",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="plantratamientoriesgos",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AddField(
            model_name="historicalplantratamientoriesgos",
            name="espacio_codigo",
            field=models.CharField(db_index=True, default=ESPACIO, max_length=60),
        ),
        migrations.AlterField(
            model_name="activo",
            name="id_activo",
            field=models.CharField(help_text="Ej. RED-012, SI-06", max_length=20),
        ),
        migrations.AlterField(
            model_name="activo",
            name="inventario_id",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="PK del activo correspondiente en la Plataforma SUIIN (Inventario) — "
                "null si aún no está vinculado. Ver comando sincronizar_activos_inventario.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="campanaredteam",
            name="nombre",
            field=models.CharField(help_text="Ej. SUIIN-CENSO", max_length=100),
        ),
        migrations.AlterField(
            model_name="riesgocontextual",
            name="id_riesgo_contextual",
            field=models.CharField(help_text="Ej. RC-03", max_length=10),
        ),
        migrations.AlterField(
            model_name="plantratamientoriesgos",
            name="referencia",
            field=models.CharField(help_text="Ej. SUIIN-SGSI-PTR-001 v1.0", max_length=50),
        ),
        migrations.AddConstraint(
            model_name="activo",
            constraint=models.UniqueConstraint(
                fields=("espacio_codigo", "id_activo"),
                name="uniq_activo_espacio_id",
            ),
        ),
        migrations.AddConstraint(
            model_name="activo",
            constraint=models.UniqueConstraint(
                condition=models.Q(("inventario_id__isnull", False)),
                fields=("espacio_codigo", "inventario_id"),
                name="uniq_activo_espacio_inventario",
            ),
        ),
        migrations.AddConstraint(
            model_name="campanaredteam",
            constraint=models.UniqueConstraint(
                fields=("espacio_codigo", "nombre"),
                name="uniq_campana_espacio_nombre",
            ),
        ),
        migrations.AddConstraint(
            model_name="riesgocontextual",
            constraint=models.UniqueConstraint(
                fields=("espacio_codigo", "id_riesgo_contextual"),
                name="uniq_rc_espacio_codigo",
            ),
        ),
        migrations.AddConstraint(
            model_name="plantratamientoriesgos",
            constraint=models.UniqueConstraint(
                fields=("espacio_codigo", "referencia"),
                name="uniq_ptr_espacio_referencia",
            ),
        ),
    ]

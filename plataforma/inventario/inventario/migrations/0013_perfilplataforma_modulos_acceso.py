from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0012_perfilplataforma_area"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilplataforma",
            name="modulos_acceso",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Proyectos de la plataforma: inventario, rbac, riesgos. Vacío = todos.",
                verbose_name="Módulos permitidos",
            ),
        ),
    ]

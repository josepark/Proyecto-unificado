# Quitar choices fijos en activo.clase — el catálogo ClaseActivo es la fuente de verdad.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0008_claseactivo_detalle_extra"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activo",
            name="clase",
            field=models.CharField(help_text="Código de ClaseActivo (catálogo dinámico)", max_length=6),
        ),
        migrations.AlterField(
            model_name="historicalactivo",
            name="clase",
            field=models.CharField(help_text="Código de ClaseActivo (catálogo dinámico)", max_length=6),
        ),
    ]

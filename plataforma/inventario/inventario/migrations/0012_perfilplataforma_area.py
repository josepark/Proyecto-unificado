from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0011_ola2_rack_sistema_rbac"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilplataforma",
            name="area",
            field=models.CharField(
                blank=True,
                help_text="Dependencia o área del CRIC/SUIIN a la que pertenece el usuario.",
                max_length=120,
                verbose_name="Área organizacional",
            ),
        ),
    ]

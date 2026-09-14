from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0018_alter_historicalactivo_id_activo"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilplataforma",
            name="mfa_habilitado",
            field=models.BooleanField(default=False, verbose_name="MFA TOTP activo"),
        ),
        migrations.AddField(
            model_name="perfilplataforma",
            name="mfa_totp_secreto",
            field=models.CharField(blank=True, max_length=64, verbose_name="Secreto TOTP (interno)"),
        ),
    ]

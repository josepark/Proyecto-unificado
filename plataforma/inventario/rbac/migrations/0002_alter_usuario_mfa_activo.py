from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='mfa_activo',
            field=models.CharField(default='No', max_length=50),
        ),
    ]

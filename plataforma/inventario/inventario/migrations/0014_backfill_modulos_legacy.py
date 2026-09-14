from django.db import migrations


def asignar_modulos_legacy(apps, schema_editor):
    """Usuarios existentes sin proyectos explícitos conservan acceso a los tres módulos."""
    Perfil = apps.get_model("inventario", "PerfilPlataforma")
    todos = ["inventario", "rbac", "riesgos"]
    for perfil in Perfil.objects.all():
        if not perfil.modulos_acceso:
            perfil.modulos_acceso = todos
            perfil.save(update_fields=["modulos_acceso"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0013_perfilplataforma_modulos_acceso"),
    ]

    operations = [
        migrations.RunPython(asignar_modulos_legacy, migrations.RunPython.noop),
    ]

# Corrige perfiles que quedaron en espacio "organizacion" por ser Administrador
# (0016 asignaba org a todo el grupo Administrador). Solo admin/dinamizador/consultor
# deben compartir el inventario demo.

from django.db import migrations

ESPACIO_ORGANIZACION = "organizacion"
USUARIOS_DEMO = frozenset({"admin", "dinamizador", "consultor"})


def corregir_espacios_no_demo(apps, schema_editor):
    EspacioDatos = apps.get_model("inventario", "EspacioDatos")
    PerfilPlataforma = apps.get_model("inventario", "PerfilPlataforma")

    org = EspacioDatos.objects.filter(codigo=ESPACIO_ORGANIZACION).first()
    if org is None:
        return

    for perfil in PerfilPlataforma.objects.select_related("user").filter(espacio_datos_id=org.id):
        user = perfil.user
        if user.is_superuser:
            continue
        if user.username.lower() in USUARIOS_DEMO:
            continue
        codigo = f"usuario-{user.username}"[:60]
        personal, _ = EspacioDatos.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": f"Espacio de {user.username}",
                "es_compartido": False,
                "propietario_id": user.id,
            },
        )
        perfil.espacio_datos = personal
        perfil.save(update_fields=["espacio_datos"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0016_espacio_datos_por_usuario"),
    ]

    operations = [
        migrations.RunPython(corregir_espacios_no_demo, migrations.RunPython.noop),
    ]

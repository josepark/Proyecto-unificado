"""Utilidades compartidas por la suite de tests del Inventario."""

from django.test import Client as DjangoTestClient

from .modulos_plataforma import MODULOS_PLATAFORMA


def asegurar_modulos_plataforma(user, modulos=None):
    """Asigna módulos al perfil; evita 403 en tests que omiten modulos_acceso."""
    from .models import PerfilPlataforma

    if user is None or not getattr(user, "pk", None):
        return
    perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    if modulos is not None:
        perfil.modulos_acceso = list(modulos)
        perfil.save(update_fields=["modulos_acceso"])
        user._modulos_configurados = True
    elif not perfil.modulos_acceso and not getattr(user, "_modulos_configurados", False):
        perfil.modulos_acceso = list(MODULOS_PLATAFORMA)
        perfil.save(update_fields=["modulos_acceso"])
    if not getattr(user, "_espacio_configurado", False) and not perfil.espacio_datos_id:
        from .espacio_datos import get_espacio_organizacion

        perfil.espacio_datos = get_espacio_organizacion()
        perfil.save(update_fields=["espacio_datos"])


def activar_helpers_test():
    """Parchea Client.force_login para rellenar modulos_acceso en tests."""
    if getattr(DjangoTestClient.force_login, "_inventario_modulos", False):
        return
    original = DjangoTestClient.force_login

    def force_login(self, user, backend=None):
        asegurar_modulos_plataforma(user)
        return original(self, user, backend)

    force_login._inventario_modulos = True
    DjangoTestClient.force_login = force_login

import pytest
from django.core.management import call_command
from riesgos.models import ControlISO27001

pytestmark = pytest.mark.django_db


class TestCargarCatalogoIso27001:
    def test_siembra_exactamente_93_controles(self):
        call_command("cargar_catalogo_iso27001")
        assert ControlISO27001.objects.count() == 93

    def test_distribucion_por_categoria(self):
        call_command("cargar_catalogo_iso27001")
        assert ControlISO27001.objects.filter(categoria="ORGANIZACIONAL").count() == 37
        assert ControlISO27001.objects.filter(categoria="PERSONAS").count() == 8
        assert ControlISO27001.objects.filter(categoria="FISICO").count() == 14
        assert ControlISO27001.objects.filter(categoria="TECNOLOGICO").count() == 34

    def test_es_idempotente(self):
        """Correrlo dos veces no debe duplicar controles."""
        call_command("cargar_catalogo_iso27001")
        call_command("cargar_catalogo_iso27001")
        assert ControlISO27001.objects.count() == 93

    def test_no_pisa_el_estado_ya_configurado_por_el_usuario(self):
        """update_or_create solo actualiza categoria/nombre — aplicable y
        estado_implementacion son ajustes de Jose y no deben resetearse al
        volver a correr el comando (ej. tras actualizar a una versión futura
        del estándar)."""
        call_command("cargar_catalogo_iso27001")
        control = ControlISO27001.objects.get(codigo="8.8")
        control.estado_implementacion = "IMPLEMENTADO"
        control.aplicable = False
        control.save()

        call_command("cargar_catalogo_iso27001")

        control.refresh_from_db()
        assert control.estado_implementacion == "IMPLEMENTADO"
        assert control.aplicable is False

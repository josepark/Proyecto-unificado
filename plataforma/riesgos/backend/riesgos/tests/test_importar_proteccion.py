import datetime as dt
import pytest
from django.utils import timezone

from riesgos.models import Activo
from riesgos.management.commands.importar_matrices import Command
from riesgos.sincronizacion import ProtectorSincronizacion

pytestmark = pytest.mark.django_db


class TestFueEditadoTrasImportacion:
    def test_sin_importado_en_y_sin_pk_no_esta_protegido(self):
        """Instancia nueva aún no guardada — no aplica protección (se va a crear)."""
        a = Activo(id_activo="PROT-01", nombre="x", valor=1)
        assert a.fue_editado_tras_importacion() is False

    def test_sin_importado_en_pero_ya_existe_esta_protegido(self, activo):
        """Registro preexistente sin origen de import conocido (ej. creado directo
        desde la app) — se protege por defecto, nunca se asume que es "seguro" de
        sobrescribir."""
        activo.importado_en = None
        activo.save()
        assert activo.fue_editado_tras_importacion() is True

    def test_recien_importado_no_esta_protegido(self, activo):
        ahora = timezone.now()
        activo.importado_en = ahora
        Activo.objects.filter(pk=activo.pk).update(actualizado_en=ahora, importado_en=ahora)
        activo.refresh_from_db()
        assert activo.fue_editado_tras_importacion() is False

    def test_editado_despues_de_importar_esta_protegido(self, activo):
        hace_un_dia = timezone.now() - dt.timedelta(days=1)
        Activo.objects.filter(pk=activo.pk).update(importado_en=hace_un_dia)
        activo.refresh_from_db()
        activo.nombre = "Editado por el analista"
        activo.save()  # actualizado_en (auto_now) queda en "ahora", después de importado_en
        assert activo.fue_editado_tras_importacion() is True


class TestGuardarProtegiendo:
    """Prueba _guardar_protegiendo directamente — no requiere un archivo Excel."""

    def _comando(self, forzar=False):
        cmd = Command()
        cmd.protector = ProtectorSincronizacion(forzar=forzar)
        return cmd

    def test_crea_si_no_existe(self):
        cmd = self._comando()
        obj, protegido = cmd._guardar_protegiendo(
            Activo, filtro={"id_activo": "GP-01"}, defaults={"nombre": "Nuevo", "valor": 1},
            descripcion="GP-01",
        )
        assert protegido is False
        assert cmd.protector.stats["creados"] == 1
        assert obj.importado_en is not None
        assert Activo.objects.filter(id_activo="GP-01").exists()

    def test_actualiza_si_no_fue_editado(self, activo):
        Activo.objects.filter(pk=activo.pk).update(importado_en=timezone.now())
        cmd = self._comando()
        obj, protegido = cmd._guardar_protegiendo(
            Activo, filtro={"id_activo": activo.id_activo},
            defaults={"nombre": "Nombre actualizado por Excel", "valor": activo.valor},
            descripcion=activo.id_activo,
        )
        assert protegido is False
        assert cmd.protector.stats["actualizados"] == 1
        assert obj.nombre == "Nombre actualizado por Excel"

    def test_protege_si_fue_editado_manualmente(self, activo):
        hace_un_dia = timezone.now() - dt.timedelta(days=1)
        Activo.objects.filter(pk=activo.pk).update(importado_en=hace_un_dia)
        activo.refresh_from_db()
        activo.nombre = "Editado a mano"
        activo.save()

        cmd = self._comando()
        obj, protegido = cmd._guardar_protegiendo(
            Activo, filtro={"id_activo": activo.id_activo},
            defaults={"nombre": "El Excel quiere poner esto", "valor": activo.valor},
            descripcion=activo.id_activo,
        )
        assert protegido is True
        assert cmd.protector.stats["protegidos"] == ["Activo " + activo.id_activo]
        assert cmd.protector.stats["actualizados"] == 0
        obj.refresh_from_db()
        assert obj.nombre == "Editado a mano"  # NO se sobrescribió

    def test_forzar_sobrescribe_aunque_este_editado(self, activo):
        hace_un_dia = timezone.now() - dt.timedelta(days=1)
        Activo.objects.filter(pk=activo.pk).update(importado_en=hace_un_dia)
        activo.refresh_from_db()
        activo.nombre = "Editado a mano"
        activo.save()

        cmd = self._comando(forzar=True)
        obj, protegido = cmd._guardar_protegiendo(
            Activo, filtro={"id_activo": activo.id_activo},
            defaults={"nombre": "El Excel gana", "valor": activo.valor},
            descripcion=activo.id_activo,
        )
        assert protegido is False
        assert cmd.protector.stats["actualizados"] == 1
        obj.refresh_from_db()
        assert obj.nombre == "El Excel gana"

    def test_no_se_pierde_como_protegido_dos_veces(self, activo):
        """Confirma que el conteo de protegidos no se duplica ni se resetea entre llamadas."""
        hace_un_dia = timezone.now() - dt.timedelta(days=1)
        Activo.objects.filter(pk=activo.pk).update(importado_en=hace_un_dia)
        activo.refresh_from_db()
        activo.nombre = "x"
        activo.save()

        cmd = self._comando()
        cmd._guardar_protegiendo(Activo, {"id_activo": activo.id_activo}, {"nombre": "y", "valor": 1}, "a")
        cmd._guardar_protegiendo(Activo, {"id_activo": activo.id_activo}, {"nombre": "z", "valor": 1}, "a")
        assert len(cmd.protector.stats["protegidos"]) == 2

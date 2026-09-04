import pytest
from riesgos.models import Activo, Vulnerabilidad, RiesgoActivo

pytestmark = pytest.mark.django_db


class TestRecalculoAutomaticoRiesgoMatriz:
    def test_agregar_vulnerabilidad_critica_eleva_el_riesgo(self, activo):
        assert activo.riesgo_matriz == "BAJO"
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Crítica", probabilidad=5, impacto=5)
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "CRITICO"

    def test_eliminar_la_vulnerabilidad_baja_el_riesgo_de_nuevo(self, activo):
        v = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Crítica", probabilidad=5, impacto=5)
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "CRITICO"

        v.delete()
        activo.refresh_from_db()
        # Sin hallazgos registrados, se conserva el último valor conocido (no hay
        # "downgrade automático a SIN_DATO" — ver docstring de recalcular_riesgo_activo).
        assert activo.riesgo_matriz == "CRITICO"

    def test_toma_el_nivel_maximo_entre_varios_hallazgos(self, activo):
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Baja", probabilidad=1, impacto=1)
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Alta", probabilidad=4, impacto=4)
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "ALTO"

    def test_riesgo_activo_tambien_dispara_recalculo(self, activo):
        assert activo.riesgo_matriz == "BAJO"
        RiesgoActivo.objects.create(
            id_riesgo="RA-SIGTEST", activo=activo, probabilidad=5, impacto=5)
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "CRITICO"

    def test_editar_probabilidad_de_vulnerabilidad_existente_recalcula(self, activo):
        v = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Prueba", probabilidad=1, impacto=1)
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "BAJO"

        v.probabilidad = 5
        v.impacto = 5
        v.save()
        activo.refresh_from_db()
        assert activo.riesgo_matriz == "CRITICO"

    def test_vulnerabilidad_sin_evaluar_no_afecta_el_calculo(self, activo):
        """Una vulnerabilidad técnica sin Prob/Impacto (SIN_DATO) no debe contarse."""
        Vulnerabilidad.objects.create(activo=activo, nombre_vulnerabilidad="Sin evaluar")
        activo.refresh_from_db()
        # No hay hallazgos con nivel definido -> se conserva el valor original importado
        assert activo.riesgo_matriz == "BAJO"

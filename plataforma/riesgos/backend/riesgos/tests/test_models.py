import pytest
from riesgos.models import (
    calcular_nivel, Vulnerabilidad, RiesgoActivo, RiesgoContextual,
    AccionTratamiento, ControlISO27001,
)

pytestmark = pytest.mark.django_db


class TestCalcularNivel:
    """Escala ISO/IEC 27005 usada en toda la matriz: Score = Probabilidad(1-5) x Impacto(1-5)."""

    @pytest.mark.parametrize("score,nivel_esperado", [
        (25, "CRITICO"), (20, "CRITICO"),
        (19, "ALTO"), (12, "ALTO"),
        (11, "MEDIO"), (6, "MEDIO"),
        (5, "BAJO"), (1, "BAJO"),
        (0, "SIN_DATO"),
    ])
    def test_umbrales(self, score, nivel_esperado):
        assert calcular_nivel(score) == nivel_esperado

    def test_none_es_sin_dato(self):
        assert calcular_nivel(None) == "SIN_DATO"


class TestVulnerabilidadScore:
    def test_score_se_calcula_al_guardar(self, activo):
        v = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Prueba", probabilidad=5, impacto=5)
        assert v.score == 25
        assert v.nivel_riesgo == "CRITICO"

    def test_sin_probabilidad_no_calcula_score(self, activo):
        """Vulnerabilidad técnica sin evaluación de riesgo aún (solo el hallazgo OpenVAS)."""
        v = Vulnerabilidad.objects.create(activo=activo, nombre_vulnerabilidad="Sin evaluar")
        assert v.score is None
        assert v.nivel_riesgo == "SIN_DATO"

    def test_actualizar_probabilidad_recalcula_score(self, activo):
        v = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Prueba", probabilidad=2, impacto=2)
        assert v.score == 4 and v.nivel_riesgo == "BAJO"
        v.probabilidad = 5
        v.impacto = 5
        v.save()
        assert v.score == 25 and v.nivel_riesgo == "CRITICO"


class TestRiesgoActivoScore:
    def test_score_y_nivel(self, activo):
        r = RiesgoActivo.objects.create(
            id_riesgo="RA-TEST-01", activo=activo, probabilidad=4, impacto=4)
        assert r.score == 16
        assert r.nivel_riesgo == "ALTO"


class TestRiesgoContextualScore:
    def test_score_y_nivel(self):
        r = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-TEST", escenario_amenaza="Prueba",
            probabilidad=3, impacto=3)
        assert r.score == 9
        assert r.nivel_riesgo == "MEDIO"


class TestAccionTratamiento:
    def test_score_y_nivel(self, plan_tratamiento):
        a = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-TEST-01", descripcion_riesgo="Prueba",
            probabilidad=5, impacto=4, acciones_tratamiento="Mitigar")
        assert a.score == 20
        assert a.nivel_riesgo == "CRITICO"

    def test_estado_cerrado_fuerza_avance_100(self, plan_tratamiento):
        a = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-TEST-02", descripcion_riesgo="Prueba",
            probabilidad=2, impacto=2, acciones_tratamiento="Mitigar", porcentaje_avance=30)
        assert a.porcentaje_avance == 30
        a.estado = "CERRADO"
        a.save()
        assert a.porcentaje_avance == 100

    def test_falso_positivo_tambien_fuerza_avance_100(self, plan_tratamiento):
        a = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-TEST-03", descripcion_riesgo="Prueba",
            probabilidad=2, impacto=2, acciones_tratamiento="Mitigar",
            estado="FALSO_POSITIVO")
        assert a.porcentaje_avance == 100


class TestPlanTratamientoRiesgosAvance:
    def test_avance_global_sin_acciones_es_cero(self, plan_tratamiento):
        assert plan_tratamiento.porcentaje_avance_global == 0

    def test_avance_global_con_acciones_mixtas(self, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-A", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", estado="CERRADO")
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-B", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", estado="PENDIENTE")
        # 1 de 2 cerrada -> 50%
        assert plan_tratamiento.porcentaje_avance_global == 50

    def test_aceptado_cuenta_como_avance_igual_que_cerrado(self, plan_tratamiento):
        """Regresión: ACEPTADO es una disposición válida de un riesgo (ISO 27005),
        no un pendiente — debe sumar al avance igual que CERRADO/FALSO_POSITIVO,
        consistente con ESTADOS_CERRADOS (el mismo criterio que usan las alertas
        de vencimiento para decidir qué ya no cuenta como abierto)."""
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-C", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", estado="ACEPTADO")
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-D", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", estado="PENDIENTE")
        assert plan_tratamiento.porcentaje_avance_global == 50

    def test_todas_aceptadas_da_100_por_ciento(self, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-E", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", estado="ACEPTADO")
        assert plan_tratamiento.porcentaje_avance_global == 100


class TestCampanaRedTeamRiesgosActuales:
    def test_sin_activos_vinculados_da_todo_en_cero(self, campana):
        assert campana.riesgos_actuales_por_nivel == {"CRITICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0}

    def test_cuenta_vulnerabilidades_y_riesgos_de_los_activos_vinculados(self, campana, activo):
        activo.campana_red_team = campana
        activo.save()
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=5, impacto=5)  # CRITICO
        RiesgoActivo.objects.create(
            id_riesgo="RA-CAMP-01", activo=activo, probabilidad=4, impacto=4)  # ALTO

        assert campana.riesgos_actuales_por_nivel == {"CRITICO": 1, "ALTO": 1, "MEDIO": 0, "BAJO": 0}

    def test_no_es_lo_mismo_que_el_campo_historico_congelado(self, campana, activo):
        """El campo importado del Excel (riesgos_criticos, etc.) NO debe cambiar
        solo porque cambien los hallazgos actuales — es una foto del momento de
        la campaña, no un valor en vivo. Ver docstring del campo en models.py."""
        campana.riesgos_criticos = 7
        campana.save()
        activo.campana_red_team = campana
        activo.save()
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=5, impacto=5)

        campana.refresh_from_db()
        assert campana.riesgos_criticos == 7  # sin cambiar
        assert campana.riesgos_actuales_por_nivel["CRITICO"] == 1  # el vivo sí refleja el hallazgo nuevo

    def test_no_cuenta_activos_de_otra_campana(self, campana, activo):
        """Un activo sin vincular a esta campaña no debe sumar a su conteo en vivo."""
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=5, impacto=5)
        assert campana.riesgos_actuales_por_nivel == {"CRITICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0}

    def test_expuesto_en_el_serializer(self, campana, activo):
        from riesgos.serializers import CampanaRedTeamSerializer
        activo.campana_red_team = campana
        activo.save()
        RiesgoActivo.objects.create(id_riesgo="RA-CAMP-02", activo=activo, probabilidad=3, impacto=3)  # score 9 -> MEDIO
        data = CampanaRedTeamSerializer(campana).data
        assert data["riesgos_actuales_por_nivel"]["MEDIO"] == 1


class TestControlISO27001NumeroOrden:
    def test_ordena_numericamente_no_alfabeticamente(self):
        """'5.10' debe ordenar después de '5.9', no antes (como haría orden alfabético)."""
        c1 = ControlISO27001(codigo="5.2")
        c2 = ControlISO27001(codigo="5.10")
        assert c1.numero_orden < c2.numero_orden

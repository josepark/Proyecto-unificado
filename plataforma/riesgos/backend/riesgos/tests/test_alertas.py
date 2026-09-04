import datetime as dt
import pytest
from django.core import mail
from django.core.management import call_command

from riesgos.models import AccionTratamiento, RiesgoActivo, RiesgoContextual

pytestmark = pytest.mark.django_db

HOY = dt.date.today()


class TestPropiedadesVencimientoAccionTratamiento:
    def _accion(self, plan_tratamiento, fecha_limite=None, estado="PENDIENTE"):
        return AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo=f"R-VENC-{fecha_limite}-{estado}",
            descripcion_riesgo="x", probabilidad=1, impacto=1, acciones_tratamiento="x",
            fecha_limite=fecha_limite, estado=estado,
        )

    def test_sin_fecha_limite_no_esta_vencida(self, plan_tratamiento):
        a = self._accion(plan_tratamiento)
        assert a.dias_para_vencer is None
        assert a.esta_vencida is False
        assert a.por_vencer is False

    def test_fecha_pasada_esta_vencida(self, plan_tratamiento):
        a = self._accion(plan_tratamiento, fecha_limite=HOY - dt.timedelta(days=3))
        assert a.dias_para_vencer == -3
        assert a.esta_vencida is True
        assert a.por_vencer is False

    def test_fecha_futura_lejana_no_es_ni_vencida_ni_por_vencer(self, plan_tratamiento):
        a = self._accion(plan_tratamiento, fecha_limite=HOY + dt.timedelta(days=30))
        assert a.esta_vencida is False
        assert a.por_vencer is False

    def test_fecha_dentro_de_7_dias_esta_por_vencer(self, plan_tratamiento):
        a = self._accion(plan_tratamiento, fecha_limite=HOY + dt.timedelta(days=5))
        assert a.por_vencer is True
        assert a.esta_vencida is False

    def test_hoy_mismo_cuenta_como_por_vencer(self, plan_tratamiento):
        a = self._accion(plan_tratamiento, fecha_limite=HOY)
        assert a.por_vencer is True

    @pytest.mark.parametrize("estado", ["CERRADO", "FALSO_POSITIVO", "ACEPTADO"])
    def test_cerrada_nunca_esta_vencida_aunque_la_fecha_haya_pasado(self, plan_tratamiento, estado):
        a = self._accion(plan_tratamiento, fecha_limite=HOY - dt.timedelta(days=10), estado=estado)
        assert a.esta_vencida is False
        assert a.por_vencer is False


class TestPropiedadesVencimientoRiesgoActivo:
    def test_riesgo_activo_vencido(self, activo):
        r = RiesgoActivo.objects.create(
            id_riesgo="RA-VENC-01", activo=activo, probabilidad=1, impacto=1,
            fecha_objetivo=HOY - dt.timedelta(days=1))
        assert r.esta_vencido is True

    def test_riesgo_activo_cerrado_no_cuenta(self, activo):
        r = RiesgoActivo.objects.create(
            id_riesgo="RA-VENC-02", activo=activo, probabilidad=1, impacto=1,
            fecha_objetivo=HOY - dt.timedelta(days=1), estado="CERRADO")
        assert r.esta_vencido is False


class TestPropiedadesVencimientoRiesgoContextual:
    def _rc(self, id_riesgo_contextual, fecha_limite=None, estado="PENDIENTE"):
        return RiesgoContextual.objects.create(
            id_riesgo_contextual=id_riesgo_contextual, escenario_amenaza="x",
            probabilidad=1, impacto=1, fecha_limite=fecha_limite, estado=estado)

    def test_sin_fecha_limite_no_esta_vencido(self):
        rc = self._rc("RC-VENC-01")
        assert rc.esta_vencido is False
        assert rc.por_vencer is False

    def test_vencido(self):
        rc = self._rc("RC-VENC-02", fecha_limite=HOY - dt.timedelta(days=3))
        assert rc.esta_vencido is True
        assert rc.dias_para_vencer == -3

    def test_por_vencer(self):
        rc = self._rc("RC-VENC-03", fecha_limite=HOY + dt.timedelta(days=5))
        assert rc.por_vencer is True
        assert rc.esta_vencido is False

    def test_cerrado_no_cuenta_aunque_este_vencido(self):
        rc = self._rc("RC-VENC-04", fecha_limite=HOY - dt.timedelta(days=10), estado="CERRADO")
        assert rc.esta_vencido is False

    def test_estado_por_defecto_es_pendiente(self):
        """Todo riesgo contextual nuevo (creado desde la app) debe partir de
        PENDIENTE, igual que las acciones de tratamiento — no de un estado
        vacío que quedaría fuera de cualquier filtro."""
        rc = self._rc("RC-VENC-05")
        assert rc.estado == "PENDIENTE"


class TestAlertasResumenEndpoint:
    def test_sin_fechas_limite_no_hay_alertas(self, api_client, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-SIN-FECHA", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x")
        resp = api_client.get("/api/alertas/resumen/")
        assert resp.status_code == 200
        assert resp.data["total_vencidas"] == 0
        assert resp.data["total_por_vencer"] == 0

    def test_agrupa_vencidas_y_por_vencer_correctamente(self, api_client, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-VENCIDA", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x",
            fecha_limite=HOY - dt.timedelta(days=2))
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-POR-VENCER", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x",
            fecha_limite=HOY + dt.timedelta(days=3))

        resp = api_client.get("/api/alertas/resumen/")
        assert resp.data["total_vencidas"] == 1
        assert resp.data["total_por_vencer"] == 1
        assert resp.data["acciones_vencidas"][0]["id_riesgo"] == "R-VENCIDA"
        assert resp.data["acciones_por_vencer"][0]["id_riesgo"] == "R-POR-VENCER"

    def test_endpoint_es_publico(self, api_client):
        resp = api_client.get("/api/alertas/resumen/")
        assert resp.status_code == 200

    def test_incluye_riesgos_contextuales_vencidos(self, api_client):
        RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-END-01", escenario_amenaza="x", probabilidad=1, impacto=1,
            fecha_limite=HOY - dt.timedelta(days=4))
        resp = api_client.get("/api/alertas/resumen/")
        assert resp.data["total_vencidas"] == 1
        assert resp.data["riesgos_contextuales_vencidos"][0]["id_riesgo_contextual"] == "RC-END-01"


class TestComandoEnviarAlertas:
    def test_sin_vencimientos_no_envia_correo(self):
        call_command("enviar_alertas_vencimiento", destinatarios="jose@test.com")
        assert len(mail.outbox) == 0

    def test_con_forzar_envia_aunque_no_haya_vencimientos(self):
        call_command("enviar_alertas_vencimiento", destinatarios="jose@test.com", forzar=True)
        assert len(mail.outbox) == 1

    def test_sin_destinatarios_no_envia(self, settings):
        settings.ALERTAS_EMAIL_DESTINATARIOS = []
        call_command("enviar_alertas_vencimiento")
        assert len(mail.outbox) == 0

    def test_incluye_los_datos_correctos_en_el_cuerpo(self, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CORREO-01",
            descripcion_riesgo="Riesgo crítico de prueba", probabilidad=1, impacto=1,
            acciones_tratamiento="x", fecha_limite=HOY - dt.timedelta(days=5))

        call_command("enviar_alertas_vencimiento", destinatarios="jose@test.com")

        assert len(mail.outbox) == 1
        correo = mail.outbox[0]
        assert correo.to == ["jose@test.com"]
        assert "R-CORREO-01" in correo.body
        assert "5 día" in correo.body
        assert "1 vencido" in correo.subject

    def test_destinatarios_por_parametro_tienen_prioridad_sobre_settings(self, settings, plan_tratamiento):
        settings.ALERTAS_EMAIL_DESTINATARIOS = ["default@test.com"]
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CORREO-02", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x",
            fecha_limite=HOY - dt.timedelta(days=1))

        call_command("enviar_alertas_vencimiento", destinatarios="otro@test.com")
        assert mail.outbox[0].to == ["otro@test.com"]

    def test_incluye_riesgos_contextuales_en_el_cuerpo(self):
        RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-CORREO-01", escenario_amenaza="Escenario de prueba correo",
            probabilidad=1, impacto=1, fecha_limite=HOY - dt.timedelta(days=2))

        call_command("enviar_alertas_vencimiento", destinatarios="jose@test.com")

        assert len(mail.outbox) == 1
        correo = mail.outbox[0]
        assert "RC-CORREO-01" in correo.body
        assert "RIESGOS CONTEXTUALES VENCIDOS" in correo.body
        assert "1 vencido" in correo.subject

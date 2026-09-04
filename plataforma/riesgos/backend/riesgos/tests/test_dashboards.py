import pytest
from riesgos.models import Vulnerabilidad, RiesgoActivo, AccionTratamiento

pytestmark = pytest.mark.django_db


class TestDashboardResumen:
    def test_endpoint_es_publico(self, api_client, activo):
        resp = api_client.get("/api/dashboard/resumen/")
        assert resp.status_code == 200

    def test_kpis_reflejan_los_datos_reales(self, api_client, activo):
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Crítica", severidad_ov="CRITICAL",
            probabilidad=5, impacto=5)
        resp = api_client.get("/api/dashboard/resumen/")
        assert resp.data["kpis"]["total_activos"] == 1
        assert resp.data["kpis"]["total_vulnerabilidades"] == 1
        assert resp.data["kpis"]["vulnerabilidades_criticas"] == 1

    def test_heatmap_agrupa_por_celda_probabilidad_impacto(self, api_client, activo):
        RiesgoActivo.objects.create(id_riesgo="RA-HM-1", activo=activo, probabilidad=5, impacto=5)
        RiesgoActivo.objects.create(id_riesgo="RA-HM-2", activo=activo, probabilidad=5, impacto=5)
        resp = api_client.get("/api/dashboard/resumen/")
        celda = next(c for c in resp.data["heatmap_probabilidad_impacto"]
                     if c["probabilidad"] == 5 and c["impacto"] == 5)
        assert celda["total"] == 2


class TestCumplimientoResumen:
    def test_sin_vinculos_cobertura_es_cero(self, api_client, catalogo_iso_minimo):
        resp = api_client.get("/api/cumplimiento/resumen/")
        assert resp.status_code == 200
        assert resp.data["porcentaje_cobertura_global"] == 0
        assert resp.data["total_aplicables"] == 2

    def test_vincular_accion_sube_la_cobertura(self, api_client, catalogo_iso_minimo, plan_tratamiento):
        control = catalogo_iso_minimo[0]
        accion = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CUMP-01", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x")
        accion.controles_iso_vinculados.add(control)

        resp = api_client.get("/api/cumplimiento/resumen/")
        assert resp.data["total_con_evidencia"] == 1
        assert resp.data["porcentaje_cobertura_global"] == 50  # 1 de 2 aplicables

    def test_control_no_aplicable_no_cuenta_en_el_denominador(self, api_client, catalogo_iso_minimo):
        no_aplica = catalogo_iso_minimo[1]
        no_aplica.aplicable = False
        no_aplica.save()

        resp = api_client.get("/api/cumplimiento/resumen/")
        assert resp.data["total_aplicables"] == 1

    def test_categoria_desglosa_correctamente(self, api_client, catalogo_iso_minimo):
        resp = api_client.get("/api/cumplimiento/resumen/")
        tecnologico = next(c for c in resp.data["por_categoria"] if c["categoria"] == "TECNOLOGICO")
        assert tecnologico["aplicables"] == 1  # solo el control 8.8 del fixture

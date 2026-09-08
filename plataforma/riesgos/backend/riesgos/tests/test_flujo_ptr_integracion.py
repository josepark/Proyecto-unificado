import pytest
from rest_framework import status

from riesgos.models import AccionTratamiento, Vulnerabilidad


@pytest.mark.django_db
class TestImportarExcelEndpoint:
    def test_rechaza_peticion_sin_archivos(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/importar/excel/", {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "matriz_riesgos" in resp.data["detail"] or "ptr" in resp.data["detail"]


@pytest.mark.django_db
class TestFlujoPtrIntegracion:
    """Flujo punta a punta vía API: hallazgo → acción PTR → trazabilidad → cierre."""

    def test_vulnerabilidad_genera_accion_y_cierre(self, api_client_autenticado, activo, plan_tratamiento):
        vuln = Vulnerabilidad.objects.create(
            activo=activo,
            nombre_vulnerabilidad="RCE en servicio expuesto",
            probabilidad=5,
            impacto=5,
            solucion_recomendada="Parchear inmediatamente",
        )

        crear = api_client_autenticado.post("/api/acciones-tratamiento/", {
            "plan": plan_tratamiento.id,
            "id_riesgo": "R-E2E",
            "descripcion_riesgo": vuln.nombre_vulnerabilidad,
            "probabilidad": 5,
            "impacto": 5,
            "acciones_tratamiento": "Aplicar parche y reiniciar servicio",
            "origen_vulnerabilidad": vuln.id,
            "fase": "FASE_1",
            "estado": "PENDIENTE",
        }, format="json")
        assert crear.status_code == status.HTTP_201_CREATED
        accion_id = crear.data["id"]

        detalle_vuln = api_client_autenticado.get(f"/api/vulnerabilidades/{vuln.id}/")
        assert len(detalle_vuln.data["acciones_ptr"]) == 1
        assert detalle_vuln.data["acciones_ptr"][0]["id"] == accion_id

        cerrar = api_client_autenticado.patch(f"/api/acciones-tratamiento/{accion_id}/", {
            "estado": "CERRADO",
            "porcentaje_avance": 100,
        }, format="json")
        assert cerrar.status_code == status.HTTP_200_OK
        assert cerrar.data["estado"] == "CERRADO"

        plan = api_client_autenticado.get(f"/api/planes-tratamiento/{plan_tratamiento.id}/")
        assert plan.status_code == status.HTTP_200_OK
        acciones_ids = [a["id"] for a in plan.data["acciones"]]
        assert accion_id in acciones_ids

        pdf = api_client_autenticado.get(f"/api/planes-tratamiento/{plan_tratamiento.id}/informe.pdf/")
        assert pdf.status_code == status.HTTP_200_OK
        assert pdf.content[:4] == b"%PDF"

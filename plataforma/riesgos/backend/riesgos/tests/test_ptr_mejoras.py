import pytest
from django.urls import reverse
from rest_framework import status

from riesgos.models import AccionTratamiento, PlanTratamientoRiesgos, Vulnerabilidad


@pytest.mark.django_db
class TestInformePtrPdf:
    def test_descarga_pdf_del_plan(self, api_client_autenticado, plan_tratamiento):
        url = reverse("plantratamiento-informe-pdf", args=[plan_tratamiento.id])
        resp = api_client_autenticado.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"


@pytest.mark.django_db
class TestAccionesPtrSerializer:
    def test_vulnerabilidad_incluye_acciones_generadas(self, api_client_autenticado, activo, plan_tratamiento):
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="SQLi", probabilidad=4, impacto=4,
        )
        accion = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-99", descripcion_riesgo="Riesgo test",
            probabilidad=4, impacto=4, acciones_tratamiento="Parchear", origen_vulnerabilidad=vuln,
        )
        resp = api_client_autenticado.get(f"/api/vulnerabilidades/{vuln.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["acciones_ptr"]) == 1
        assert resp.data["acciones_ptr"][0]["id_riesgo"] == accion.id_riesgo


@pytest.mark.django_db
class TestEstadoPlan:
    def test_lista_excluye_archivados_por_defecto(self, api_client_autenticado, plan_tratamiento):
        plan_tratamiento.estado_plan = "ARCHIVADO"
        plan_tratamiento.save()
        resp = api_client_autenticado.get("/api/planes-tratamiento/")
        resultados = resp.data.get("results") if isinstance(resp.data, dict) else resp.data
        ids = [p["id"] for p in resultados]
        assert plan_tratamiento.id not in ids

        resp2 = api_client_autenticado.get("/api/planes-tratamiento/?incluir_archivados=true")
        resultados2 = resp2.data.get("results") if isinstance(resp2.data, dict) else resp2.data
        ids2 = [p["id"] for p in resultados2]
        assert plan_tratamiento.id in ids2

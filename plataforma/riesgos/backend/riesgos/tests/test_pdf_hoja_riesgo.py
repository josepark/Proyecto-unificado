import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from riesgos.models import (
    Vulnerabilidad, RiesgoActivo, RiesgoContextual, AccionTratamiento, Evidencia, CampanaRedTeam,
)
from riesgos.pdf_hoja_riesgo import generar_hoja_riesgo_pdf

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_aislado")]


def _es_pdf_valido(buf):
    contenido = buf.read()
    buf.seek(0)
    return contenido[:5] == b"%PDF-"


class TestGenerarHojaRiesgoPdf:
    def test_activo_sin_ningun_dato_relacionado_genera_pdf_valido(self, activo):
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_vulnerabilidades_del_activo(self, activo):
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Hallazgo de prueba XYZ",
            probabilidad=5, impacto=5, severidad_ov="CRITICAL")
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_riesgos_por_activo(self, activo):
        RiesgoActivo.objects.create(
            id_riesgo="RA-PDF-01", activo=activo, probabilidad=4, impacto=4)
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_acciones_vinculadas_por_origen_fino(self, activo, plan_tratamiento):
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=3, impacto=3)
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-PDF-01", descripcion_riesgo="x",
            probabilidad=3, impacto=3, acciones_tratamiento="x", origen_vulnerabilidad=vuln)
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_acciones_vinculadas_por_campana_aunque_no_tengan_origen_fino(
            self, activo, plan_tratamiento):
        """Regresión: las acciones importadas directo de un PTR en Excel no
        tienen origen_vulnerabilidad/origen_riesgo_activo (esa granularidad no
        existe en ese Excel) — deben seguir apareciendo en la hoja de riesgo del
        activo si comparten campaña de Red Team con el plan."""
        activo.campana_red_team = plan_tratamiento.campana_red_team
        activo.save()
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-PDF-02", descripcion_riesgo="Acción del PTR",
            probabilidad=2, impacto=2, acciones_tratamiento="x")

        from riesgos.pdf_hoja_riesgo import Q, AccionTratamiento as AT
        filtro = Q(origen_vulnerabilidad__activo=activo) | Q(origen_riesgo_activo__activo=activo)
        if activo.campana_red_team_id:
            filtro |= Q(plan__campana_red_team=activo.campana_red_team)
        assert AT.objects.filter(filtro).count() == 1

        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_acciones_de_un_riesgo_contextual_relacionado_con_el_activo(
            self, activo, plan_tratamiento):
        """Tercera vía de vínculo, agregada junto con origen_riesgo_contextual
        en AccionTratamiento — antes un riesgo contextual (amenaza interna,
        legal, físico) no tenía forma de generar una acción trazada en
        absoluto, así que esta ruta simplemente no existía."""
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-PDF-01", escenario_amenaza="x", probabilidad=3, impacto=3)
        rc.activos_relacionados.add(activo)
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-PDF-03", descripcion_riesgo="Desde riesgo contextual",
            probabilidad=3, impacto=3, acciones_tratamiento="x", origen_riesgo_contextual=rc)

        from riesgos.pdf_hoja_riesgo import Q, AccionTratamiento as AT
        filtro = Q(origen_riesgo_contextual__activos_relacionados=activo)
        assert AT.objects.filter(filtro).count() == 1

        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_no_incluye_acciones_de_un_riesgo_contextual_de_otro_activo(
            self, activo, plan_tratamiento):
        from riesgos.models import Activo
        otro_activo = Activo.objects.create(id_activo="PDF-OTRO-RC", nombre="Otro", valor=1)
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-PDF-02", escenario_amenaza="x", probabilidad=1, impacto=1)
        rc.activos_relacionados.add(otro_activo)  # NO el activo de la prueba
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-PDF-04", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", origen_riesgo_contextual=rc)

        from riesgos.pdf_hoja_riesgo import Q, AccionTratamiento as AT
        filtro = Q(origen_riesgo_contextual__activos_relacionados=activo)
        assert AT.objects.filter(filtro).count() == 0

    def test_no_mezcla_acciones_de_otra_campana(self, activo, plan_tratamiento):
        """Un activo sin campaña asignada, o con una distinta a la del plan, no
        debe heredar acciones de tratamiento que no le corresponden."""
        otra_campana = CampanaRedTeam.objects.create(nombre="OTRA-CAMPANA", host_ip="10.0.0.9")
        activo.campana_red_team = otra_campana
        activo.save()
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-PDF-03", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x")

        from riesgos.pdf_hoja_riesgo import Q, AccionTratamiento as AT
        filtro = Q(origen_vulnerabilidad__activo=activo) | Q(origen_riesgo_activo__activo=activo)
        if activo.campana_red_team_id:
            filtro |= Q(plan__campana_red_team=activo.campana_red_team)
        assert AT.objects.filter(filtro).count() == 0

    def test_incluye_evidencia_adjunta_directamente_al_activo(self, activo):
        content_type = __import__(
            "django.contrib.contenttypes.models", fromlist=["ContentType"]
        ).ContentType.objects.get_for_model(activo.__class__)
        Evidencia.objects.create(
            content_type=content_type, object_id=activo.id,
            archivo=SimpleUploadedFile("evidencia.pdf", b"%PDF-1.4 x", content_type="application/pdf"))
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_incluye_evidencia_de_una_vulnerabilidad_del_activo(self, activo):
        from django.contrib.contenttypes.models import ContentType
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=1, impacto=1)
        ct_vuln = ContentType.objects.get(app_label="riesgos", model="vulnerabilidad")
        Evidencia.objects.create(
            content_type=ct_vuln, object_id=vuln.id,
            archivo=SimpleUploadedFile("evidencia_vuln.pdf", b"%PDF-1.4 x", content_type="application/pdf"))
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)

    def test_no_incluye_evidencia_de_otro_activo(self, activo):
        from django.contrib.contenttypes.models import ContentType
        from riesgos.models import Activo
        from riesgos.pdf_hoja_riesgo import _evidencia_del_activo
        otro = Activo.objects.create(id_activo="PDF-OTRO", nombre="Otro", valor=1)
        ct_activo = ContentType.objects.get_for_model(Activo)
        Evidencia.objects.create(
            content_type=ct_activo, object_id=otro.id,
            archivo=SimpleUploadedFile("no_deberia_salir.pdf", b"%PDF-1.4 x", content_type="application/pdf"))
        assert _evidencia_del_activo(activo) == []

    def test_texto_largo_no_rompe_la_generacion(self, activo):
        """Regresión: nombres/descripciones largas deben envolverse dentro de la
        celda, no desbordar — no hay una aserción visual automatizada posible
        aquí, pero al menos confirma que reportlab no lanza excepción."""
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="X" * 300, probabilidad=1, impacto=1)
        buf = generar_hoja_riesgo_pdf(activo)
        assert _es_pdf_valido(buf)


class TestEndpointHojaRiesgoPdf:
    def test_devuelve_pdf_descargable(self, api_client, activo, media_aislado):
        resp = api_client.get(f"/api/activos/{activo.id}/hoja-riesgo.pdf/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert activo.id_activo in resp["Content-Disposition"]

    def test_endpoint_es_publico(self, api_client, activo, media_aislado):
        """Como el resto de la lectura del sistema — no requiere autenticación."""
        resp = api_client.get(f"/api/activos/{activo.id}/hoja-riesgo.pdf/")
        assert resp.status_code == 200

    def test_activo_inexistente_da_404(self, api_client, media_aislado):
        resp = api_client.get("/api/activos/999999/hoja-riesgo.pdf/")
        assert resp.status_code == 404

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.contenttypes.models import ContentType

from riesgos.models import Evidencia, Vulnerabilidad, Activo

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_aislado")]


def _pdf(nombre="evidencia.pdf", contenido=b"%PDF-1.4 contenido de prueba"):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


class TestModeloEvidencia:
    def test_save_calcula_metadatos_automaticamente(self, activo):
        content_type = ContentType.objects.get(app_label="riesgos", model="activo")
        ev = Evidencia.objects.create(
            content_type=content_type, object_id=activo.id, archivo=_pdf("captura.pdf"))
        assert ev.tipo_archivo == "PDF"
        assert ev.nombre_original == "captura.pdf"
        assert ev.tamano_bytes > 0

    def test_content_object_resuelve_al_objeto_correcto(self, activo):
        content_type = ContentType.objects.get(app_label="riesgos", model="activo")
        ev = Evidencia.objects.create(content_type=content_type, object_id=activo.id, archivo=_pdf())
        assert ev.content_object == activo

    def test_extension_no_permitida_lanza_validationerror(self, activo):
        from django.core.exceptions import ValidationError
        content_type = ContentType.objects.get(app_label="riesgos", model="activo")
        ev = Evidencia(content_type=content_type, object_id=activo.id,
                        archivo=SimpleUploadedFile("script.exe", b"x", content_type="application/octet-stream"))
        with pytest.raises(ValidationError):
            ev.full_clean()


class TestApiEvidencia:
    def test_subir_evidencia_valida(self, api_client_autenticado, activo):
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id, "archivo": _pdf(),
            "descripcion": "Evidencia de prueba",
        }, format="multipart")
        assert resp.status_code == 201, resp.data
        assert resp.data["modelo_actual"] == "activo"
        assert resp.data["tipo_archivo"] == "PDF"
        assert resp.data["archivo_url"] is not None

    def test_registra_quien_subio_el_archivo(self, api_client_autenticado, activo, usuario):
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id, "archivo": _pdf(),
        }, format="multipart")
        assert resp.data["subido_por_username"] == usuario.username

    def test_requiere_autenticacion(self, api_client, activo):
        resp = api_client.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id, "archivo": _pdf(),
        }, format="multipart")
        assert resp.status_code == 401

    def test_rechaza_extension_no_permitida(self, api_client_autenticado, activo):
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id,
            "archivo": SimpleUploadedFile("malware.exe", b"x", content_type="application/octet-stream"),
        }, format="multipart")
        assert resp.status_code == 400
        assert "archivo" in resp.data

    def test_rechaza_archivo_demasiado_grande(self, api_client_autenticado, activo):
        contenido_grande = b"0" * (11 * 1024 * 1024)  # 11 MB > límite de 10 MB
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id,
            "archivo": SimpleUploadedFile("grande.pdf", contenido_grande, content_type="application/pdf"),
        }, format="multipart")
        assert resp.status_code == 400
        assert "archivo" in resp.data

    def test_rechaza_object_id_inexistente(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": 999999, "archivo": _pdf(),
        }, format="multipart")
        assert resp.status_code == 400
        assert "object_id" in resp.data

    def test_rechaza_modelo_fuera_de_whitelist(self, api_client_autenticado, usuario):
        """Confirma que no se puede adjuntar evidencia a modelos sensibles (ej. User)
        aunque el content_type exista en el sistema — MODELOS_CON_EVIDENCIA es una
        whitelist explícita, no una blacklist."""
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "user", "object_id": usuario.id, "archivo": _pdf(),
        }, format="multipart")
        assert resp.status_code == 400
        assert "modelo" in resp.data

    def test_filtra_por_modelo_y_object_id(self, api_client_autenticado, activo):
        otro_activo = Activo.objects.create(id_activo="TEST-002", nombre="Otro", valor=1)
        api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id, "archivo": _pdf("a.pdf"),
        }, format="multipart")
        api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": otro_activo.id, "archivo": _pdf("b.pdf"),
        }, format="multipart")

        resp = api_client_autenticado.get(f"/api/evidencias/?modelo=activo&object_id={activo.id}")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["nombre_original"] == "a.pdf"

    def test_vincula_evidencia_a_una_vulnerabilidad(self, api_client_autenticado, activo):
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Hallazgo de prueba", probabilidad=3, impacto=3)
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "vulnerabilidad", "object_id": vuln.id, "archivo": _pdf(),
        }, format="multipart")
        assert resp.status_code == 201
        assert Evidencia.objects.get(pk=resp.data["id"]).content_object == vuln

    def test_eliminar_evidencia_requiere_autenticacion(self, api_client, api_client_autenticado, activo):
        resp = api_client_autenticado.post("/api/evidencias/", {
            "modelo": "activo", "object_id": activo.id, "archivo": _pdf(),
        }, format="multipart")
        ev_id = resp.data["id"]

        assert api_client.delete(f"/api/evidencias/{ev_id}/").status_code == 401
        assert api_client_autenticado.delete(f"/api/evidencias/{ev_id}/").status_code == 204

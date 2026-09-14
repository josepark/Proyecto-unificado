import pytest

pytestmark = pytest.mark.django_db


class TestHistorialAuditoria:
    def test_activo_recien_creado_sin_ediciones_tiene_una_entrada(self, api_client_autenticado):
        resp_crear = api_client_autenticado.post("/api/activos/", {
            "id_activo": "HIST-001", "nombre": "x", "valor": 1,
        })
        activo_id = resp_crear.data["id"]

        resp = api_client_autenticado.get(f"/api/activos/{activo_id}/historial/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["tipo"] == "Creación"
        assert resp.data[0]["cambios"] == []

    def test_editar_registra_el_diff_del_campo(self, api_client_autenticado):
        resp_crear = api_client_autenticado.post("/api/activos/", {
            "id_activo": "HIST-002", "nombre": "Nombre original", "valor": 1,
        })
        activo_id = resp_crear.data["id"]

        api_client_autenticado.patch(f"/api/activos/{activo_id}/", {"nombre": "Nombre editado"})

        resp = api_client_autenticado.get(f"/api/activos/{activo_id}/historial/")
        assert len(resp.data) == 2
        edicion = resp.data[0]  # más reciente primero
        assert edicion["tipo"] == "Edición"
        cambio_nombre = next(c for c in edicion["cambios"] if c["campo"] == "nombre")
        assert cambio_nombre["antes"] == "Nombre original"
        assert cambio_nombre["despues"] == "Nombre editado"

    def test_registra_el_usuario_que_hizo_el_cambio(self, api_client_autenticado):
        resp_crear = api_client_autenticado.post("/api/activos/", {
            "id_activo": "HIST-003", "nombre": "x", "valor": 1,
        })
        resp = api_client_autenticado.get(f"/api/activos/{resp_crear.data['id']}/historial/")
        assert resp.data[0]["usuario"] == "analista"

    def test_historial_no_expone_datos_de_otro_activo(self, api_client_autenticado):
        r1 = api_client_autenticado.post("/api/activos/", {"id_activo": "HIST-A", "nombre": "a", "valor": 1})
        api_client_autenticado.post("/api/activos/", {"id_activo": "HIST-B", "nombre": "b", "valor": 1})

        resp = api_client_autenticado.get(f"/api/activos/{r1.data['id']}/historial/")
        assert len(resp.data) == 1  # solo la creación de HIST-A, no de HIST-B

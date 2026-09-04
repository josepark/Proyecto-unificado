import pytest

pytestmark = pytest.mark.django_db


class TestLogin:
    def test_login_correcto_devuelve_token(self, api_client, usuario):
        resp = api_client.post("/api/auth/login/", {
            "username": "analista", "password": "clave-segura-qa",
        })
        assert resp.status_code == 200
        assert "token" in resp.data
        assert resp.data["username"] == "analista"

    def test_login_credenciales_invalidas(self, api_client, usuario):
        resp = api_client.post("/api/auth/login/", {
            "username": "analista", "password": "incorrecta",
        })
        assert resp.status_code == 400

    def test_me_requiere_token(self, api_client):
        resp = api_client.get("/api/auth/me/")
        assert resp.status_code == 401

    def test_me_con_token_valido(self, api_client_autenticado):
        resp = api_client_autenticado.get("/api/auth/me/")
        assert resp.status_code == 200
        assert resp.data["username"] == "analista"

    def test_logout_invalida_el_token(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/auth/logout/")
        assert resp.status_code == 204
        # el mismo token ya no debe servir
        resp2 = api_client_autenticado.get("/api/auth/me/")
        assert resp2.status_code == 401


class TestLecturaLibreEscrituraProtegida:
    """IsAuthenticatedOrReadOnly: GET siempre abierto, escritura exige token."""

    def test_listar_activos_sin_autenticar(self, api_client, activo):
        resp = api_client.get("/api/activos/")
        assert resp.status_code == 200

    def test_crear_activo_sin_token_es_rechazado(self, api_client):
        resp = api_client.post("/api/activos/", {
            "id_activo": "NOAUTH-001", "nombre": "x", "valor": 1,
        })
        assert resp.status_code == 401

    def test_crear_activo_con_token_funciona(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/activos/", {
            "id_activo": "AUTH-001", "nombre": "x", "valor": 1,
        })
        assert resp.status_code == 201

    def test_token_invalido_es_rechazado(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Token token-que-no-existe")
        resp = api_client.post("/api/activos/", {
            "id_activo": "BAD-001", "nombre": "x", "valor": 1,
        })
        assert resp.status_code == 401

    def test_eliminar_sin_token_es_rechazado(self, api_client, activo):
        resp = api_client.delete(f"/api/activos/{activo.id}/")
        assert resp.status_code == 401

import datetime as dt

import jwt
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from riesgos.models import Activo

pytestmark = pytest.mark.django_db

SECRETO = "secreto-de-prueba-para-jwt"


@pytest.fixture(autouse=True)
def jwt_habilitado(settings):
    settings.JWT_SHARED_SECRET = SECRETO
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_ISSUER = "suiin-inventario"


def _token(username="analista_plataforma", roles=("Dinamizador",), issuer="suiin-inventario",
           secreto=SECRETO, expira_en_minutos=30, sub="7", ver=1):
    ahora = dt.datetime.now(dt.timezone.utc)
    payload = {
        "iss": issuer, "sub": sub, "username": username, "roles": list(roles),
        "ver": ver,
        "iat": ahora, "exp": ahora + dt.timedelta(minutes=expira_en_minutos),
    }
    return jwt.encode(payload, secreto, algorithm="HS256")


def _cliente_con_jwt(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class TestAutenticacionJWT:
    def test_token_valido_autentica(self):
        resp = _cliente_con_jwt(_token()).get("/api/activos/")
        assert resp.status_code == 200

    def test_aprovisiona_el_usuario_la_primera_vez(self):
        assert not User.objects.filter(username="usuario_nuevo_jwt").exists()
        _cliente_con_jwt(_token(username="usuario_nuevo_jwt")).get("/api/activos/")
        assert User.objects.filter(username="usuario_nuevo_jwt").exists()

    def test_reutiliza_el_mismo_usuario_en_peticiones_siguientes(self):
        _cliente_con_jwt(_token(username="misma_persona")).get("/api/activos/")
        _cliente_con_jwt(_token(username="misma_persona")).get("/api/activos/")
        assert User.objects.filter(username="misma_persona").count() == 1

    def test_token_expirado_es_rechazado(self):
        token = _token(expira_en_minutos=-10)
        resp = _cliente_con_jwt(token).post("/api/activos/", {"id_activo": "X", "nombre": "x", "valor": 1})
        assert resp.status_code == 401

    def test_firma_invalida_es_rechazada(self):
        token = _token(secreto="secreto-equivocado")
        resp = _cliente_con_jwt(token).post("/api/activos/", {"id_activo": "X", "nombre": "x", "valor": 1})
        assert resp.status_code == 401

    def test_issuer_incorrecto_es_rechazado(self):
        token = _token(issuer="alguien-mas")
        resp = _cliente_con_jwt(token).post("/api/activos/", {"id_activo": "X", "nombre": "x", "valor": 1})
        assert resp.status_code == 401

    def test_sin_jwt_shared_secret_configurado_no_autentica_pero_no_falla(self, settings):
        settings.JWT_SHARED_SECRET = ""
        resp = _cliente_con_jwt(_token()).get("/api/activos/")
        assert resp.status_code == 200  # lectura sigue libre, JWT simplemente no aplica

    def test_header_no_bearer_lo_maneja_la_autenticacion_por_token_no_jwt(self):
        """Un header 'Token ...' no es un JWT — JWTPlataformaAuthentication debe
        hacerse a un lado (devolver None) en vez de fallar, dejando que
        TokenAuthentication lo evalúe. Como ese valor no es un token válido de
        riesgos, la respuesta correcta sigue siendo 401 — por la otra vía, no
        por un error de parseo de JWT."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token algo-que-no-es-jwt")
        resp = client.get("/api/activos/")
        assert resp.status_code == 401
        assert "token" in resp.data["detail"].lower()  # mensaje de TokenAuthentication, no de JWT


class TestPermisosPorRolDePlataforma:
    def test_consultor_puede_leer(self):
        resp = _cliente_con_jwt(_token(roles=["Consultor"])).get("/api/activos/")
        assert resp.status_code == 200

    def test_consultor_no_puede_escribir(self):
        resp = _cliente_con_jwt(_token(roles=["Consultor"])).post(
            "/api/activos/", {"id_activo": "ROL-01", "nombre": "x", "valor": 1})
        assert resp.status_code == 403
        assert not Activo.objects.filter(id_activo="ROL-01").exists()

    def test_dinamizador_puede_escribir(self):
        resp = _cliente_con_jwt(_token(roles=["Dinamizador"])).post(
            "/api/activos/", {"id_activo": "ROL-02", "nombre": "x", "valor": 1})
        assert resp.status_code == 201

    def test_administrador_puede_escribir(self):
        resp = _cliente_con_jwt(_token(roles=["Administrador"])).post(
            "/api/activos/", {"id_activo": "ROL-03", "nombre": "x", "valor": 1})
        assert resp.status_code == 201

    def test_sin_ningun_rol_no_puede_escribir(self):
        resp = _cliente_con_jwt(_token(roles=[])).post(
            "/api/activos/", {"id_activo": "ROL-04", "nombre": "x", "valor": 1})
        assert resp.status_code == 403

    def test_administrador_obtiene_is_staff(self):
        _cliente_con_jwt(_token(username="jefe", roles=["Administrador"])).get("/api/activos/")
        assert User.objects.get(username="jefe").is_staff is True

    def test_dinamizador_no_obtiene_is_staff(self):
        _cliente_con_jwt(_token(username="operativo", roles=["Dinamizador"])).get("/api/activos/")
        assert User.objects.get(username="operativo").is_staff is False

    def test_perder_el_rol_administrador_quita_is_staff_en_la_siguiente_peticion(self):
        """Si a alguien le retiran el rol en el inventario, el próximo JWT que
        traiga ya no lo incluye — riesgos debe reflejarlo, no quedarse con el
        is_staff de una sesión anterior."""
        _cliente_con_jwt(_token(username="ex_admin", roles=["Administrador"])).get("/api/activos/")
        assert User.objects.get(username="ex_admin").is_staff is True

        _cliente_con_jwt(_token(username="ex_admin", roles=["Consultor"])).get("/api/activos/")
        assert User.objects.get(username="ex_admin").is_staff is False

    def test_token_con_version_obsoleta_es_rechazado(self, monkeypatch):
        """Ola 1: si el inventario incrementó jwt_version, un token anterior debe fallar."""
        monkeypatch.setattr(
            "riesgos.auth_jwt.jwt_version_vigente",
            lambda username: 99,
        )
        token = _token(username="usuario_revocado", roles=["Dinamizador"], expira_en_minutos=30)
        import jwt as pyjwt
        payload = pyjwt.decode(token, SECRETO, algorithms=["HS256"], issuer="suiin-inventario")
        payload["ver"] = 1
        token_viejo = pyjwt.encode(payload, SECRETO, algorithm="HS256")
        resp = _cliente_con_jwt(token_viejo).get("/api/activos/")
        assert resp.status_code == 401


class TestCompatibilidadConTokenPropio:
    """El token propio de riesgos (modo independiente, sin plataforma) debe
    seguir funcionando exactamente igual que antes de agregar JWT."""

    def test_token_propio_sigue_permitiendo_escritura_a_cualquier_autenticado(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/activos/", {"id_activo": "TOK-01", "nombre": "x", "valor": 1})
        assert resp.status_code == 201

    def test_sin_ninguna_autenticacion_no_puede_escribir(self, api_client):
        resp = api_client.post("/api/activos/", {"id_activo": "TOK-02", "nombre": "x", "valor": 1})
        assert resp.status_code == 401

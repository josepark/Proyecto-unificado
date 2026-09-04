import datetime as dt

import jwt
import pytest
from rest_framework.test import APIClient

from riesgos.models import Vulnerabilidad

pytestmark = pytest.mark.django_db

URL = "/api/vulnerabilidades/bulk-actualizar/"
SECRETO = "secreto-de-prueba-para-jwt"


@pytest.fixture(autouse=True)
def jwt_habilitado(settings):
    settings.JWT_SHARED_SECRET = SECRETO
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_ISSUER = "suiin-inventario"


def _token(username="analista_plataforma", roles=("Dinamizador",)):
    ahora = dt.datetime.now(dt.timezone.utc)
    payload = {
        "iss": "suiin-inventario", "sub": "7", "username": username, "roles": list(roles),
        "iat": ahora, "exp": ahora + dt.timedelta(minutes=30),
    }
    return jwt.encode(payload, SECRETO, algorithm="HS256")


def _cliente_con_rol(roles):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(roles=roles)}")
    return client


@pytest.fixture
def tres_vulnerabilidades(activo):
    return [
        Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad=f"Hallazgo {i}",
            probabilidad=5, impacto=5, estado="PENDIENTE")
        for i in range(3)
    ]


class TestBulkActualizarVulnerabilidades:
    def test_actualiza_el_estado_de_varias_a_la_vez(self, api_client_autenticado, tres_vulnerabilidades):
        ids = [v.id for v in tres_vulnerabilidades]
        resp = api_client_autenticado.post(URL, {"ids": ids, "campos": {"estado": "EN_PROGRESO"}}, format="json")
        assert resp.status_code == 200
        assert resp.data["actualizados"] == 3
        for v in tres_vulnerabilidades:
            v.refresh_from_db()
            assert v.estado == "EN_PROGRESO"

    def test_cada_actualizacion_queda_en_el_historial_de_auditoria(self, api_client_autenticado, tres_vulnerabilidades):
        """La razón de guardar una por una en vez de un UPDATE masivo: que
        django-simple-history sí registre cada cambio — verificado con
        datos reales antes de escribir esta prueba."""
        ids = [v.id for v in tres_vulnerabilidades]
        api_client_autenticado.post(URL, {"ids": ids, "campos": {"estado": "CERRADO"}}, format="json")
        for v in tres_vulnerabilidades:
            v.refresh_from_db()
            ultimo = v.historial.first()
            assert ultimo.history_type == "~"
            assert ultimo.estado == "CERRADO"

    def test_puede_actualizar_varios_campos_a_la_vez(self, api_client_autenticado, tres_vulnerabilidades):
        ids = [v.id for v in tres_vulnerabilidades]
        resp = api_client_autenticado.post(
            URL, {"ids": ids, "campos": {"estado": "CERRADO", "tratamiento": "MITIGAR"}}, format="json")
        assert resp.status_code == 200
        for v in tres_vulnerabilidades:
            v.refresh_from_db()
            assert v.estado == "CERRADO"
            assert v.tratamiento == "MITIGAR"

    def test_solo_afecta_los_ids_indicados(self, api_client_autenticado, tres_vulnerabilidades):
        ids = [tres_vulnerabilidades[0].id]
        api_client_autenticado.post(URL, {"ids": ids, "campos": {"estado": "CERRADO"}}, format="json")
        tres_vulnerabilidades[0].refresh_from_db()
        tres_vulnerabilidades[1].refresh_from_db()
        assert tres_vulnerabilidades[0].estado == "CERRADO"
        assert tres_vulnerabilidades[1].estado == "PENDIENTE"

    def test_ignora_campos_no_permitidos(self, api_client_autenticado, tres_vulnerabilidades):
        """No se puede colar un cambio a un campo fuera de la lista blanca
        (ej. nombre_vulnerabilidad) a través de este endpoint."""
        ids = [v.id for v in tres_vulnerabilidades]
        resp = api_client_autenticado.post(
            URL, {"ids": ids, "campos": {"nombre_vulnerabilidad": "Hackeado"}}, format="json")
        assert resp.status_code == 400
        tres_vulnerabilidades[0].refresh_from_db()
        assert tres_vulnerabilidades[0].nombre_vulnerabilidad == "Hallazgo 0"

    def test_sin_ids_da_400(self, api_client_autenticado):
        resp = api_client_autenticado.post(URL, {"ids": [], "campos": {"estado": "CERRADO"}}, format="json")
        assert resp.status_code == 400

    def test_sin_campos_validos_da_400(self, api_client_autenticado, tres_vulnerabilidades):
        resp = api_client_autenticado.post(URL, {"ids": [tres_vulnerabilidades[0].id], "campos": {}}, format="json")
        assert resp.status_code == 400

    def test_ids_inexistentes_no_fallan_simplemente_no_actualizan_nada(self, api_client_autenticado):
        resp = api_client_autenticado.post(URL, {"ids": [999999], "campos": {"estado": "CERRADO"}}, format="json")
        assert resp.status_code == 200
        assert resp.data["actualizados"] == 0

    def test_requiere_autenticacion(self, api_client, tres_vulnerabilidades):
        ids = [v.id for v in tres_vulnerabilidades]
        resp = api_client.post(URL, {"ids": ids, "campos": {"estado": "CERRADO"}}, format="json")
        assert resp.status_code == 401
        tres_vulnerabilidades[0].refresh_from_db()
        assert tres_vulnerabilidades[0].estado == "PENDIENTE"

    def test_consultor_no_puede_usar_el_bulk(self, tres_vulnerabilidades):
        """Mismo criterio de escritura que el resto del sistema — un rol de
        solo lectura no debe poder editar en lote tampoco."""
        ids = [v.id for v in tres_vulnerabilidades]
        resp = _cliente_con_rol(["Consultor"]).post(URL, {"ids": ids, "campos": {"estado": "CERRADO"}}, format="json")
        assert resp.status_code == 403

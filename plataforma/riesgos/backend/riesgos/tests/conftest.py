import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from riesgos.models import (
    Activo, CampanaRedTeam, PlanTratamientoRiesgos, ControlISO27001,
)


@pytest.fixture
def usuario(db):
    return User.objects.create_user(username="analista", password="clave-segura-qa")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_client_autenticado(usuario):
    """
    Cliente API con token válido — simula al frontend tras iniciar sesión.
    Crea un APIClient propio (no reutiliza la fixture `api_client`): si un test
    pide ambos fixtures a la vez para comparar autenticado-vs-anónimo,
    `.credentials()` sobre un cliente compartido mutaría el mismo objeto y el
    cliente "anónimo" terminaría autenticado también.
    """
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=usuario)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def activo(db):
    return Activo.objects.create(
        id_activo="TEST-001", nombre="Servidor de prueba", tipo="Servidor",
        ip_principal="10.0.0.1", valor=6, riesgo_matriz="BAJO",
    )


@pytest.fixture
def campana(db):
    return CampanaRedTeam.objects.create(
        nombre="TEST-CAMPANA", host_ip="10.0.0.1", estado_compromiso="COMPROMETIDO",
    )


@pytest.fixture
def plan_tratamiento(db, campana):
    return PlanTratamientoRiesgos.objects.create(
        referencia="TEST-PTR-001", titulo="PTR de prueba", campana_red_team=campana,
        fecha_emision="2026-01-01",
    )


@pytest.fixture
def catalogo_iso_minimo(db):
    """Un par de controles reales para pruebas — no requiere cargar los 93."""
    return [
        ControlISO27001.objects.create(codigo="8.8", categoria="TECNOLOGICO",
                                        nombre="Gestión de vulnerabilidades técnicas"),
        ControlISO27001.objects.create(codigo="5.9", categoria="ORGANIZACIONAL",
                                        nombre="Inventario de información y otros activos asociados"),
    ]


@pytest.fixture
def media_aislado(settings, tmp_path):
    """Redirige MEDIA_ROOT a una carpeta temporal — evita que los archivos que
    suben las pruebas de Evidencia queden en el media/ real del proyecto."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path

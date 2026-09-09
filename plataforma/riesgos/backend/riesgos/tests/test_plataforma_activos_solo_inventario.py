import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
@override_settings(PLATAFORMA_ACTIVOS_SOLO_INVENTARIO=True)
def test_post_activo_bloqueado_en_plataforma_unificada(api_client_autenticado):
    resp = api_client_autenticado.post("/api/activos/", {
        "id_activo": "HUERF-001",
        "nombre": "Activo huérfano",
        "valor": 5,
    })
    assert resp.status_code == 403
    assert "Inventario" in resp.data["detail"]


@pytest.mark.django_db
@override_settings(PLATAFORMA_ACTIVOS_SOLO_INVENTARIO=False)
def test_post_activo_permitido_fuera_de_plataforma(api_client_autenticado):
    resp = api_client_autenticado.post("/api/activos/", {
        "id_activo": "STAND-001",
        "nombre": "Activo standalone",
        "valor": 3,
    })
    assert resp.status_code == 201, resp.data

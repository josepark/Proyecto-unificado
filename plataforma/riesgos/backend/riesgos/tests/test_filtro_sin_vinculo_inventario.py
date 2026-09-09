import pytest

pytestmark = pytest.mark.django_db


class TestFiltroSinVinculoInventario:
    def test_filtra_activos_huerfanos(self, api_client_autenticado):
        from riesgos.models import Activo

        Activo.objects.create(id_activo="VINC-01", nombre="Vinculado", valor=5, inventario_id=10)
        Activo.objects.create(id_activo="HUERF-01", nombre="Huérfano", valor=3)

        resp = api_client_autenticado.get("/api/activos/", {"sin_vinculo_inventario": "true"})
        assert resp.status_code == 200
        ids = {a["id_activo"] for a in resp.data["results"]}
        assert "HUERF-01" in ids
        assert "VINC-01" not in ids

    def test_sin_filtro_devuelve_ambos(self, api_client_autenticado):
        from riesgos.models import Activo

        Activo.objects.create(id_activo="VINC-02", nombre="Vinculado", valor=5, inventario_id=11)
        Activo.objects.create(id_activo="HUERF-02", nombre="Huérfano", valor=3)

        resp = api_client_autenticado.get("/api/activos/")
        ids = {a["id_activo"] for a in resp.data["results"]}
        assert "VINC-02" in ids
        assert "HUERF-02" in ids

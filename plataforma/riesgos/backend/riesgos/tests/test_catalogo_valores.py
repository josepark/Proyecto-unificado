import pytest
from django.core.management import call_command

from riesgos.models import CatalogoValor, Activo

pytestmark = pytest.mark.django_db


class TestModeloCatalogoValor:
    def test_unique_together_categoria_valor(self):
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor")
        with pytest.raises(Exception):
            CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor")

    def test_mismo_valor_en_categorias_distintas_si_se_permite(self):
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Administrador")
        CatalogoValor.objects.create(categoria="RESPONSABLE_ACCION", valor="Administrador")
        assert CatalogoValor.objects.count() == 2


class TestComandoSembrarCatalogos:
    def test_extrae_valores_distintos_reales(self, activo):
        activo2 = Activo.objects.create(id_activo="CAT-02", nombre="x", valor=1, tipo="Servidor")
        Activo.objects.filter(pk=activo.pk).update(tipo="Servidor")  # mismo valor, no debe duplicar
        activo3 = Activo.objects.create(id_activo="CAT-03", nombre="x", valor=1, tipo="Switch")

        call_command("sembrar_catalogos")

        valores = set(CatalogoValor.objects.filter(categoria="TIPO_ACTIVO").values_list("valor", flat=True))
        assert valores == {"Servidor", "Switch"}

    def test_es_idempotente(self, activo):
        Activo.objects.filter(pk=activo.pk).update(tipo="Servidor")
        call_command("sembrar_catalogos")
        total_primera_vez = CatalogoValor.objects.count()
        call_command("sembrar_catalogos")
        assert CatalogoValor.objects.count() == total_primera_vez

    def test_ignora_valores_vacios(self, activo):
        Activo.objects.filter(pk=activo.pk).update(tipo="")
        call_command("sembrar_catalogos")
        assert not CatalogoValor.objects.filter(categoria="TIPO_ACTIVO", valor="").exists()


class TestApiCatalogoValor:
    def test_listar_filtrado_por_categoria(self):
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor")
        CatalogoValor.objects.create(categoria="RESPONSABLE_ACCION", valor="Adm.")

        from rest_framework.test import APIClient
        resp = APIClient().get("/api/catalogo/?categoria=TIPO_ACTIVO")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["valor"] == "Servidor"

    def test_por_defecto_solo_lista_los_activos(self):
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor", activo=True)
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Obsoleto", activo=False)

        from rest_framework.test import APIClient
        resp = APIClient().get("/api/catalogo/?categoria=TIPO_ACTIVO")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["valor"] == "Servidor"

    def test_parametro_activo_false_lista_los_desactivados(self):
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor", activo=True)
        CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Obsoleto", activo=False)

        from rest_framework.test import APIClient
        resp = APIClient().get("/api/catalogo/?categoria=TIPO_ACTIVO&activo=false")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["valor"] == "Obsoleto"

    def test_endpoint_es_publico_para_lectura(self):
        from rest_framework.test import APIClient
        resp = APIClient().get("/api/catalogo/")
        assert resp.status_code == 200


class TestObtenerOCrear:
    URL = "/api/catalogo/obtener-o-crear/"

    def test_reusa_un_valor_existente_sin_duplicar(self, api_client_autenticado):
        original = CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor")
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "Servidor"})
        assert resp.status_code == 200
        assert resp.data["id"] == original.id
        assert CatalogoValor.objects.count() == 1

    def test_crea_un_valor_genuinamente_nuevo(self, api_client_autenticado):
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "Impresora"})
        assert resp.status_code == 201
        assert CatalogoValor.objects.filter(categoria="TIPO_ACTIVO", valor="Impresora").exists()

    def test_reuso_case_insensitive_no_duplica(self, api_client_autenticado):
        original = CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor")
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "SERVIDOR"})
        assert resp.status_code == 200
        assert resp.data["id"] == original.id
        assert CatalogoValor.objects.count() == 1

    def test_reactiva_un_valor_que_estaba_desactivado(self, api_client_autenticado):
        desactivado = CatalogoValor.objects.create(categoria="TIPO_ACTIVO", valor="Servidor", activo=False)
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "Servidor"})
        assert resp.status_code == 200
        desactivado.refresh_from_db()
        assert desactivado.activo is True

    def test_requiere_categoria_y_valor(self, api_client_autenticado):
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO"})
        assert resp.status_code == 400

    def test_requiere_autenticacion(self, api_client):
        resp = api_client.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "Servidor"})
        assert resp.status_code == 401

    def test_no_mezcla_el_mismo_valor_entre_categorias_distintas(self, api_client_autenticado):
        CatalogoValor.objects.create(categoria="RESPONSABLE_ACCION", valor="Administrador")
        resp = api_client_autenticado.post(self.URL, {"categoria": "TIPO_ACTIVO", "valor": "Administrador"})
        assert resp.status_code == 201  # es nuevo EN ESA categoría, aunque el texto coincida con otra
        assert CatalogoValor.objects.count() == 2

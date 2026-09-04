import pytest
import responses
from django.core.management import call_command

from riesgos.models import TecnicaMitre

pytestmark = pytest.mark.django_db

BASE_URL = "http://inventario-test/api"


def _tecnica(codigo, nombre, tipo="TE", tacticas="Initial Access"):
    return {
        "id": hash(codigo) % 1000, "codigo": codigo, "nombre": nombre, "tipo": tipo,
        "tacticas": tacticas, "codigo_padre": "", "url": f"https://attack.mitre.org/techniques/{codigo}",
    }


class TestComandoSincronizarTecnicasMitre:
    @responses.activate
    def test_crea_tecnicas_nuevas(self):
        responses.add(responses.GET, f"{BASE_URL}/amenazas/", json={
            "count": 2, "next": None, "previous": None,
            "results": [_tecnica("T1190", "Exploit Public-Facing Application"),
                        _tecnica("T1040", "Network Sniffing")],
        }, status=200)

        call_command("sincronizar_tecnicas_mitre", url=BASE_URL)

        assert TecnicaMitre.objects.count() == 2
        t = TecnicaMitre.objects.get(codigo="T1190")
        assert t.nombre == "Exploit Public-Facing Application"
        assert t.tacticas == "Initial Access"

    @responses.activate
    def test_actualiza_una_tecnica_existente(self):
        TecnicaMitre.objects.create(codigo="T1190", nombre="Nombre viejo")
        responses.add(responses.GET, f"{BASE_URL}/amenazas/", json={
            "count": 1, "next": None, "previous": None,
            "results": [_tecnica("T1190", "Nombre actualizado")],
        }, status=200)

        call_command("sincronizar_tecnicas_mitre", url=BASE_URL)

        assert TecnicaMitre.objects.count() == 1
        assert TecnicaMitre.objects.get(codigo="T1190").nombre == "Nombre actualizado"

    @responses.activate
    def test_pagina_hasta_agotar_resultados(self):
        responses.add(responses.GET, f"{BASE_URL}/amenazas/", json={
            "count": 2, "next": f"{BASE_URL}/amenazas/?page=2", "previous": None,
            "results": [_tecnica("T1001", "Uno")],
        }, status=200)
        responses.add(responses.GET, f"{BASE_URL}/amenazas/?page=2", json={
            "count": 2, "next": None, "previous": None,
            "results": [_tecnica("T1002", "Dos")],
        }, status=200)

        call_command("sincronizar_tecnicas_mitre", url=BASE_URL)
        assert TecnicaMitre.objects.count() == 2

    @responses.activate
    def test_error_de_conexion_no_lanza_excepcion(self):
        import requests
        responses.add(responses.GET, f"{BASE_URL}/amenazas/",
                       body=requests.exceptions.ConnectionError("caído"))
        call_command("sincronizar_tecnicas_mitre", url=BASE_URL)  # no debe lanzar
        assert TecnicaMitre.objects.count() == 0


class TestApiTecnicaMitre:
    def test_busqueda_por_codigo(self):
        TecnicaMitre.objects.create(codigo="T1040", nombre="Network Sniffing")
        TecnicaMitre.objects.create(codigo="T1078", nombre="Valid Accounts")

        from rest_framework.test import APIClient
        resp = APIClient().get("/api/tecnicas-mitre/?search=T1040")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["nombre"] == "Network Sniffing"

    def test_busqueda_por_nombre(self):
        TecnicaMitre.objects.create(codigo="T1040", nombre="Network Sniffing")
        from rest_framework.test import APIClient
        resp = APIClient().get("/api/tecnicas-mitre/?search=sniffing")
        assert resp.data["count"] == 1

    def test_filtro_por_tipo(self):
        TecnicaMitre.objects.create(codigo="TA0001", nombre="Initial Access", tipo="TA")
        TecnicaMitre.objects.create(codigo="T1190", nombre="Exploit", tipo="TE")

        from rest_framework.test import APIClient
        resp = APIClient().get("/api/tecnicas-mitre/?tipo=TA")
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["codigo"] == "TA0001"

    def test_endpoint_es_publico(self):
        from rest_framework.test import APIClient
        resp = APIClient().get("/api/tecnicas-mitre/")
        assert resp.status_code == 200

    def test_es_de_solo_lectura(self, api_client_autenticado):
        resp = api_client_autenticado.post(
            "/api/tecnicas-mitre/", {"codigo": "T9999", "nombre": "x"})
        assert resp.status_code == 405  # method not allowed — ReadOnlyModelViewSet

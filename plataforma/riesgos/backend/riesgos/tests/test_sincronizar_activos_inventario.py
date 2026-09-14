import datetime as dt

import pytest
import requests
import responses
from django.core.management import call_command
from django.utils import timezone

from riesgos.models import Activo

pytestmark = pytest.mark.django_db

BASE_URL = "http://inventario-test/api"


def _sincronizado_previamente(activo):
    """Simula un activo que ya pasó por una sincronización limpia anterior — sin
    esto, fue_editado_tras_importacion() lo protege por defecto (ver
    test_importar_proteccion.py: un registro preexistente sin importado_en se
    protege siempre, sea cual sea su origen real)."""
    Activo.objects.filter(pk=activo.pk).update(importado_en=timezone.now())
    activo.refresh_from_db()
    return activo


def _mock_lista(items, url=f"{BASE_URL}/activos/"):
    responses.add(responses.GET, url, json={
        "count": len(items), "next": None, "previous": None, "results": items,
    }, status=200)


def _item(id, id_activo, nombre, clase="SIST", clasificacion_si="CONF", valor=6):
    return {
        "id": id, "id_activo": id_activo, "nombre": nombre, "clase": clase,
        "clasificacion_si": clasificacion_si, "valor": valor,
    }


def _mock_detalle(inv_id, ip="192.168.1.200/24", vlan="LAN"):
    responses.add(
        responses.GET, f"{BASE_URL}/activos/{inv_id}/",
        json={"infraestructura": {"ip_segmento": ip, "vlan": vlan}}, status=200,
    )


class TestSincronizacionBasica:
    @responses.activate
    def test_crea_activos_nuevos_cuando_no_hay_nada_local(self):
        _mock_lista([_item(1, "SIS-006", "CENSO")])
        call_command("sincronizar_activos_inventario", url=BASE_URL)

        activo = Activo.objects.get(inventario_id=1)
        assert activo.id_activo == "SIS-006"
        assert activo.nombre == "CENSO"
        assert activo.clasificacion_si == "CONFIDENCIAL"

    @responses.activate
    def test_pagina_hasta_agotar_resultados(self):
        responses.add(responses.GET, f"{BASE_URL}/activos/", json={
            "count": 2, "next": f"{BASE_URL}/activos/?page=2", "previous": None,
            "results": [_item(1, "SIS-001", "A")],
        }, status=200)
        responses.add(responses.GET, f"{BASE_URL}/activos/?page=2", json={
            "count": 2, "next": None, "previous": None,
            "results": [_item(2, "SIS-002", "B")],
        }, status=200)

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.count() == 2

    @responses.activate
    def test_infra_consulta_el_detalle_para_la_ip(self):
        _mock_lista([_item(1, "RED-012", "Servidor Dell", clase="INFRA")])
        _mock_detalle(1, ip="192.168.1.200/24")

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.get(inventario_id=1).ip_principal == "192.168.1.200/24"

    @responses.activate
    def test_sistema_no_consulta_detalle(self):
        """Solo INFRA necesita IP — pedir el detalle de cada SIST/EQUI sería
        tráfico innecesario para un dato que ese serializer no expone."""
        _mock_lista([_item(1, "SIS-006", "CENSO", clase="SIST")])
        call_command("sincronizar_activos_inventario", url=BASE_URL)
        # Si el comando hubiera intentado pedir el detalle, `responses` habría
        # lanzado ConnectionError por no tener ese mock registrado — no lo hizo.
        assert Activo.objects.get(inventario_id=1).nombre == "CENSO"

    @responses.activate
    def test_error_de_conexion_no_lanza_excepcion(self):
        responses.add(responses.GET, f"{BASE_URL}/activos/",
                       body=requests.exceptions.ConnectionError("caído"))
        call_command("sincronizar_activos_inventario", url=BASE_URL)  # no debe lanzar
        assert Activo.objects.count() == 0


class TestCorrelacion:
    @responses.activate
    def test_vincula_por_id_activo_exacto(self, activo):
        activo.id_activo = "RED-012"
        activo.save()
        _sincronizado_previamente(activo)
        _mock_lista([_item(5, "RED-012", "Nombre actualizado desde inventario", clase="INFRA")])
        _mock_detalle(5)

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        activo.refresh_from_db()
        assert activo.inventario_id == 5
        assert activo.nombre == "Nombre actualizado desde inventario"
        assert Activo.objects.count() == 1  # no se creó un duplicado

    @responses.activate
    def test_vincula_por_nombre_normalizado_sin_tildes(self, db):
        a = Activo.objects.create(id_activo="SI-16", nombre="SISTEMA PEDAGÓGICO UAIIN", valor=5)
        _sincronizado_previamente(a)
        _mock_lista([_item(10, "SIS-016", "SISTEMA PEDAGOGICO UAIIN")])  # sin tilde

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.count() == 1
        vinculado = Activo.objects.get(inventario_id=10)
        assert vinculado.id_activo == "SIS-016"

    @responses.activate
    def test_vincula_por_subcadena_como_ultimo_recurso(self, db):
        a = Activo.objects.create(id_activo="SI-15", nombre="KEYCLOAK (IAM/SSO)", valor=5)
        _sincronizado_previamente(a)
        _mock_lista([_item(11, "SIS-015", "KEYCLOAK")])

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.count() == 1
        assert Activo.objects.get(inventario_id=11).id_activo == "SIS-015"

    @responses.activate
    def test_no_fusiona_nombres_genuinamente_distintos(self, db):
        """MOODLE vs MOODEL: un typo real no debe auto-corregirse — mejor un
        duplicado visible y reportado que fusionar dos activos distintos."""
        Activo.objects.create(id_activo="SI-17", nombre="MOODLE", valor=5)
        _mock_lista([_item(12, "SIS-017", "MOODEL")])

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.count() == 2
        assert Activo.objects.filter(inventario_id__isnull=True, id_activo="SI-17").exists()
        assert Activo.objects.get(inventario_id=12).id_activo == "SIS-017"

    @responses.activate
    def test_ya_vinculado_usa_inventario_id_directamente_sin_reevaluar_nombre(self, db):
        """Si el activo ya cambió de nombre en ambos lados tras un vínculo previo,
        la correlación por inventario_id no debe romperse por eso."""
        a = Activo.objects.create(id_activo="SIS-006", nombre="Nombre viejo", inventario_id=25, valor=5)
        _sincronizado_previamente(a)
        _mock_lista([_item(25, "SIS-006", "CENSO — Nombre nuevo")])

        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.count() == 1
        assert Activo.objects.get(inventario_id=25).nombre == "CENSO — Nombre nuevo"


class TestProteccionEdicionesManuales:
    @responses.activate
    def test_activo_editado_manualmente_no_pierde_sus_campos_de_riesgo(self, db):
        activo = Activo.objects.create(id_activo="RED-012", nombre="Servidor", valor=5)
        Activo.objects.filter(pk=activo.pk).update(importado_en=timezone.now() - dt.timedelta(days=1))
        activo.refresh_from_db()
        activo.observacion_critica = "Nota del analista — no debe perderse"
        activo.save()  # actualizado_en queda después de importado_en -> protegido

        _mock_lista([_item(5, "RED-012", "Nombre distinto desde inventario", clase="INFRA")])
        _mock_detalle(5)
        call_command("sincronizar_activos_inventario", url=BASE_URL)

        activo.refresh_from_db()
        assert activo.observacion_critica == "Nota del analista — no debe perderse"
        assert activo.nombre == "Servidor"  # NO se sobrescribió

    @responses.activate
    def test_activo_protegido_igual_queda_vinculado_al_inventario(self, db):
        """El vínculo (inventario_id) se establece siempre, aunque el resto de
        los campos quede protegido — de lo contrario, un activo editado antes de
        la primera sincronización nunca llegaría a vincularse jamás."""
        activo = Activo.objects.create(id_activo="RED-012", nombre="Servidor", valor=5)
        Activo.objects.filter(pk=activo.pk).update(importado_en=timezone.now() - dt.timedelta(days=1))
        activo.refresh_from_db()
        activo.observacion_critica = "Editado"
        activo.save()

        _mock_lista([_item(5, "RED-012", "Otro nombre", clase="INFRA")])
        _mock_detalle(5)
        call_command("sincronizar_activos_inventario", url=BASE_URL)

        activo.refresh_from_db()
        assert activo.inventario_id == 5  # vinculado
        assert activo.nombre == "Servidor"  # pero el resto de campos, protegido

    @responses.activate
    def test_forzar_sobrescritura_ignora_la_proteccion(self, db):
        activo = Activo.objects.create(id_activo="RED-012", nombre="Servidor", valor=5)
        Activo.objects.filter(pk=activo.pk).update(importado_en=timezone.now() - dt.timedelta(days=1))
        activo.refresh_from_db()
        activo.nombre = "Editado a mano"
        activo.save()

        _mock_lista([_item(5, "RED-012", "El inventario gana", clase="INFRA")])
        _mock_detalle(5)
        call_command("sincronizar_activos_inventario", url=BASE_URL, forzar_sobrescritura=True)

        activo.refresh_from_db()
        assert activo.nombre == "El inventario gana"


class TestMapeoClasificacion:
    @responses.activate
    @pytest.mark.parametrize("origen,esperado", [
        ("ALTA", "ALTAMENTE_CONFIDENCIAL"), ("CONF", "CONFIDENCIAL"),
        ("PUB", "PUBLICO"), ("INT", "CONFIDENCIAL"), ("", "DESCONOCIDA"),
    ])
    def test_mapea_clasificacion_si(self, origen, esperado):
        _mock_lista([_item(1, "SIS-001", "x", clasificacion_si=origen)])
        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.get(inventario_id=1).clasificacion_si == esperado

    @responses.activate
    def test_valor_nulo_se_convierte_en_cero(self):
        item = _item(1, "SIS-006", "CENSO")
        item["valor"] = None
        _mock_lista([item])
        call_command("sincronizar_activos_inventario", url=BASE_URL)
        assert Activo.objects.get(inventario_id=1).valor == 0

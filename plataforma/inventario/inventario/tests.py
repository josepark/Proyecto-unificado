import json
import os
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings


class AuthCheckRBACTest(TestCase):
    """Cubre la puerta de autorización (`/api/auth-rbac/`) que nginx usa
    (auth_request) para proteger el módulo SUIIN-RBAC, que no tiene login
    propio por diseño. Si esta prueba se rompe, el acceso a RBAC quedó
    abierto o cerrado para el rol equivocado — ver README-DESPLIEGUE.md
    sección 2."""

    URL = "/api/auth-rbac/"

    @classmethod
    def setUpTestData(cls):
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")

        cls.consultor = User.objects.create_user("consultor_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)

        cls.dinamizador = User.objects.create_user("dinamizador_test", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)

        cls.administrador = User.objects.create_user("admin_test", password="x")
        cls.administrador.groups.add(cls.grupo_admin)

        cls.superusuario = User.objects.create_superuser("super_test", password="x")

    def test_anonimo_no_autorizado(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 401)

    def test_consultor_autorizado_en_get(self):
        self.client.force_login(self.consultor)
        r = self.client.get(self.URL, HTTP_X_ORIGINAL_METHOD="GET")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers.get("X-Usuario-Autorizado"), "consultor_test")

    def test_consultor_no_autorizado_en_escritura(self):
        self.client.force_login(self.consultor)
        r = self.client.get(self.URL, HTTP_X_ORIGINAL_METHOD="POST")
        self.assertEqual(r.status_code, 401)

    def test_dinamizador_autorizado(self):
        self.client.force_login(self.dinamizador)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 204)

    def test_administrador_autorizado(self):
        self.client.force_login(self.administrador)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 204)

    def test_superusuario_autorizado(self):
        self.client.force_login(self.superusuario)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 204)

    def test_respuesta_autorizada_incluye_identidad_para_trazabilidad(self):
        """nginx reenvía este header a RBAC (X-Usuario-SGSI) para que su
        bitácora registre quién hizo cada cambio, en vez de 'operador
        local'. Ver rbac/db.py:_responsable_actual()."""
        self.client.force_login(self.dinamizador)
        r = self.client.get(self.URL)
        self.assertEqual(r.headers.get("X-Usuario-Autorizado"), "dinamizador_test")

    def test_respuesta_no_autorizada_no_incluye_identidad(self):
        r = self.client.get(self.URL)
        self.assertNotIn("X-Usuario-Autorizado", r.headers)

    def test_autoriza_con_cookie_de_sesion_sin_request_user_hidratado(self):
        """Simula la subpetición nginx auth_request: cookie válida en sesión
        Django pero request.user anónimo (DRF no siempre re-hidrata)."""
        sesion = self.client.session
        sesion["_auth_user_id"] = str(self.dinamizador.pk)
        sesion.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = sesion.session_key

        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers.get("X-Usuario-Autorizado"), "dinamizador_test")

    def test_sesion_y_auth_rbac_coinciden_sin_request_user_hidratado(self):
        """GET /api/sesion/ y /api/auth-rbac/ deben usar la misma lectura de sesión."""
        sesion = self.client.session
        sesion["_auth_user_id"] = str(self.dinamizador.pk)
        sesion.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = sesion.session_key

        sesion_api = self.client.get("/api/sesion/")
        auth_api = self.client.get(self.URL)
        self.assertTrue(sesion_api.json()["puede_editar"])
        self.assertEqual(auth_api.status_code, 204)

    def test_autoriza_si_request_session_vacia_pero_cookie_valida(self):
        """request.session puede no tener _auth_user_id aunque la cookie siga válida."""
        sesion = SessionStore()
        sesion["_auth_user_id"] = str(self.administrador.pk)
        sesion.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = sesion.session_key

        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers.get("X-Usuario-Autorizado"), "admin_test")


class PanelEjecutivoUnificadoTest(TestCase):
    """El Panel ejecutivo consolida indicadores propios del Inventario con
    los KPIs de RBAC (llamada servidor-a-servidor, ver
    inventario/views.py:_resumen_rbac). Debe degradar con gracia si RBAC
    no responde, en vez de tumbar el panel completo."""

    URL = "/api/dashboard-ejecutivo/"

    def test_incluye_clave_rbac(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        self.assertIn("rbac", r.json())

    def test_degrada_con_gracia_si_rbac_no_responde(self):
        import requests
        from unittest.mock import patch

        with patch("inventario.integracion_rbac.requests.get",
                   side_effect=requests.RequestException("no disponible")):
            r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["rbac"])

    def test_incluye_los_kpis_de_rbac_cuando_responde(self):
        from unittest.mock import patch, MagicMock

        resumen_falso = {
            "roles_total": 27, "sistemas_total": 30, "usuarios_activos": 11,
            "mfa_pct": 100, "mfa_ok": 6, "mfa_total": 6,
            "proximos_vencimientos": 0, "excepciones_vigentes": 37,
            "excepciones_vencidas": 0, "roles_certificacion_vencida": 27,
            "pendientes_total": 27,
            "desglose_pendientes": {
                "proximos_vencimientos": 0,
                "excepciones_vencidas": 0,
                "roles_certificacion_vencida": 27,
                "alertas_mfa": 0,
            },
        }
        respuesta_falsa = MagicMock()
        respuesta_falsa.json.return_value = resumen_falso
        respuesta_falsa.raise_for_status.return_value = None

        with patch("inventario.integracion_rbac.requests.get", return_value=respuesta_falsa):
            r = self.client.get(self.URL)
        self.assertEqual(r.json()["rbac"], resumen_falso)

    def test_incluye_vinculacion_inventario_riesgos(self):
        from unittest.mock import patch

        vinc_falsa = {
            "disponible": True,
            "total_inventario": 38,
            "vinculados": 36,
            "sin_espejo_riesgos": 2,
            "huerfanos_riesgos": 0,
        }
        with patch("inventario.views._resumen_vinculacion", return_value=vinc_falsa):
            r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["vinculacion"], vinc_falsa)


class IntegracionRiesgosOla7Test(TestCase):
    """Ola 7 — vinculación en panel ejecutivo y reporte consolidado."""

    URL_PANEL = "/api/dashboard-ejecutivo/"

    @classmethod
    def setUpTestData(cls):
        from .models import Activo
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("ola7_reporte", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)
        cls.activo = Activo.objects.create(
            nombre="Activo reporte", clase="INFRA", clasificacion_si="INT",
            nivel_riesgo="MED",
        )

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def test_reporte_pdf_incluye_sincronizacion(self):
        from unittest.mock import patch

        vinc_falsa = {
            "disponible": True,
            "total_inventario": 1,
            "vinculados": 0,
            "sin_espejo_riesgos": 1,
            "huerfanos_riesgos": 0,
        }
        with patch("inventario.reporte_consolidado.inicio_rbac", return_value=None), \
             patch("inventario.views._resumen_vinculacion", return_value=vinc_falsa):
            r = self.client.get("/api/reporte-consolidado.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"sin espejo", r.content.lower())


class CruceRBACSistemaTest(TestCase):
    """Cruce en vivo (por nombre) entre `sistema_mca_equivalente` del
    Inventario y el catálogo canónico de RBAC — reemplaza la dependencia
    exclusiva de la copia local (RolMCA/AccesoRol), que se llena a mano y
    puede desactualizarse. Ver inventario/integracion_rbac.py."""

    @classmethod
    def setUpTestData(cls):
        from .models import Activo, SistemaInformacion
        cls.activo = Activo.objects.create(
            nombre="Sistema de Nómina", clase="SIST",
            clasificacion_si="CONF", estado="ACT")
        cls.sistema =         SistemaInformacion.objects.create(
            activo=cls.activo, estado_operativo="OP",
            sistema_mca_equivalente="Nómina y Contratación")
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("cruce_rbac_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)

    def setUp(self):
        self.client.force_login(self.consultor)

    def _detalle(self):
        return self.client.get(f"/api/activos/{self.activo.id}/")

    def test_sin_rbac_disponible_devuelve_none_y_avisa(self):
        from unittest.mock import patch
        import requests

        with patch("inventario.integracion_rbac.requests.get",
                   side_effect=requests.RequestException("no disponible")):
            r = self._detalle()
        self.assertIsNone(r.json()["sistema"]["accesos_rbac"])

    def test_con_coincidencia_devuelve_los_accesos_reales(self):
        from unittest.mock import patch, MagicMock

        catalogo_falso = [
            {"id": 1, "nombre": "Nómina y Contratación", "categoria": "RRHH",
             "clasificacion": "Confidencial",
             "accesos": [{"rol": "DTG", "denominacion": "Dinamizador Tecnólogo", "nivel": "A"}]},
            {"id": 2, "nombre": "Otro Sistema", "categoria": "X",
             "clasificacion": "Interna", "accesos": []},
        ]
        respuesta_falsa = MagicMock()
        respuesta_falsa.json.return_value = catalogo_falso
        respuesta_falsa.raise_for_status.return_value = None

        with patch("inventario.integracion_rbac.requests.get", return_value=respuesta_falsa):
            r = self._detalle()
        self.assertEqual(r.json()["sistema"]["accesos_rbac"],
                         catalogo_falso[0]["accesos"])

    def test_sin_coincidencia_devuelve_none(self):
        from unittest.mock import patch, MagicMock

        catalogo_falso = [{"id": 9, "nombre": "Sistema Totalmente Distinto",
                           "categoria": "X", "clasificacion": "Interna", "accesos": []}]
        respuesta_falsa = MagicMock()
        respuesta_falsa.json.return_value = catalogo_falso
        respuesta_falsa.raise_for_status.return_value = None

        with patch("inventario.integracion_rbac.requests.get", return_value=respuesta_falsa):
            r = self._detalle()
        self.assertIsNone(r.json()["sistema"]["accesos_rbac"])


class EquipoComputoTest(TestCase):
    """Registro de equipos de cómputo (escritorio/portátil) como una
    tercera clase de activo, junto a Infraestructura y Sistema de
    información — con su propio detalle (custodia, postura de seguridad
    del endpoint, ciclo de vida de garantía)."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("equipo_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def _payload(self, **extra):
        body = {
            "nombre": "Portátil de Coordinación TI",
            "clase": "EQUI",
            "clasificacion_si": "INT",
            "equipo": {
                "tipo_equipo": "PORT",
                "marca": "Dell",
                "modelo": "Latitude 5440",
                "serial": "SN-EQUIPO-001",
                "mac_address": "AA:BB:CC:DD:EE:01",
                "usuario_asignado": "María Fernanda Yule",
                "ubicacion_fisica": "Sede Popayán",
                "sistema_operativo": "Windows 11 Pro",
                "ram_gb": 16,
                "almacenamiento": "512GB SSD",
                "antivirus_edr": "Microsoft Defender for Endpoint",
                "cifrado_disco": True,
                "unido_a_dominio": True,
                "fin_garantia": "2027-01-15",
            },
        }
        body.update(extra)
        return body

    def test_crear_activo_equi_genera_codigo_con_prefijo_pc(self):
        r = self.client.post("/api/activos/", self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()["id_activo"].startswith("PC-"))

    def test_detalle_incluye_los_datos_del_equipo(self):
        r = self.client.post("/api/activos/", self._payload(), content_type="application/json")
        activo_id = r.json()["id"]
        det = self.client.get(f"/api/activos/{activo_id}/").json()
        self.assertEqual(det["equipo"]["marca"], "Dell")
        self.assertEqual(det["equipo"]["serial"], "SN-EQUIPO-001")
        self.assertTrue(det["equipo"]["cifrado_disco"])
        self.assertEqual(det["equipo"]["tipo_equipo_display"], "Portatil / Laptop")

    def test_editar_actualiza_el_equipo_existente(self):
        r = self.client.post("/api/activos/", self._payload(), content_type="application/json")
        activo_id = r.json()["id"]
        r2 = self.client.patch(f"/api/activos/{activo_id}/",
                               {"equipo": {"usuario_asignado": "Nuevo Custodio"}},
                               content_type="application/json")
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.json()["equipo"]["usuario_asignado"], "Nuevo Custodio")
        # el resto de los datos del equipo no se pierde con un PATCH parcial
        self.assertEqual(r2.json()["equipo"]["marca"], "Dell")

    def test_anonimo_no_puede_crear_equipo(self):
        self.client.logout()
        r = self.client.post("/api/activos/", self._payload(), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_equipo_con_garantia_vencida_aparece_en_alertas(self):
        payload = self._payload()
        payload["equipo"]["fin_garantia"] = "2020-01-01"  # claramente vencida
        r = self.client.post("/api/activos/", payload, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)

        alertas = self.client.get("/api/alertas/").json()
        grupo = next(g for g in alertas["grupos"] if g["clave"] == "garantia")
        ids = {i["id_activo"] for i in grupo["items"]}
        self.assertIn(r.json()["id_activo"], ids)

    def test_estadisticas_cuenta_equi_en_por_clase(self):
        self.client.post("/api/activos/", self._payload(), content_type="application/json")
        est = self.client.get("/api/activos/estadisticas/").json()
        self.assertGreaterEqual(est["por_clase"].get("EQUI", 0), 1)
        self.assertIn("clases", est)


class ClaseActivoDinamicaTest(TestCase):
    """Catálogo configurable de clases y metadatos para la SPA."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("clases_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def test_meta_expone_clases_y_datacenter(self):
        r = self.client.get("/api/activos/meta/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("clases", data)
        self.assertGreaterEqual(len(data["clases"]), 3)
        self.assertIn("INFRA", data["colores_clase"])
        self.assertIn("tipos", data["datacenter"])

    def test_crear_clase_generica_y_activo_con_detalle_json(self):
        from inventario.models import ClaseActivo
        cr = self.client.post("/api/clases-activo/", {
            "codigo": "SERV", "nombre": "Servicio cloud", "prefijo_id": "SRV",
            "color": "#0ea5e9", "orden": 10, "modelo_detalle": "generico",
        }, content_type="application/json")
        self.assertEqual(cr.status_code, 201, cr.content)
        ar = self.client.post("/api/activos/", {
            "nombre": "Bucket S3 auditoría",
            "clase": "SERV",
            "detalle_extra": {"proveedor": "AWS", "region": "us-east-1"},
        }, content_type="application/json")
        self.assertEqual(ar.status_code, 201, ar.content)
        self.assertTrue(ar.json()["id_activo"].startswith("SRV-"))
        ClaseActivo.objects.filter(codigo="SERV").delete()

    def test_rechaza_bloque_detalle_incompatible_con_clase(self):
        r = self.client.post("/api/activos/", {
            "nombre": "Incoherente",
            "clase": "SIST",
            "infraestructura": {"tipo": "Switch"},
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)


class Ola2ArquitecturaDatosTest(TestCase):
    """Ola 2: racks, esquema dinámico, vínculo RBAC por ID."""

    @classmethod
    def setUpTestData(cls):
        from inventario.models import ClaseActivo, Datacenter, Rack
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("ola2_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)
        cls.dc_a = Datacenter.objects.create(codigo="BOG1", nombre="Bogotá principal")
        cls.dc_b = Datacenter.objects.create(codigo="MED1", nombre="Medellín")
        cls.rack_a = Rack.objects.create(datacenter=cls.dc_a, codigo="A01", capacidad_u=42)
        cls.rack_b = Rack.objects.create(datacenter=cls.dc_b, codigo="B01", capacidad_u=42)
        ClaseActivo.objects.filter(codigo="SERV").delete()
        ClaseActivo.objects.create(
            codigo="SERV", nombre="Servicio", prefijo_id="SRV", modelo_detalle="generico",
            detalle_schema={"campos": [
                {"nombre": "proveedor", "tipo": "texto", "requerido": True},
                {"nombre": "region", "tipo": "opciones", "opciones": ["us-east-1", "sa-east-1"]},
            ]},
        )

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def test_valida_detalle_extra_contra_esquema(self):
        r = self.client.post("/api/activos/", {
            "nombre": "Bucket",
            "clase": "SERV",
            "detalle_extra": {"region": "us-east-1"},
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("proveedor", str(r.json()))

        r2 = self.client.post("/api/activos/", {
            "nombre": "Bucket OK",
            "clase": "SERV",
            "detalle_extra": {"proveedor": "AWS", "region": "us-east-1"},
        }, content_type="application/json")
        self.assertEqual(r2.status_code, 201, r2.content)

    def test_rechaza_rack_de_otro_datacenter(self):
        r = self.client.post("/api/activos/", {
            "nombre": "Switch core",
            "clase": "INFRA",
            "datacenter": self.dc_a.id,
            "infraestructura": {
                "tipo": "Switch",
                "rack_fk": self.rack_b.id,
                "unidad_inicio": 10,
                "unidad_fin": 11,
            },
        }, content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("rack_fk", str(r.json()))

    def test_accesos_rbac_por_sistema_rbac_id(self):
        from inventario.models import Activo, SistemaInformacion
        from unittest.mock import patch, MagicMock

        activo = Activo.objects.create(
            nombre="Portal", clase="SIST", clasificacion_si="CONF", estado="ACT")
        SistemaInformacion.objects.create(
            activo=activo, sistema_rbac_id=42, sistema_mca_equivalente="Nombre distinto")

        catalogo = [
            {"id": 42, "nombre": "Portal académico", "categoria": "X",
             "clasificacion": "Interna",
             "accesos": [{"rol": "DTG", "denominacion": "Dinamizador", "nivel": "C"}]},
        ]
        respuesta = MagicMock()
        respuesta.json.return_value = catalogo
        respuesta.raise_for_status.return_value = None

        with patch("inventario.integracion_rbac.requests.get", return_value=respuesta):
            r = self.client.get(f"/api/activos/{activo.id}/")
        self.assertEqual(r.status_code, 200)
        sis = r.json()["sistema"]
        self.assertEqual(sis["accesos_rbac"], catalogo[0]["accesos"])
        self.assertEqual(sis["sistema_rbac_nombre"], "Portal académico")

    def test_infra_sin_rack_genera_alerta(self):
        from inventario.models import Activo, ActivoInfraestructura
        a = Activo.objects.create(
            nombre="Router borde", clase="INFRA", datacenter=self.dc_a, estado="ACT")
        ActivoInfraestructura.objects.create(activo=a, tipo="Router")
        r = self.client.get("/api/alertas/")
        self.assertEqual(r.status_code, 200)
        grupos = {g["clave"]: g for g in r.json()["grupos"]}
        ids = [i["id_activo"] for i in grupos["sin_rack"]["items"]]
        self.assertIn(a.id_activo, ids)

    def test_datacenter_expone_racks(self):
        r = self.client.get(f"/api/datacenters/{self.dc_a.id}/racks/")
        self.assertEqual(r.status_code, 200)
        codigos = [x["codigo"] for x in r.json()]
        self.assertIn("A01", codigos)


class Ola4RacksLegacyTest(TestCase):
    """Ola 4: migración texto → rack_fk y utilidades de parsing."""

    @classmethod
    def setUpTestData(cls):
        from inventario.models import Activo, ActivoInfraestructura, Datacenter, Rack
        cls.dc = Datacenter.objects.create(codigo="TST1", nombre="Test DC")
        cls.rack = Rack.objects.create(datacenter=cls.dc, codigo="2", capacidad_u=42)
        cls.activo = Activo.objects.create(
            nombre="Switch legacy", clase="INFRA", datacenter=cls.dc, estado="ACT")
        cls.inf = ActivoInfraestructura.objects.create(
            activo=cls.activo, tipo="Switch", rack="Rack 2", unidad_rack="U10-U11")

    def test_parse_unidad_rack(self):
        from inventario.rack_utils import parse_unidad_rack
        self.assertEqual(parse_unidad_rack("U20-U21"), (20, 21))
        self.assertEqual(parse_unidad_rack("U40"), (40, 40))

    def test_migrar_racks_legacy_vincula_por_texto(self):
        from io import StringIO
        from django.core.management import call_command
        from inventario.models import ActivoInfraestructura

        call_command("migrar_racks_legacy", stdout=StringIO())
        inf = ActivoInfraestructura.objects.get(pk=self.inf.pk)
        self.assertEqual(inf.rack_fk_id, self.rack.id)
        self.assertEqual(inf.unidad_inicio, 10)
        self.assertEqual(inf.unidad_fin, 11)

    def test_migrar_crea_rack_con_flag(self):
        from io import StringIO
        from django.core.management import call_command
        from inventario.models import Activo, ActivoInfraestructura, Rack

        a2 = Activo.objects.create(
            nombre="Otro", clase="INFRA", datacenter=self.dc, estado="ACT")
        ActivoInfraestructura.objects.create(
            activo=a2, rack="Rack NUEVO", unidad_rack="U5")
        call_command("migrar_racks_legacy", crear_faltantes=True, stdout=StringIO())
        inf = ActivoInfraestructura.objects.get(activo=a2)
        self.assertIsNotNone(inf.rack_fk_id)
        self.assertTrue(Rack.objects.filter(datacenter=self.dc, codigo="NUEVO").exists())


class RiesgoCruzadoTest(TestCase):
    """Correlación de riesgo cruzado (Alertas): un activo con riesgo
    Crítico/Alto que además tiene excepciones de acceso vigentes en RBAC
    es una señal que ninguna de las dos apps ve por separado — ver
    inventario/views.py:alertas()."""

    URL = "/api/alertas/"

    @classmethod
    def setUpTestData(cls):
        from .models import Activo, SistemaInformacion
        cls.activo_critico = Activo.objects.create(
            nombre="Core Financiero", clase="SIST", clasificacion_si="ALTA",
            estado="ACT", nivel_riesgo="CRIT")
        SistemaInformacion.objects.create(
            activo=cls.activo_critico, estado_operativo="OP",
            sistema_mca_equivalente="Sistema Financiero SUIIN")

        # Activo de riesgo bajo — no debe aparecer aunque tenga excepciones.
        cls.activo_bajo = Activo.objects.create(
            nombre="Portal público", clase="SIST", clasificacion_si="PUB",
            estado="ACT", nivel_riesgo="BAJO")
        SistemaInformacion.objects.create(
            activo=cls.activo_bajo, estado_operativo="OP",
            sistema_mca_equivalente="Portal Público")
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("riesgo_cruzado_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)

    def setUp(self):
        self.client.force_login(self.consultor)

    def _catalogo_falso(self):
        return [
            {"id": 1, "nombre": "Sistema Financiero SUIIN", "categoria": "FIN",
             "clasificacion": "Confidencial", "accesos": [], "excepciones_vigentes": 3},
            {"id": 2, "nombre": "Portal Público", "categoria": "WEB",
             "clasificacion": "Publica", "accesos": [], "excepciones_vigentes": 2},
        ]

    def test_activo_critico_con_excepciones_aparece_en_riesgo_cruzado(self):
        from unittest.mock import patch

        with patch("inventario.views.catalogo_sistemas_rbac", return_value=self._catalogo_falso()):
            r = self.client.get(self.URL)
        grupo = next((g for g in r.json()["grupos"] if g["clave"] == "riesgo_cruzado"), None)
        self.assertIsNotNone(grupo)
        ids = {i["id_activo"] for i in grupo["items"]}
        self.assertIn(self.activo_critico.id_activo, ids)
        self.assertEqual(next(i for i in grupo["items"]
                              if i["id_activo"] == self.activo_critico.id_activo)["severidad"], "crit")

    def test_activo_de_riesgo_bajo_no_aparece_aunque_tenga_excepciones(self):
        from unittest.mock import patch

        with patch("inventario.views.catalogo_sistemas_rbac", return_value=self._catalogo_falso()):
            r = self.client.get(self.URL)
        grupo = next((g for g in r.json()["grupos"] if g["clave"] == "riesgo_cruzado"), None)
        ids = {i["id_activo"] for i in (grupo["items"] if grupo else [])}
        self.assertNotIn(self.activo_bajo.id_activo, ids)

    def test_sin_rbac_disponible_no_rompe_las_demas_alertas(self):
        from unittest.mock import patch

        with patch("inventario.views.catalogo_sistemas_rbac", return_value=None):
            r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        grupo = next((g for g in r.json()["grupos"] if g["clave"] == "riesgo_cruzado"), None)
        self.assertIsNone(grupo)  # el grupo se omite si no tiene items, no rompe la respuesta


class EndurecimientoLoginTest(TestCase):
    """django-axes: bloquea el login tras repetidos intentos fallidos. Desde
    la unificación, este login protege el acceso a los dos módulos
    (Inventario y, a través de él, RBAC), así que vale la pena endurecerlo
    — ver README-DESPLIEGUE.md sección 8.9."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("endurecimiento_test", password="claveCorrecta123")
    def setUp(self):
        # django-axes guarda los intentos en base de datos, no en memoria;
        # cada prueba parte de un estado limpio.
        from axes.models import AccessAttempt
        AccessAttempt.objects.all().delete()

    def test_intentos_por_debajo_del_limite_no_bloquean(self):
        from django.conf import settings
        for _ in range(settings.AXES_FAILURE_LIMIT - 1):
            r = self.client.post("/login/", {"username": "endurecimiento_test",
                                             "password": "claveMALA"})
            self.assertEqual(r.status_code, 200)  # formulario con error, no bloqueo

    def test_supera_el_limite_bloquea_incluso_con_clave_correcta(self):
        from django.conf import settings
        for _ in range(settings.AXES_FAILURE_LIMIT):
            self.client.post("/login/", {"username": "endurecimiento_test",
                                         "password": "claveMALA"})
        r = self.client.post("/login/", {"username": "endurecimiento_test",
                                         "password": "claveCorrecta123"})
        self.assertEqual(r.status_code, 429)

    def test_login_correcto_resetea_el_contador(self):
        """AXES_RESET_ON_SUCCESS=True: un login exitoso limpia los intentos
        fallidos previos, para no penalizar a alguien que solo se equivocó
        una vez tecleando la contraseña."""
        self.client.post("/login/", {"username": "endurecimiento_test",
                                     "password": "claveMALA"})
        r = self.client.post("/login/", {"username": "endurecimiento_test",
                                         "password": "claveCorrecta123"})
        self.assertEqual(r.status_code, 302)  # login exitoso, redirect normal


class ApiLoginTest(TestCase):
    """Login JSON para la SPA (/api/auth/login/) — misma protección django-axes."""

    URL = "/api/auth/login/"

    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("api_login_test", password="claveCorrecta123")

    def setUp(self):
        from axes.models import AccessAttempt
        AccessAttempt.objects.all().delete()

    def test_credenciales_validas_abre_sesion(self):
        r = self.client.post(
            self.URL,
            {"username": "api_login_test", "password": "claveCorrecta123"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["autenticado"])
        self.assertEqual(r.json()["usuario"], "api_login_test")

    def test_credenciales_invalidas_devuelve_401(self):
        r = self.client.post(
            self.URL,
            {"username": "api_login_test", "password": "mala"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_supera_el_limite_bloquea_incluso_con_clave_correcta(self):
        from django.conf import settings
        for _ in range(settings.AXES_FAILURE_LIMIT):
            self.client.post(
                self.URL,
                {"username": "api_login_test", "password": "claveMALA"},
                content_type="application/json",
            )
        r = self.client.post(
            self.URL,
            {"username": "api_login_test", "password": "claveCorrecta123"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 429)


class _ActivoFalso:
    """Doble liviano de Activo para probar deteccion_diagramas.py sin
    necesidad de tocar la base de datos."""
    _contador = 0

    def __init__(self, id_activo, nombre):
        _ActivoFalso._contador += 1
        self.id = _ActivoFalso._contador
        self.id_activo = id_activo
        self.nombre = nombre


class DeteccionDiagramasTest(TestCase):
    """Detección automática de activos mencionados en un diagrama SVG —
    'Correlación de riesgo cruzado' empieza por tener buenos datos de
    relación activo↔diagrama sin que capturarlos a mano sea tedioso."""

    SVG_EJEMPLO = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
        b'<text x="0" y="0">Topologia SUIIN - CRIC (ejemplo)</text>'
        b'<text x="0" y="0">pfSense FW</text>'
        b'<text x="0" y="0">Proxmox R740</text>'
        b'<text x="0" y="0">Oracle DB</text>'
        b'</svg>')

    def test_extraer_textos_svg_valido(self):
        from .deteccion_diagramas import extraer_textos_svg
        textos = extraer_textos_svg(self.SVG_EJEMPLO)
        self.assertIn("pfSense FW", textos)
        self.assertIn("Proxmox R740", textos)
        self.assertEqual(len(textos), 4)

    def test_extraer_textos_svg_invalido_no_lanza_excepcion(self):
        from .deteccion_diagramas import extraer_textos_svg
        self.assertEqual(extraer_textos_svg(b"esto no es xml <<<"), [])
        self.assertEqual(extraer_textos_svg(b""), [])

    def test_es_svg(self):
        from .deteccion_diagramas import es_svg
        self.assertTrue(es_svg("topologia.svg"))
        self.assertFalse(es_svg("plano.pdf"))
        self.assertFalse(es_svg("foto.png"))

    def test_sugiere_activos_por_nombre_parcial(self):
        """'pfSense FW' debe encontrar el activo cuyo nombre contiene
        'pfSense', aunque el resto del nombre no se parezca en nada."""
        from .deteccion_diagramas import sugerir_activos
        activos = [
            _ActivoFalso("RED-003", "Firewall — Netgate pfSense NG Firewall"),
            _ActivoFalso("SIS-010", "Contratación"),
        ]
        sugerencias = sugerir_activos(self.SVG_EJEMPLO, activos)
        ids = {s["id_activo"] for s in sugerencias}
        self.assertIn("RED-003", ids)
        self.assertNotIn("SIS-010", ids)

    def test_prioriza_coincidencia_de_modelo_especifico(self):
        """Entre varios servidores Proxmox, el que además coincide en el
        número de modelo (R740) debe quedar mejor puntuado que los que
        solo comparten la marca."""
        from .deteccion_diagramas import sugerir_activos
        activos = [
            _ActivoFalso("RED-012", "Servidor Dell EMC PowerEdge R740 (Proxmox)"),
            _ActivoFalso("RED-013", "Servidor Dell EMC PowerEdge R420 (Proxmox Backups)"),
        ]
        sugerencias = sugerir_activos(self.SVG_EJEMPLO, activos)
        por_id = {s["id_activo"]: s["confianza"] for s in sugerencias}
        self.assertGreater(por_id["RED-012"], por_id["RED-013"])

    def test_no_sugiere_por_boilerplate_institucional(self):
        """'SUIIN' aparece en el título de cualquier diagrama — no debe
        bastar por sí solo para sugerir una relación."""
        from .deteccion_diagramas import sugerir_activos
        activos = [_ActivoFalso("RED-015", "VM — Open Media Vault (NAS/Almacenamiento SUIIN)")]
        sugerencias = sugerir_activos(self.SVG_EJEMPLO, activos)
        self.assertEqual(sugerencias, [])

    def test_coincidencia_exacta_de_id_activo_puntua_maximo(self):
        from .deteccion_diagramas import sugerir_activos
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><text>RED-099</text></svg>'
        activos = [_ActivoFalso("RED-099", "Cualquier nombre, no importa")]
        sugerencias = sugerir_activos(svg, activos)
        self.assertEqual(sugerencias[0]["confianza"], 1.0)

    def test_sin_texto_no_sugiere_nada(self):
        from .deteccion_diagramas import sugerir_activos
        svg_vacio = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        activos = [_ActivoFalso("RED-001", "Cualquiera")]
        self.assertEqual(sugerir_activos(svg_vacio, activos), [])


class CookieCSRFSeguraSegunTLSTest(TestCase):
    """Bug real detectado al construir el cliente API de React: con
    DEBUG=False (producción) y sin TLS todavía (el estado actual del
    despliegue, DJANGO_SSL_REDIRECT=False según .env.example),
    CSRF_COOKIE_SECURE quedaba en True sin condición — el navegador
    descarta cookies Secure sobre HTTP plano, así que la cookie csrftoken
    nunca llegaba a guardarse y todo POST/PUT/DELETE del Inventario (JS
    existente y el nuevo cliente de React por igual) se rechazaba con 403.
    Ahora Secure sigue al mismo indicador que ya gobierna la redirección a
    HTTPS (DJANGO_SSL_REDIRECT), en vez de a DEBUG solo. Se prueba
    ejecutando settings.py en un proceso aparte con cada combinación de
    variables de entorno, porque una vez que Django carga la
    configuración no se puede recomputar en el mismo proceso."""

    def _cookie_secura(self, ssl_redirect):
        import subprocess
        peticion = (
            "c.get('/', secure=True)" if ssl_redirect == "True"
            else "c.get('/')"
        )
        codigo = (
            "import os, django;"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');"
            "django.setup();"
            "from django.test import Client;"
            "c = Client(HTTP_X_FORWARDED_PROTO='https');"
            f"r = {peticion};"
            "m = r.cookies.get('csrftoken');"
            "print(repr(m['secure']) if m else 'SIN_COOKIE')"
        )
        entorno = dict(os.environ, DJANGO_ALLOWED_HOSTS="testserver,localhost,127.0.0.1",
                       DJANGO_DEBUG="False", DJANGO_SSL_REDIRECT=ssl_redirect,
                       DJANGO_SECRET_KEY="clave-de-prueba-solo-para-este-subproceso",
                       JWT_SHARED_SECRET="jwt-de-prueba-solo-para-este-subproceso")
        resultado = subprocess.run(
            ["python3", "-c", codigo], env=entorno, capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return resultado.stdout.strip()

    def test_sin_tls_la_cookie_no_queda_secure(self):
        """Estado actual real del despliegue (sección 6 del README: TLS
        real sigue pendiente) — la cookie debe poder guardarse sobre
        HTTP plano."""
        self.assertEqual(self._cookie_secura("False"), "''")

    def test_con_tls_la_cookie_si_queda_secure(self):
        """Cuando se implemente TLS (próximo paso), la cookie vuelve a
        exigir Secure, como corresponde."""
        self.assertEqual(self._cookie_secura("True"), "True")


class ActivoDetailDisplayTest(TestCase):
    """El endpoint de detalle (/api/activos/{id}/) debe traer las mismas
    etiquetas legibles que ya trae el listado — la ficha de React (Fase 1
    de la migración) las muestra directamente, sin traducir códigos."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("detalle_test_cons", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)

    def setUp(self):
        self.client.force_login(self.consultor)

    def test_detalle_incluye_etiquetas_legibles(self):
        from .models import Activo
        a = Activo.objects.create(
            nombre="Activo de prueba", clase="INFRA",
            clasificacion_si="ALTA", nivel_riesgo="CRIT")
        r = self.client.get(f"/api/activos/{a.pk}/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["clase_display"], "Infraestructura de red")
        self.assertEqual(d["clasificacion_si_display"], "Altamente Confidencial")
        self.assertEqual(d["nivel_riesgo_display"], "Critico")
        self.assertIn("estado_display", d)
        self.assertIn("ciclo_vida_display", d)

    def test_detalle_con_infraestructura_no_falla(self):
        from .models import Activo, ActivoInfraestructura, Datacenter, Rack
        dc = Datacenter.objects.create(codigo="DC-TEST", nombre="Test DC")
        rack = Rack.objects.create(datacenter=dc, codigo="1", capacidad_u=42)
        a = Activo.objects.create(
            nombre="Servidor con infra", clase="INFRA",
            clasificacion_si="INT", nivel_riesgo="MED", datacenter=dc,
        )
        ActivoInfraestructura.objects.create(
            activo=a, rack_fk=rack, unidad_inicio=10, unidad_fin=12,
        )
        r = self.client.get(f"/api/activos/{a.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["infraestructura"]["rack_codigo"], "1")


class EtiquetaActivoTest(TestCase):
    """Etiqueta adhesiva (70x40mm) para pegar en el activo físico, en
    formato individual y de impresión masiva — ver README-DESPLIEGUE.md."""

    @classmethod
    def setUpTestData(cls):
        from .models import Activo
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("etiqueta_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)
        cls.a1 = Activo.objects.create(
            nombre="Servidor de prueba para etiqueta", clase="INFRA",
            clasificacion_si="INT")
        cls.a2 = Activo.objects.create(
            nombre="Segundo activo de prueba", clase="SIST",
            clasificacion_si="INT")

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def test_etiqueta_individual_devuelve_un_pdf(self):
        r = self.client.get(f"/api/activos/{self.a1.pk}/etiqueta.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_etiqueta_no_revela_clasificacion_ni_riesgo(self):
        """La etiqueta es visible físicamente en el equipo — no debe
        anunciar su clasificación de seguridad ni su nivel de riesgo."""
        activo_critico = type(self.a1).objects.create(
            nombre="Activo con datos sensibles", clase="SIST",
            clasificacion_si="ALTA", nivel_riesgo="CRIT")
        r = self.client.get(f"/api/activos/{activo_critico.pk}/etiqueta.pdf")
        contenido = r.content
        self.assertNotIn(b"Altamente Confidencial", contenido)
        self.assertNotIn(b"Critico", contenido)
        self.assertNotIn(b"Cr\xc3\xadtico", contenido)

    def test_etiqueta_lote_sin_ids_da_400(self):
        r = self.client.get("/api/etiquetas/lote.pdf")
        self.assertEqual(r.status_code, 400)

    def test_etiqueta_lote_ids_invalidos_da_400(self):
        r = self.client.get("/api/etiquetas/lote.pdf?ids=abc,,")
        self.assertEqual(r.status_code, 400)

    def test_etiqueta_lote_genera_una_pagina_por_activo(self):
        import re
        r = self.client.get(
            f"/api/etiquetas/lote.pdf?ids={self.a1.pk},{self.a2.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        paginas = re.findall(rb"/Type /Page[^s]", r.content)
        self.assertEqual(len(paginas), 2)

    def test_etiqueta_lote_ignora_ids_inexistentes_pero_conserva_validos(self):
        import re
        r = self.client.get(f"/api/etiquetas/lote.pdf?ids=999999,{self.a1.pk}")
        self.assertEqual(r.status_code, 200)
        paginas = re.findall(rb"/Type /Page[^s]", r.content)
        self.assertEqual(len(paginas), 1)


class ResumenAlertasEmailTest(TestCase):
    """Comando enviar_resumen_alertas — notificaciones proactivas por
    correo (antes las alertas eran enteramente "pull": solo se veían si
    alguien entraba a mirar la pestaña). Se simula inicio_rbac() porque
    hace una llamada HTTP real a RBAC; el resto usa datos reales de la
    base de datos de prueba, igual que las demás pruebas del Inventario."""

    @classmethod
    def setUpTestData(cls):
        from datetime import date, timedelta

        from .models import Activo, ActivoInfraestructura
        a = Activo.objects.create(
            nombre="Firewall de prueba para alertas", clase="INFRA",
            clasificacion_si="ALTA", nivel_riesgo="CRIT")
        ActivoInfraestructura.objects.create(
            activo=a, fin_soporte_eol=date.today() - timedelta(days=10))
        cls.activo_vencido = a

    def _limpiar_config_correo(self):
        from django.conf import settings
        from django.core import mail
        mail.outbox = []
        settings.ALERTAS_EMAIL_DESTINATARIOS = ["seguridad@cric.org.co"]
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    def test_sin_destinatarios_configurados_no_envia_nada(self):
        from django.conf import settings
        from django.core import mail
        from django.core.management import call_command
        settings.ALERTAS_EMAIL_DESTINATARIOS = []
        call_command("enviar_resumen_alertas")
        self.assertEqual(len(mail.outbox), 0)

    def test_envia_correo_con_las_alertas_reales_del_inventario(self):
        from unittest.mock import patch

        from django.core import mail
        from django.core.management import call_command
        self._limpiar_config_correo()
        with patch("inventario.management.commands.enviar_resumen_alertas.inicio_rbac",
                   return_value=None):
            call_command("enviar_resumen_alertas")
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ["seguridad@cric.org.co"])
        self.assertIn("crítica", correo.subject.lower())
        # el activo con EOL vencido que se creó en setUpTestData debe aparecer
        self.assertIn(self.activo_vencido.id_activo, correo.body)
        # tiene version HTML ademas de texto plano
        self.assertEqual(correo.alternatives[0][1], "text/html")
        self.assertIn(self.activo_vencido.id_activo, correo.alternatives[0][0])

    def test_si_rbac_no_responde_lo_indica_sin_romper_el_envio(self):
        from unittest.mock import patch

        from django.core import mail
        from django.core.management import call_command
        self._limpiar_config_correo()
        with patch("inventario.management.commands.enviar_resumen_alertas.inicio_rbac",
                   return_value=None):
            call_command("enviar_resumen_alertas")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("no se pudo consultar rbac", mail.outbox[0].body.lower())

    def test_incluye_vencimientos_y_alertas_mfa_reales_de_rbac(self):
        from unittest.mock import patch

        from django.core import mail
        from django.core.management import call_command
        self._limpiar_config_correo()
        rbac_simulado = {
            "mfa_pct": 80, "mfa_ok": 4, "mfa_total": 5, "dias_alerta": 7,
            "proximos_vencimientos": [
                {"tipo": "Usuario temporal", "nombre": "Persona De Prueba",
                 "contexto": "DTG", "fecha_fin": "2026-08-15", "dias": 3},
            ],
            "alertas_mfa": [{"nombre": "Persona Con Mfa Pendiente", "rol": "ADM-TI"}],
            "criticos": [], "temporales": [], "revocados": [], "log": [],
            "riesgo": [], "max_riesgo": 1, "stats": {},
        }
        with patch("inventario.management.commands.enviar_resumen_alertas.inicio_rbac",
                   return_value=rbac_simulado), \
             patch("inventario.management.commands.enviar_resumen_alertas.resumen_rbac",
                   return_value={"pendientes_total": 2}):
            call_command("enviar_resumen_alertas")
        correo = mail.outbox[0]
        self.assertIn("Persona De Prueba", correo.body)
        self.assertIn("Persona Con Mfa Pendiente", correo.body)
        self.assertIn("Persona De Prueba", correo.alternatives[0][0])
        self.assertIn("2 pendiente", correo.subject)  # 1 vencimiento + 1 alerta MFA

    def test_solo_si_hay_criticas_no_envia_cuando_todo_esta_bien(self):
        from unittest.mock import patch

        from django.core import mail
        from django.core.management import call_command
        from .models import Activo
        self._limpiar_config_correo()
        Activo.objects.all().delete()  # sin activos, sin alertas posibles
        with patch("inventario.management.commands.enviar_resumen_alertas.inicio_rbac",
                   return_value=None):
            call_command("enviar_resumen_alertas", "--solo-si-hay-criticas")
        self.assertEqual(len(mail.outbox), 0)

    def test_destinatarios_por_linea_de_comandos_tiene_prioridad(self):
        from unittest.mock import patch

        from django.core import mail
        from django.core.management import call_command
        self._limpiar_config_correo()
        with patch("inventario.management.commands.enviar_resumen_alertas.inicio_rbac",
                   return_value=None):
            call_command("enviar_resumen_alertas", destinatarios="otro@x.com,mas@x.com")
        self.assertEqual(mail.outbox[0].to, ["otro@x.com", "mas@x.com"])


class IntegridadCadenaTest(TestCase):
    """Bitácora encadenada por hash SHA-256 del Inventario (mismo esquema
    que ya tenía RBAC) — antes, django-simple-history registraba bien
    quién/cuándo/qué cambió, pero nada impedía editar esa bitácora
    directamente en la base de datos sin dejar rastro."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("integridad_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)
        cls.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        cls.administrador = User.objects.create_user("integridad_test_admin", password="x")
        cls.administrador.groups.add(cls.grupo_admin)

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def _payload_infra(self, nombre, **extra):
        body = {"nombre": nombre, "clase": "INFRA", "infraestructura": {}}
        body.update(extra)
        return body

    def _payload_sist(self, nombre, **extra):
        body = {"nombre": nombre, "clase": "SIST", "sistema": {}}
        body.update(extra)
        return body

    def test_crear_activo_agrega_una_fila_a_la_cadena(self):
        from .models import RegistroIntegridad
        r = self.client.post("/api/activos/",
                             self._payload_infra("Activo de prueba integridad"),
                             content_type="application/json")
        self.assertEqual(r.status_code, 201)
        fila = RegistroIntegridad.objects.get(entidad="Activo", accion="ALTA")
        self.assertEqual(fila.responsable, "integridad_test_dinam")
        self.assertIn("Activo de prueba integridad", fila.detalle)

    def test_editar_activo_registra_los_campos_modificados(self):
        from .models import RegistroIntegridad
        creado = self.client.post(
            "/api/activos/", self._payload_infra("Original"),
            content_type="application/json").json()
        self.client.patch(f"/api/activos/{creado['id']}/",
                          {"nombre": "Renombrado"}, content_type="application/json")
        fila = RegistroIntegridad.objects.get(entidad="Activo", accion="MODIFICACION")
        self.assertIn("nombre", fila.detalle)

    def test_eliminar_activo_registra_la_eliminacion(self):
        from .models import RegistroIntegridad
        creado = self.client.post(
            "/api/activos/", self._payload_infra("Para borrar"),
            content_type="application/json").json()
        self.client.force_login(self.administrador)  # DELETE exige Administrador
        r = self.client.delete(f"/api/activos/{creado['id']}/")
        self.assertEqual(r.status_code, 204)
        self.assertTrue(RegistroIntegridad.objects.filter(
            entidad="Activo", accion="ELIMINACION").exists())

    def test_cadena_intacta_tras_varios_cambios(self):
        creado = self.client.post(
            "/api/activos/", self._payload_sist("Activo con historia"),
            content_type="application/json").json()
        self.client.patch(f"/api/activos/{creado['id']}/",
                          {"nombre": "Con historia (v2)"}, content_type="application/json")
        self.client.patch(f"/api/activos/{creado['id']}/",
                          {"nombre": "Con historia (v3)"}, content_type="application/json")
        r = self.client.get("/api/integridad/verificar/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"integra": True, "total_verificado": 3})

    def test_verificar_detecta_una_fila_alterada_por_fuera_de_la_app(self):
        from .models import RegistroIntegridad
        self.client.post("/api/activos/", self._payload_infra("Activo A"),
                         content_type="application/json")
        self.client.post("/api/activos/", self._payload_infra("Activo B"),
                         content_type="application/json")
        primera = RegistroIntegridad.objects.order_by("id").first()
        primera.detalle = "detalle alterado a mano, sin pasar por la app"
        primera.save()

        r = self.client.get("/api/integridad/verificar/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertFalse(data["integra"])
        self.assertEqual(data["registro_alterado"], primera.id)

    def test_cadena_vacia_se_considera_intacta(self):
        r = self.client.get("/api/integridad/verificar/")
        self.assertEqual(r.json(), {"integra": True, "total_verificado": 0})

    def test_lista_respeta_el_limite(self):
        for i in range(5):
            self.client.post("/api/activos/", self._payload_infra(f"Activo {i}"),
                             content_type="application/json")
        r = self.client.get("/api/integridad/?limite=3")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 3)


class ImportarActivosTest(TestCase):
    """Importación masiva de activos desde Excel (análisis + confirmación
    en dos pasos, igual que ya hacía RBAC para importar la matriz por
    CSV) — antes, cargar un lote de equipos nuevos significaba
    registrarlos uno por uno desde el formulario."""

    @classmethod
    def setUpTestData(cls):
        from .models import Datacenter
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("importar_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("importar_test_cons", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)
        cls.dc = Datacenter.objects.create(codigo="DC-TEST", nombre="Sede de prueba",
                                           tipo="PRIN", nivel_tier="T3")

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def _archivo(self, filas):
        """Construye un .xlsx en memoria con la plantilla real más las
        filas indicadas — filas pueden ser listas o dicts indexados por COLUMNAS."""
        import io

        from .importar_activos import COLUMNAS, generar_plantilla
        wb = generar_plantilla()
        ws = wb.active
        ws.delete_rows(2, 1)  # quitar la fila de ejemplo
        for f in filas:
            if isinstance(f, dict):
                ws.append([f.get(c, "") for c in COLUMNAS])
            else:
                ws.append(f)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = "lote.xlsx"
        return buf

    def test_plantilla_descargable_es_un_xlsx_valido(self):
        r = self.client.get("/api/activos/importar/plantilla.xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheet", r["Content-Type"])

    def test_analizar_detecta_filas_validas_e_invalidas(self):
        archivo = self._archivo([
            ["", "Activo válido", "INFRA", "INT", "BAJO", 1, 1, 1, "ACT", "PROD",
             "DC-TEST", "", "", "", "No", "", ""],
            ["", "Clase inválida", "NOEXISTE", "", "", "", "", "", "ACT", "PROD",
             "", "", "", "", "No", "", ""],
        ])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["listas"], 1)
        self.assertEqual(data["con_error"], 1)

    def test_analizar_ignora_filas_en_blanco(self):
        archivo = self._archivo([
            ["", "Único activo", "INFRA", "", "", "", "", "", "ACT", "PROD",
             "", "", "", "", "No", "", ""],
            ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        self.assertEqual(r.json()["total"], 1)

    def test_analizar_resuelve_datacenter_por_codigo(self):
        archivo = self._archivo([
            ["", "Con datacenter", "INFRA", "", "", "", "", "", "ACT", "PROD",
             "DC-TEST", "", "", "", "No", "", ""],
        ])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        fila = r.json()["filas"][0]
        self.assertEqual(fila["estado"], "ok")
        self.assertEqual(fila["datos"]["datacenter"], self.dc.id)

    def test_analizar_rechaza_datacenter_inexistente(self):
        archivo = self._archivo([
            ["", "Con datacenter falso", "INFRA", "", "", "", "", "", "ACT", "PROD",
             "DC-NO-EXISTE", "", "", "", "No", "", ""],
        ])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        fila = r.json()["filas"][0]
        self.assertEqual(fila["estado"], "error")
        self.assertIn("DC-NO-EXISTE", fila["mensaje"])

    def test_analizar_detecta_id_activo_repetido_en_el_mismo_archivo(self):
        archivo = self._archivo([
            ["RED-099", "Primero", "INFRA", "", "", "", "", "", "ACT", "PROD",
             "", "", "", "", "No", "", ""],
            ["RED-099", "Segundo con el mismo ID", "INFRA", "", "", "", "", "", "ACT", "PROD",
             "", "", "", "", "No", "", ""],
        ])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        data = r.json()
        self.assertEqual(data["filas"][0]["estado"], "ok")
        self.assertEqual(data["filas"][1]["estado"], "error")

    def test_confirmar_crea_solo_las_filas_marcadas(self):
        from .models import Activo
        filas = [
            {"fila": 2, "datos": {"nombre": "A crear", "clase": "INFRA"}},
        ]
        r = self.client.post("/api/activos/importar/confirmar/",
                             data=json.dumps({"filas": filas}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total_creados"], 1)
        self.assertEqual(Activo.objects.filter(nombre="A crear").count(), 1)

    def test_confirmar_reporta_fallidos_sin_bloquear_los_validos(self):
        filas = [
            {"fila": 2, "datos": {"nombre": "Válido", "clase": "INFRA"}},
            {"fila": 3, "datos": {"nombre": "Inválido", "clase": "NOEXISTE"}},
        ]
        r = self.client.post("/api/activos/importar/confirmar/",
                             data=json.dumps({"filas": filas}), content_type="application/json")
        data = r.json()
        self.assertEqual(data["total_creados"], 1)
        self.assertEqual(data["total_fallidos"], 1)

    def test_confirmar_las_filas_creadas_quedan_en_la_cadena_de_integridad(self):
        from .models import RegistroIntegridad
        filas = [{"fila": 2, "datos": {"nombre": "Trazado", "clase": "INFRA"}}]
        self.client.post("/api/activos/importar/confirmar/",
                         data=json.dumps({"filas": filas}), content_type="application/json")
        self.assertTrue(RegistroIntegridad.objects.filter(
            entidad="Activo", accion="ALTA", detalle__contains="Trazado").exists())

    def test_consultor_no_puede_analizar_ni_confirmar(self):
        self.client.force_login(self.consultor)
        archivo = self._archivo([["", "x", "INFRA", "", "", "", "", "", "ACT", "PROD",
                                  "", "", "", "", "No", "", ""]])
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": archivo})
        self.assertEqual(r.status_code, 403)
        r = self.client.post("/api/activos/importar/confirmar/",
                             data=json.dumps({"filas": []}), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_analizar_sin_archivo_da_400(self):
        r = self.client.post("/api/activos/importar/analizar/", {})
        self.assertEqual(r.status_code, 400)

    def test_analizar_infra_con_rack_por_codigo(self):
        from .models import Rack
        from .importar_activos import COLUMNAS

        Rack.objects.create(datacenter=self.dc, codigo="A01", capacidad_u=42)
        fila = {c: "" for c in COLUMNAS}
        fila.update({
            "nombre": "Switch rack A01", "clase": "INFRA", "estado": "ACT",
            "ciclo_vida": "PROD", "datacenter": "DC-TEST", "procesa_datos_personales": "No",
            "infra_tipo": "Switch", "infra_rack": "A01", "infra_u_inicio": 10, "infra_u_fin": 11,
        })
        r = self.client.post("/api/activos/importar/analizar/", {"archivo": self._archivo([fila])})
        self.assertEqual(r.status_code, 200)
        item = r.json()["filas"][0]
        self.assertEqual(item["estado"], "ok")
        self.assertEqual(item["datos"]["infraestructura"]["rack_fk"], Rack.objects.get(codigo="A01").id)

    def test_exportar_inventario_comparte_esquema_con_plantilla(self):
        from openpyxl import load_workbook
        import io

        from .importar_activos import COLUMNAS, generar_plantilla
        plantilla = generar_plantilla()
        r = self.client.get("/api/exportar/inventario.xlsx")
        self.assertEqual(r.status_code, 200)
        exp = load_workbook(io.BytesIO(r.content), read_only=True)
        self.assertEqual(
            [c.value for c in exp.active[1]],
            [c.value for c in plantilla.active[1]],
        )
        self.assertEqual(len([c.value for c in exp.active[1]]), len(COLUMNAS))


class ReporteConsolidadoTest(TestCase):
    """PDF único con SoA, riesgos, alertas y cumplimiento RBAC — antes,
    preparar evidencia de auditoría significaba combinar a mano varias
    exportaciones parciales."""

    @classmethod
    def setUpTestData(cls):
        from datetime import date, timedelta

        from .models import Activo, ActivoInfraestructura, ControlISO
        a = Activo.objects.create(
            nombre="Firewall para el reporte", clase="INFRA",
            clasificacion_si="ALTA", nivel_riesgo="CRIT",
            confidencialidad=4, integridad=4, disponibilidad=4,
            propietario="Coordinación TI")
        ActivoInfraestructura.objects.create(
            activo=a, fin_soporte_eol=date.today() - timedelta(days=5))
        ctrl = ControlISO.objects.create(codigo="8.20", descripcion="Redes")
        a.controles.add(ctrl)
        cls.activo = a
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.dinamizador = User.objects.create_user("reporte_test_dinam", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)

    def setUp(self):
        self.client.force_login(self.dinamizador)

    def test_devuelve_un_pdf_valido(self):
        r = self.client.get("/api/reporte-consolidado.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_el_pdf_incluye_datos_reales_del_activo_critico(self):
        from unittest.mock import patch
        with patch("inventario.reporte_consolidado.inicio_rbac", return_value=None):
            r = self.client.get("/api/reporte-consolidado.pdf")
        # el codigo del activo de prueba debe aparecer en el PDF (en texto
        # plano dentro del stream, no comprimido, dado el reportlab por defecto)
        self.assertIn(self.activo.id_activo.encode(), r.content)

    def test_funciona_aunque_rbac_no_responda(self):
        from unittest.mock import patch
        with patch("inventario.reporte_consolidado.inicio_rbac", return_value=None):
            r = self.client.get("/api/reporte-consolidado.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_incluye_seccion_rbac_cuando_si_responde(self):
        from unittest.mock import patch
        rbac_simulado = {
            "stats": {"roles": 5, "sistemas": 8, "usuarios": 10, "accesos": 40},
            "mfa_pct": 90, "mfa_ok": 9, "mfa_total": 10, "dias_alerta": 7,
            "criticos": [{"abreviatura": "ADM-REPORTE-TEST", "denominacion": "Rol de prueba", "n_admin": 3}],
            "alertas_mfa": [], "proximos_vencimientos": [],
            "temporales": [], "revocados": [], "log": [], "riesgo": [], "max_riesgo": 1,
        }
        with patch("inventario.reporte_consolidado.inicio_rbac", return_value=rbac_simulado):
            r = self.client.get("/api/reporte-consolidado.pdf")
        self.assertIn(b"ADM-REPORTE-TEST", r.content)

    def test_nombre_de_archivo_incluye_la_fecha(self):
        r = self.client.get("/api/reporte-consolidado.pdf")
        self.assertIn("reporte_consolidado_suiin_", r["Content-Disposition"])


class TokenJWTTest(TestCase):
    """
    Cubre la emisión del JWT de plataforma (`/api/token-jwt/`), que permite
    sesión única con SUIIN-SGSI-RIESGOS sin que ese módulo tenga su propio
    login — ver inventario/jwt_plataforma.py y README-DESPLIEGUE.md sección 11.
    Si esta prueba se rompe, ese módulo deja de poder autenticar usuarios de
    la plataforma (aunque su login propio por token seguiría funcionando).
    """
    URL = "/api/token-jwt/"

    @classmethod
    def setUpTestData(cls):
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.usuario = User.objects.create_user(
            "con_sesion_test", password="clave-de-prueba-123")
        cls.usuario.groups.add(cls.grupo_dinamizador)

    def _decodificar(self, token, secreto="secreto-de-prueba-jwt"):
        import jwt
        return jwt.decode(token, secreto, algorithms=["HS256"], issuer="suiin-inventario")

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_sin_sesion_ni_credenciales_devuelve_401(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 401)

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_get_con_sesion_activa_emite_token(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        payload = self._decodificar(r.json()["token"])
        self.assertEqual(payload["username"], "con_sesion_test")
        self.assertEqual(payload["roles"], ["Dinamizador"])

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_post_con_credenciales_validas_emite_token_sin_sesion_previa(self):
        r = self.client.post(
            self.URL, {"username": "con_sesion_test", "password": "clave-de-prueba-123"},
            content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.json())

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_post_con_credenciales_invalidas_devuelve_401(self):
        r = self.client.post(
            self.URL, {"username": "con_sesion_test", "password": "incorrecta"},
            content_type="application/json")
        self.assertEqual(r.status_code, 401)

    @override_settings(JWT_SHARED_SECRET="")
    def test_sin_jwt_shared_secret_configurado_devuelve_503(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 503)

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt", JWT_EXPIRACION_MINUTOS=30)
    def test_token_incluye_version_y_roles(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.URL)
        payload = self._decodificar(r.json()["token"])
        self.assertIn("ver", payload)
        self.assertGreaterEqual(payload["ver"], 1)
        self.assertEqual(payload["roles"], ["Dinamizador"])

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt", JWT_EXPIRACION_MINUTOS=30)
    def test_token_incluye_expiracion_coherente_con_la_configuracion(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.URL)
        payload = self._decodificar(r.json()["token"])
        vigencia_segundos = payload["exp"] - payload["iat"]
        self.assertEqual(vigencia_segundos, 30 * 60)

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_token_no_es_valido_con_otro_secreto(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.URL)
        with self.assertRaises(Exception):
            self._decodificar(r.json()["token"], secreto="otro-secreto-distinto")

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_bloqueo_por_fuerza_bruta_es_por_usuario_no_por_ip_completa(self):
        """Reproduce, contra /api/token-jwt/ (POST con usuario/clave), el mismo
        hallazgo que llevó a corregir AXES_LOCKOUT_PARAMETERS: con la forma
        plana (sin anidar), un segundo usuario válido desde la misma IP
        también quedaba bloqueado. Con la forma anidada, no debe pasar."""
        otro = User.objects.create_user("otro_para_jwt_test", password="clave-de-otro-456")
        for _ in range(5):
            self.client.post(self.URL, {"username": "con_sesion_test", "password": "incorrecta"},
                              content_type="application/json")
        r = self.client.post(self.URL, {"username": "otro_para_jwt_test", "password": "clave-de-otro-456"},
                              content_type="application/json")
        self.assertEqual(r.status_code, 200)
        otro.delete()

    @override_settings(JWT_SHARED_SECRET="secreto-de-prueba-jwt")
    def test_login_exitoso_resetea_el_contador_de_fallos(self):
        """token_jwt no llama a django.contrib.auth.login() (entrega un JWT,
        no abre sesión) — sin el reset explícito agregado a la vista, tres
        fallos seguidos de un acierto no reiniciaban el contador."""
        for _ in range(3):
            self.client.post(self.URL, {"username": "con_sesion_test", "password": "incorrecta"},
                              content_type="application/json")
        r_ok = self.client.post(self.URL, {"username": "con_sesion_test", "password": "clave-de-prueba-123"},
                                 content_type="application/json")
        self.assertEqual(r_ok.status_code, 200)

        for _ in range(4):
            r = self.client.post(self.URL, {"username": "con_sesion_test", "password": "incorrecta"},
                                  content_type="application/json")
            self.assertEqual(r.status_code, 401)
        r_final = self.client.post(self.URL, {"username": "con_sesion_test", "password": "clave-de-prueba-123"},
                                    content_type="application/json")
        self.assertEqual(r_final.status_code, 200)


class ServicioInternoCatalogoTest(TestCase):
    """Sync Riesgos/RBAC usa X-Plataforma-Secret (= JWT_SHARED_SECRET)."""

    @override_settings(JWT_SHARED_SECRET="secreto-sync-interno-test")
    def test_amenazas_accesible_con_secreto_sin_sesion(self):
        r = self.client.get(
            "/api/amenazas/?page_size=5",
            HTTP_X_PLATAFORMA_SECRET="secreto-sync-interno-test",
        )
        self.assertEqual(r.status_code, 200, r.content)

    @override_settings(JWT_SHARED_SECRET="secreto-sync-interno-test")
    def test_amenazas_anonimo_sigue_prohibido(self):
        r = self.client.get("/api/amenazas/?page_size=5")
        self.assertEqual(r.status_code, 403)

    @override_settings(JWT_SHARED_SECRET="secreto-sync-interno-test")
    def test_catalogo_mitre_interno_con_secreto(self):
        r = self.client.get(
            "/api/interno/catalogo-mitre/?page_size=5",
            HTTP_X_PLATAFORMA_SECRET="secreto-sync-interno-test",
        )
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertIn("results", data)
        self.assertIn("count", data)

    @override_settings(JWT_SHARED_SECRET="secreto-sync-interno-test")
    def test_catalogo_mitre_interno_sin_secreto_403(self):
        r = self.client.get("/api/interno/catalogo-mitre/?page_size=5")
        self.assertEqual(r.status_code, 403)


class AllowedHostsInternoTest(TestCase):
    """
    Cubre el hallazgo real de un despliegue: sincronizar_activos_inventario
    (en riesgos) llama a http://inventario:8000/... directo, contenedor a
    contenedor, sin pasar por nginx — con Host: inventario, Django lo
    rechazaba con 400 ("Invalid HTTP_HOST header") porque 'inventario' (el
    nombre del servicio en docker-compose.yml) no estaba en
    DJANGO_ALLOWED_HOSTS. Ver README-DESPLIEGUE.md.
    """

    def test_inventario_esta_en_allowed_hosts_sin_importar_el_env(self):
        # settings.py lo agrega incondicionalmente — no depende de que alguien
        # lo haya puesto a mano en DJANGO_ALLOWED_HOSTS.
        self.assertIn("inventario", settings.ALLOWED_HOSTS)

    def test_una_peticion_con_host_inventario_no_se_rechaza(self):
        r = self.client.get("/api/sesion/", HTTP_HOST="inventario")
        self.assertNotEqual(r.status_code, 400)
        self.assertEqual(r.status_code, 200)

    def test_una_peticion_con_host_inventario_y_puerto_tampoco_se_rechaza(self):
        """Así es exactamente como llega — http://inventario:8000/... — con
        el puerto incluido en el header Host."""
        r = self.client.get("/api/sesion/", HTTP_HOST="inventario:8000")
        self.assertNotEqual(r.status_code, 400)
        self.assertEqual(r.status_code, 200)

    def test_un_host_no_autorizado_de_verdad_si_se_sigue_rechazando(self):
        """Control: confirma que el fix no abrió la puerta a cualquier Host —
        solo agregó el nombre interno específico que hacía falta."""
        r = self.client.get("/api/sesion/", HTTP_HOST="dominio-cualquiera-no-autorizado.com")
        self.assertEqual(r.status_code, 400)


class XFrameOptionsTest(TestCase):
    """
    Hallazgo real, reportado con captura y confirmado con el error exacto de
    la consola del navegador ("Refused to display '.../' in a frame because
    it set 'X-Frame-Options' to 'deny'"): el Inventario incrusta RBAC y
    Riesgos en <iframe> propios, y ambos módulos redirigen de vuelta acá
    (/login/) como respaldo cuando su sesión no está sincronizada. Con DENY,
    esa página de respaldo tampoco se podía mostrar dentro de ESE iframe, y
    el navegador la bloqueaba por completo — se veía como un ícono de
    archivo roto, sin ningún mensaje. RBAC ya tenía este mismo ajuste hecho
    correctamente (ver rbac/auth.py); acá se había quedado en DENY.

    El ajuste real (settings.py) vive dentro de "if not DEBUG:" (bloque de
    endurecimiento de producción), que se evalúa una sola vez al cargar el
    módulo — override_settings(DEBUG=False) NO lo vuelve a ejecutar, solo
    cambia el valor de settings.DEBUG en el proceso de pruebas ya cargado
    (se intentó así primero; la prueba seguía dando DENY, aunque el fix ya
    estaba aplicado — confirmando que ese enfoque no prueba nada real). La
    única forma correcta es levantar un proceso Django nuevo con
    DJANGO_DEBUG=False de verdad, para que settings.py se cargue desde cero
    con ese valor — subprocess, no el cliente de pruebas de Django.
    """

    def _x_frame_options_con_debug_false(self, ruta):
        import subprocess
        codigo = (
            "import django, os; "
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); "
            "django.setup(); "
            "from django.test import Client; "
            f"r = Client().get('{ruta}'); "
            "print(r.headers.get('X-Frame-Options'))"
        )
        env = os.environ.copy()
        env.update({
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": "clave-de-prueba-no-placeholder-suficientemente-larga-1234567890",
            "JWT_SHARED_SECRET": "jwt-clave-de-prueba-no-placeholder-suficientemente-larga-1234567890",
            "DJANGO_ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
            "DJANGO_SSL_REDIRECT": "False",  # como en producción real (.env.example) — sin esto,
                                              # SECURE_SSL_REDIRECT devuelve 301 antes de llegar a la vista
        })
        resultado = subprocess.run(
            ["python3", "manage.py", "shell", "-c", codigo],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, timeout=30,
        )
        return resultado.stdout.strip().splitlines()[-1] if resultado.stdout.strip() else None

    def test_x_frame_options_es_sameorigin_no_deny(self):
        self.assertEqual(self._x_frame_options_con_debug_false("/login/"), "SAMEORIGIN")

    def test_la_raiz_redirige_a_la_spa(self):
        """Tras el corte final, Django ya no sirve dashboard.html en /."""
        self.assertEqual(self._x_frame_options_con_debug_false("/"), "SAMEORIGIN")


class PoliticaSeguridadAPITest(TestCase):
    """Ola 1 — opción C: KPIs agregados públicos; detalle y exportaciones con sesión."""

    URL_KPI = "/api/dashboard-ejecutivo/"

    @classmethod
    def setUpTestData(cls):
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        cls.consultor = User.objects.create_user("politica_cons", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)
        cls.admin = User.objects.create_user("politica_admin", password="x")
        cls.admin.groups.add(cls.grupo_admin)

    def test_kpi_ejecutivo_sigue_publico(self):
        r = self.client.get(self.URL_KPI)
        self.assertEqual(r.status_code, 200)
        self.assertIn("total_activos", r.json())
        self.assertIn("riesgos", r.json())

    def test_panel_incluye_riesgos_cuando_responde(self):
        from unittest.mock import patch

        riesgos_falso = {
            "disponible": True,
            "pendientes_total": 6,
            "total_vencidas": 1,
            "total_por_vencer": 2,
            "activos_sin_cobertura": 1,
            "vulnerabilidades_criticas": 1,
            "activos_comprometidos": 1,
        }
        with patch("inventario.views._resumen_riesgos", return_value=riesgos_falso):
            r = self.client.get(self.URL_KPI)
        self.assertEqual(r.json()["riesgos"]["pendientes_total"], 6)

    def test_anonimo_no_accede_a_detalle_de_activos(self):
        from .models import Activo
        a = Activo.objects.create(nombre="Privado", clase="INFRA")
        r = self.client.get(f"/api/activos/{a.pk}/")
        self.assertIn(r.status_code, (401, 403))

    def test_anonimo_no_descarga_exportaciones(self):
        for url in (
            "/api/exportar/inventario.xlsx",
            "/api/reporte-consolidado.pdf",
            "/api/activos/importar/plantilla.xlsx",
        ):
            r = self.client.get(url)
            self.assertIn(r.status_code, (401, 403), url)

    def test_consultor_si_accede_a_detalle(self):
        from .models import Activo
        a = Activo.objects.create(nombre="Visible autenticado", clase="INFRA")
        self.client.force_login(self.consultor)
        r = self.client.get(f"/api/activos/{a.pk}/")
        self.assertEqual(r.status_code, 200)

    def test_accesos_unificado_solo_administrador(self):
        self.client.force_login(self.consultor)
        r = self.client.get("/api/accesos/unificado/")
        self.assertEqual(r.status_code, 403)
        self.client.force_login(self.admin)
        r = self.client.get("/api/accesos/unificado/")
        self.assertEqual(r.status_code, 200)


class JWTRevocacionTest(TestCase):
    """Ola 1 — jwt_version invalida tokens emitidos antes de un cambio de rol."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.usuario = User.objects.create_user("jwt_revoc_test", password="x")
        cls.usuario.groups.add(cls.grupo_dinamizador)

    @override_settings(JWT_SHARED_SECRET="secreto-jwt-revocacion-test")
    def test_cambio_de_rol_incrementa_version_y_token_antiguo_queda_obsoleto(self):
        from .signals import jwt_version_de
        self.client.force_login(self.usuario)
        r1 = self.client.get("/api/token-jwt/")
        self.assertEqual(r1.status_code, 200)
        token_viejo = r1.json()["token"]
        ver_inicial = jwt_version_de(self.usuario)

        self.usuario.groups.remove(self.grupo_dinamizador)
        self.usuario.groups.add(self.grupo_consultor)
        ver_nueva = jwt_version_de(self.usuario)
        self.assertGreater(ver_nueva, ver_inicial)

        r2 = self.client.get(
            f"/api/auth/jwt-version/{self.usuario.username}/",
            HTTP_X_PLATAFORMA_SECRET="secreto-jwt-revocacion-test",
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["ver"], ver_nueva)

        import jwt
        payload = jwt.decode(token_viejo, "secreto-jwt-revocacion-test",
                             algorithms=["HS256"], issuer="suiin-inventario")
        self.assertLess(payload["ver"], ver_nueva)


class IntegracionRiesgosOla5Test(TestCase):
    """Ola 5 — flujo unificado Inventario ↔ Riesgos (integracion_riesgos.py)."""

    URL_ALERTAS = "/api/alertas/unificadas/"

    @classmethod
    def setUpTestData(cls):
        from .models import Activo
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("integracion_riesgos_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)
        cls.activo = Activo.objects.create(
            nombre="Servidor sync", clase="INFRA", clasificacion_si="CONF",
            estado="ACT", nivel_riesgo="MED",
        )

    def setUp(self):
        self.client.force_login(self.consultor)

    def test_alertas_unificadas_incluye_tres_modulos(self):
        from unittest.mock import patch

        rbac_falso = {
            "pendientes_total": 5,
            "desglose_pendientes": {
                "proximos_vencimientos": 1,
                "alertas_mfa": 2,
                "roles_certificacion_vencida": 1,
                "excepciones_vencidas": 1,
            },
        }
        ries_alertas = {"total_vencidas": 2, "total_por_vencer": 3, "disponible": True}
        ries_kpis = {
            "disponible": True,
            "activos_sin_cobertura": 4,
            "vulnerabilidades_criticas": 1,
            "activos_comprometidos": 0,
        }

        with patch("inventario.views.catalogo_sistemas_rbac", return_value=[]), \
             patch("inventario.integracion_rbac.resumen_rbac", return_value=rbac_falso), \
             patch("inventario.integracion_riesgos.alertas_riesgos_resumen", return_value=ries_alertas), \
             patch("inventario.integracion_riesgos.kpis_riesgos_dashboard", return_value=ries_kpis), \
             patch("inventario.integracion_riesgos.resumen_vinculacion", return_value={
                 "disponible": True, "total_inventario": 5, "vinculados": 4,
                 "sin_espejo_riesgos": 1, "huerfanos_riesgos": 0,
             }):
            r = self.client.get(self.URL_ALERTAS)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("inventario", data)
        self.assertIn("rbac", data)
        self.assertIn("riesgos", data)
        self.assertIn("resumen", data)
        self.assertIn("vinculacion", data)
        self.assertTrue(data["rbac"]["disponible"])
        self.assertTrue(data["riesgos"]["disponible"])
        self.assertEqual(data["riesgos"]["total_vencidas"], 2)
        self.assertEqual(data["riesgos"]["activos_sin_cobertura"], 4)
        self.assertEqual(data["resumen"]["inventario"], data["inventario"]["total_alertas"])
        self.assertEqual(data["resumen"]["riesgos"], 10)  # 2+3+4+1+0
        self.assertEqual(data["resumen"]["sync"], 1)
        self.assertEqual(data["resumen"]["sin_espejo_riesgos"], 1)
        inv_total = data["inventario"]["total_alertas"]
        self.assertEqual(
            data["total_consolidado"],
            inv_total + 5 + 10 + 1,
        )

    def test_alertas_unificadas_degrada_si_riesgos_no_responde(self):
        import requests
        from unittest.mock import patch

        with patch("inventario.integracion_riesgos.requests.get",
                   side_effect=requests.RequestException("caído")):
            r = self.client.get(self.URL_ALERTAS)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["riesgos"]["disponible"])

    def test_resumen_riesgos_sin_vinculo(self):
        r = self.client.get(f"/api/activos/{self.activo.pk}/resumen-riesgos/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["vinculado"])

    def test_resumen_riesgos_con_activo_espejo(self):
        from unittest.mock import patch, MagicMock

        resp = MagicMock()
        resp.json.return_value = {
            "results": [{
                "id": 99,
                "id_activo": "INFRA-001",
                "riesgo_matriz": "ALTO",
                "total_vulnerabilidades": 7,
                "vulnerabilidades_criticas": 2,
                "cobertura": "PARCIAL",
                "afectado_red_team": False,
            }],
        }
        resp.raise_for_status = MagicMock()

        with patch("inventario.integracion_riesgos.requests.get", return_value=resp):
            r = self.client.get(f"/api/activos/{self.activo.pk}/resumen-riesgos/")
        data = r.json()
        self.assertTrue(data["vinculado"])
        self.assertEqual(data["total_vulnerabilidades"], 7)
        self.assertEqual(data["inventario_id"], self.activo.pk)
        self.assertEqual(data["url_gestion"], "/gestion-riesgos/activos/99")
        self.assertEqual(data["url_inventario"], f"/inventario/activos/{self.activo.pk}")

    def test_calcular_riesgos_incluye_vinculacion_y_mapa(self):
        from unittest.mock import patch

        mapa_falso = {
            self.activo.pk: {
                "id": 99,
                "id_activo": "INFRA-001",
                "total_vulnerabilidades": 2,
                "vulnerabilidades_criticas": 1,
                "riesgo_matriz": "ALTO",
            },
        }
        vinc_falsa = {
            "disponible": True,
            "total_inventario": 1,
            "vinculados": 1,
            "sin_espejo_riesgos": 0,
            "huerfanos_riesgos": 0,
        }
        with patch("inventario.integracion_riesgos.mapa_activos_por_inventario", return_value=mapa_falso), \
             patch("inventario.integracion_riesgos.resumen_vinculacion", return_value=vinc_falsa):
            from inventario.views import calcular_riesgos
            data = calcular_riesgos()
        fila = next(f for f in data["activos"] if f["id"] == self.activo.pk)
        self.assertTrue(fila["vinculado_riesgos"])
        self.assertEqual(fila["riesgos_id"], 99)
        self.assertEqual(data["vinculacion"]["vinculados"], 1)


class IntegracionRiesgosOla6Test(TestCase):
    """Ola 6 — panel de sincronización, detalle y export CSV."""

    @classmethod
    def setUpTestData(cls):
        from .models import Activo
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("ola6_vinc_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)
        cls.vinculado = Activo.objects.create(
            nombre="Con espejo", clase="INFRA", clasificacion_si="CONF",
            estado="ACT", nivel_riesgo="MED",
        )
        cls.sin_espejo = Activo.objects.create(
            nombre="Sin espejo", clase="SIST", clasificacion_si="INT",
            estado="ACT", nivel_riesgo="BAJO",
        )

    def setUp(self):
        self.client.force_login(self.consultor)

    def test_integracion_vinculacion_detalle(self):
        from unittest.mock import patch

        mapa = {
            self.vinculado.pk: {
                "id": 10,
                "id_activo": "INFRA-001",
                "total_vulnerabilidades": 0,
                "vulnerabilidades_criticas": 0,
                "riesgo_matriz": "MED",
            },
        }
        huerfanos = [{
            "riesgos_id": 99,
            "id_activo": "HUER-01",
            "nombre": "Huérfano",
            "ip_principal": "10.0.0.1",
            "riesgo_matriz": "ALTO",
        }]
        with patch("inventario.integracion_riesgos.mapa_activos_por_inventario", return_value=mapa), \
             patch("inventario.integracion_riesgos._contar_huerfanos_riesgos", return_value=1), \
             patch("inventario.integracion_riesgos.listar_huerfanos_riesgos", return_value=huerfanos):
            r = self.client.get("/api/integracion/vinculacion/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["disponible"])
        self.assertFalse(data["sincronizacion_ok"])
        self.assertEqual(data["resumen"]["vinculados"], 1)
        self.assertEqual(data["resumen"]["sin_espejo_riesgos"], 1)
        self.assertEqual(len(data["sin_espejo"]), 1)
        self.assertEqual(data["sin_espejo"][0]["inventario_id"], self.sin_espejo.pk)
        self.assertEqual(len(data["huerfanos_riesgos"]), 1)

    def test_export_csv_vinculacion(self):
        from unittest.mock import patch

        detalle_falso = {
            "disponible": True,
            "sin_espejo": [{
                "inventario_id": self.sin_espejo.pk,
                "id_activo": self.sin_espejo.id_activo,
                "nombre": self.sin_espejo.nombre,
                "clase": "SIST",
                "nivel_riesgo": "BAJO",
            }],
            "huerfanos_riesgos": [],
        }
        with patch("inventario.integracion_riesgos.detalle_vinculacion", return_value=detalle_falso):
            r = self.client.get("/api/integracion/vinculacion.csv?tipo=sin_espejo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        cuerpo = r.content.decode("utf-8")
        self.assertIn("sin_espejo", cuerpo)
        self.assertIn(self.sin_espejo.id_activo, cuerpo)

    def test_export_csv_tipo_invalido(self):
        r = self.client.get("/api/integracion/vinculacion.csv?tipo=invalido")
        self.assertEqual(r.status_code, 400)

    def test_generar_csv_vinculacion_huerfanos(self):
        from inventario.integracion_riesgos import generar_csv_vinculacion

        csv_text = generar_csv_vinculacion({
            "sin_espejo": [],
            "huerfanos_riesgos": [{
                "riesgos_id": 5,
                "id_activo": "X-01",
                "nombre": "Test",
                "ip_principal": "1.2.3.4",
                "riesgo_matriz": "CRIT",
            }],
        }, tipo="huerfanos")
        self.assertIn("huerfano_riesgos", csv_text)
        self.assertIn("X-01", csv_text)


class IntegracionRiesgosOla8Test(TestCase):
    """Ola 8 — vinculación en listado de activos y filtro operativo."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.consultor = User.objects.create_user("ola8_list_test", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)
        from .models import Activo
        cls.vinculado = Activo.objects.create(
            nombre="Con espejo", clase="INFRA", clasificacion_si="CONF",
            estado="ACT", nivel_riesgo="MED",
        )
        cls.sin_espejo = Activo.objects.create(
            nombre="Sin espejo", clase="SIST", clasificacion_si="INT",
            estado="ACT", nivel_riesgo="BAJO",
        )

    def setUp(self):
        self.client.force_login(self.consultor)

    def test_listado_incluye_vinculado_riesgos(self):
        from unittest.mock import patch

        mapa = {
            self.vinculado.pk: {
                "id": 42,
                "id_activo": "INFRA-001",
                "total_vulnerabilidades": 0,
                "vulnerabilidades_criticas": 0,
                "riesgo_matriz": "MED",
            },
        }
        with patch("inventario.integracion_riesgos.mapa_activos_por_inventario", return_value=mapa):
            r = self.client.get("/api/activos/")
        self.assertEqual(r.status_code, 200)
        filas = {a["id"]: a for a in r.json()["results"]}
        self.assertTrue(filas[self.vinculado.pk]["vinculado_riesgos"])
        self.assertEqual(filas[self.vinculado.pk]["riesgos_id"], 42)
        self.assertFalse(filas[self.sin_espejo.pk]["vinculado_riesgos"])
        self.assertIsNone(filas[self.sin_espejo.pk]["riesgos_id"])

    def test_filtro_sin_espejo_riesgos(self):
        from unittest.mock import patch

        mapa = {self.vinculado.pk: {"id": 42, "id_activo": "X", "vulnerabilidades_criticas": 0}}
        with patch("inventario.integracion_riesgos.mapa_activos_por_inventario", return_value=mapa):
            r = self.client.get("/api/activos/", {"sin_espejo_riesgos": "true"})
        ids = [a["id"] for a in r.json()["results"]]
        self.assertIn(self.sin_espejo.pk, ids)
        self.assertNotIn(self.vinculado.pk, ids)

    def test_listado_vinculado_null_si_riesgos_caido(self):
        from unittest.mock import patch

        with patch("inventario.integracion_riesgos.mapa_activos_por_inventario", return_value=None):
            r = self.client.get("/api/activos/")
        fila = r.json()["results"][0]
        self.assertIsNone(fila["vinculado_riesgos"])


class UsuariosPlataformaAPITest(TestCase):
    """CRUD de cuentas de login — solo Administrador."""

    BASE = "/api/usuarios-plataforma/"

    @classmethod
    def setUpTestData(cls):
        cls.grupo_consultor, _ = Group.objects.get_or_create(name="Consultor")
        cls.grupo_dinamizador, _ = Group.objects.get_or_create(name="Dinamizador")
        cls.grupo_admin, _ = Group.objects.get_or_create(name="Administrador")

        cls.consultor = User.objects.create_user("up_consultor", password="x")
        cls.consultor.groups.add(cls.grupo_consultor)

        cls.dinamizador = User.objects.create_user("up_dinamizador", password="x")
        cls.dinamizador.groups.add(cls.grupo_dinamizador)

        cls.administrador = User.objects.create_user("up_admin", password="x")
        cls.administrador.groups.add(cls.grupo_admin)

    def test_dinamizador_no_puede_listar(self):
        self.client.force_login(self.dinamizador)
        r = self.client.get(self.BASE)
        self.assertEqual(r.status_code, 403)

    def test_admin_crea_usuario_con_area(self):
        self.client.force_login(self.administrador)
        r = self.client.post(
            self.BASE,
            {
                "username": "usuario_uaiin",
                "password": "ClaveSegura1",
                "first_name": "Ana",
                "last_name": "Mesa",
                "email": "ana@cric.org.co",
                "rol": "Consultor",
                "area": "UAIIN",
                "modulos_acceso": ["inventario"],
            },
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["username"], "usuario_uaiin")
        self.assertEqual(data["rol"], "Consultor")
        self.assertEqual(data["area"], "UAIIN")
        self.assertTrue(data["is_active"])

    def test_admin_actualiza_rol_y_contrasena(self):
        self.client.force_login(self.administrador)
        crear = self.client.post(
            self.BASE,
            {
                "username": "temp_user",
                "password": "ClaveSegura1",
                "rol": "Consultor",
                "area": "TIC",
                "modulos_acceso": ["inventario", "rbac"],
            },
            content_type="application/json",
        )
        uid = crear.json()["id"]
        r = self.client.patch(
            f"{self.BASE}{uid}/",
            {"rol": "Dinamizador", "password": "OtraClave9"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rol"], "Dinamizador")

    def test_meta_devuelve_roles(self):
        self.client.force_login(self.administrador)
        r = self.client.get(f"{self.BASE}meta/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Consultor", r.json()["roles"])

    def test_admin_crea_usuario_solo_rbac(self):
        self.client.force_login(self.administrador)
        r = self.client.post(
            self.BASE,
            {
                "username": "solo_rbac",
                "password": "ClaveSegura1",
                "rol": "Consultor",
                "area": "TIC",
                "modulos_acceso": ["rbac"],
            },
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["modulos_acceso"], ["rbac"])

    def test_usuario_solo_rbac_no_accede_inventario_api(self):
        from django.contrib.auth.models import User
        self.client.force_login(self.administrador)
        self.client.post(
            self.BASE,
            {
                "username": "consultor_rbac",
                "password": "ClaveSegura1",
                "rol": "Consultor",
                "modulos_acceso": ["rbac"],
            },
            content_type="application/json",
        )
        consultor = User.objects.get(username="consultor_rbac")
        self.client.force_login(consultor)
        r = self.client.get("/api/activos/")
        self.assertEqual(r.status_code, 403)
        r_rbac = self.client.get("/api/auth-rbac/")
        self.assertEqual(r_rbac.status_code, 204)

    def test_no_degrada_ultimo_admin(self):
        self.client.force_login(self.administrador)
        r = self.client.patch(
            f"{self.BASE}{self.administrador.pk}/",
            {"rol": "Consultor"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("Administrador", str(r.json()))

    def test_crear_sin_proyectos_rechazado(self):
        self.client.force_login(self.administrador)
        r = self.client.post(
            self.BASE,
            {
                "username": "sin_proyectos",
                "password": "ClaveSegura1",
                "rol": "Consultor",
                "modulos_acceso": [],
            },
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("proyecto", str(r.json()).lower())

    def test_sesion_incluye_modulos(self):
        self.client.force_login(self.administrador)
        r = self.client.get("/api/sesion/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("modulos", r.json())
        self.assertIn("inventario", r.json()["modulos"])


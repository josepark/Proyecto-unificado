# -*- coding: utf-8 -*-
"""Aislamiento por espacio_codigo en el módulo de Riesgos."""
import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from riesgos.models import Activo, ESPACIO_ORGANIZACION


@override_settings(JWT_SHARED_SECRET="test-secret-espacio")
class EspacioRiesgosTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        Activo.objects.create(
            espacio_codigo=ESPACIO_ORGANIZACION,
            id_activo="DEMO-001",
            nombre="Activo demo org",
            valor=5,
        )
        Activo.objects.create(
            espacio_codigo="usuario-pruebas",
            id_activo="PRIV-001",
            nombre="Activo privado",
            valor=3,
        )

    def _token(self, espacio):
        payload = {
            "iss": settings.JWT_ISSUER,
            "username": "pruebas",
            "roles": ["Consultor"],
            "modulos": ["riesgos"],
            "espacio_codigo": espacio,
            "ver": 1,
        }
        token = jwt.encode(payload, settings.JWT_SHARED_SECRET, algorithm=settings.JWT_ALGORITHM)
        return token if isinstance(token, str) else token.decode()

    def test_jwt_filtra_activos_por_espacio(self):
        token = self._token("usuario-pruebas")
        r = self.client.get("/api/activos/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 200)
        ids = [a["id_activo"] for a in r.json()["results"]]
        self.assertEqual(ids, ["PRIV-001"])

    def test_api_interna_filtra_por_header(self):
        r = self.client.get(
            "/api/activos/",
            HTTP_X_PLATAFORMA_SECRET=settings.JWT_SHARED_SECRET,
            HTTP_X_ESPACIO_DATOS="usuario-pruebas",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)

    def test_dashboard_vacio_en_espacio_personal(self):
        r = self.client.get(
            "/api/dashboard/resumen/",
            HTTP_X_PLATAFORMA_SECRET=settings.JWT_SHARED_SECRET,
            HTTP_X_ESPACIO_DATOS="usuario-nuevo",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["kpis"]["total_activos"], 0)

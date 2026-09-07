#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — pruebas de integración (solo API, post-migración React).

La suite HTML legacy (plantillas Jinja2) fue retirada; la cobertura de
negocio detallada vive en test_api_rest.py. Aquí quedan contratos de
integración con el Inventario y salvaguardas transversales.
"""
import os
import sqlite3
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import db as capa_db  # noqa: E402
import seed  # noqa: E402


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    ruta = str(tmp_path / "prueba.db")
    seed.crear(ruta)
    monkeypatch.setattr(capa_db, "DB", ruta)

    from app import crear_app
    aplicacion = crear_app()
    aplicacion.config["TESTING"] = True
    with aplicacion.test_client() as c:
        yield c


def _csrf(c):
    return c.get("/api/csrf").get_json()["csrf_token"]


def _headers(c):
    return {"X-CSRF-Token": _csrf(c)}


def test_raiz_indica_modo_api(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert r.get_json()["modo"] == "api"


def test_encabezados_de_seguridad_en_api(cliente):
    r = cliente.get("/api/csrf")
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "default-src 'none'" in r.headers.get("Content-Security-Policy", "")


def test_post_sin_csrf_rechazado(cliente):
    r = cliente.post("/api/matriz", json={"rol_id": 1, "sistema_id": 1, "nivel": "L"})
    assert r.status_code == 403


def test_bitacora_registra_usuario_real_en_despliegue_integrado(cliente):
    h = _headers(cliente)
    matriz = cliente.get("/api/matriz").get_json()
    rol_id = matriz["roles"][0]["id"]
    sistema_id = matriz["sistemas"][0]["id"]
    cliente.put("/api/matriz", headers={**h, "X-Usuario-SGSI": "jljaramillo"},
                json={"rol_id": rol_id, "sistema_id": sistema_id, "nivel": "C"})
    con = sqlite3.connect(capa_db.DB)
    resp = con.execute(
        "SELECT responsable FROM log_auditoria ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    con.close()
    assert resp == "jljaramillo"


def test_vencimientos_automaticos(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.execute("UPDATE usuario SET estado='Temporal', fecha_fin='2026-01-01' WHERE id=9")
    con.execute(
        "INSERT INTO acceso_excepcion (usuario_id, sistema_id, nivel_codigo, motivo, fecha_fin) "
        "VALUES (5, 1, 'L', 'vencida', '2026-01-01')"
    )
    con.commit()
    con.close()

    from app import app as aplicacion
    with aplicacion.test_request_context():
        capa_db.aplicar_vencimientos(forzar=True)
        capa_db.cerrar_db()

    con = sqlite3.connect(capa_db.DB)
    assert con.execute("SELECT estado FROM usuario WHERE id=9").fetchone()[0] == "Suspendido"
    assert con.execute(
        "SELECT COUNT(*) FROM acceso_excepcion WHERE usuario_id=5 AND sistema_id=1"
    ).fetchone()[0] == 0
    con.close()


def test_cadena_de_auditoria_detecta_alteraciones(cliente):
    h = _headers(cliente)
    matriz = cliente.get("/api/matriz").get_json()
    rol_id, sistema_id = matriz["roles"][1]["id"], matriz["sistemas"][1]["id"]
    cliente.put("/api/matriz", headers=h,
                json={"rol_id": rol_id, "sistema_id": sistema_id, "nivel": "L"})

    from app import app as aplicacion
    with aplicacion.test_request_context():
        ok, total = capa_db.verificar_cadena()
        capa_db.cerrar_db()
    assert ok and total >= 2

    con = sqlite3.connect(capa_db.DB)
    con.execute("UPDATE log_auditoria SET detalle='manipulado' WHERE id=2")
    con.commit()
    con.close()
    with aplicacion.test_request_context():
        ok2, donde = capa_db.verificar_cadena()
        capa_db.cerrar_db()
    assert not ok2 and donde == 2


def test_api_resumen_expone_los_kpis_esperados(cliente):
    r = cliente.get("/api/resumen")
    assert r.status_code == 200
    data = r.get_json()
    claves = {"roles_total", "sistemas_total", "usuarios_activos",
              "mfa_pct", "mfa_ok", "mfa_total", "proximos_vencimientos",
              "excepciones_vigentes", "excepciones_vencidas",
              "roles_certificacion_vencida", "pendientes_total"}
    assert claves.issubset(data.keys())


def test_api_sistemas_expone_el_catalogo_canonico_con_accesos(cliente):
    r = cliente.get("/api/sistemas")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) > 0
    assert {"id", "nombre", "categoria", "clasificacion", "accesos",
            "excepciones_vigentes"} <= data[0].keys()


def test_catalogo_attack_json_disponible_en_static(cliente):
    r = cliente.get("/static/attack_tecnicas.json")
    assert r.status_code == 200
    datos = r.get_json()
    assert len(datos) > 500

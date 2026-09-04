#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC v2.0 — suite de pruebas (pytest).
Cubre autenticación, autorización por rol de aplicación, CSRF, gestión de la
matriz, excepciones, vencimientos automáticos, cadena de auditoría y
salvaguardas de integridad.   Ejecución:  pytest -q
"""
import io
import os
import re
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


def token_de(c, ruta):
    html = c.get(ruta).get_data(as_text=True)
    return re.search(r'name="_csrf" value="([0-9a-f]+)"', html).group(1), html


# ----------------------------------------------------------------- acceso
def test_tablero_accesible_sin_login(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "Tablero de control de acceso" in r.get_data(as_text=True)


def test_post_sin_token_csrf_rechazado(cliente):
    cliente.get("/")  # crea la sesión anónima con su token
    r = cliente.post("/matriz/editar",
                     data={"rol_id": 1, "sistema_id": 1, "nivel": "L"})
    assert r.status_code == 403


def test_encabezados_de_seguridad(cliente):
    r = cliente.get("/")
    # SAMEORIGIN (no DENY): despliegue integrado, el módulo se incrusta en
    # un <iframe> del Inventario servido bajo el mismo origen (nginx).
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp.split(
        "script-src")[1]


def test_csp_permite_las_fuentes_de_google_que_usa_base_html(cliente):
    """Regresión real: se agregaron las fuentes Space Grotesk/Inter/IBM Plex
    Mono a base.html en el rediseño visual sin revisar esta política — CSP
    las bloqueaba en silencio (confirmado con el error real de consola del
    navegador), RBAC caía a la fuente del sistema sin ningún aviso visible."""
    r = cliente.get("/")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "https://fonts.googleapis.com" in csp.split("style-src")[1].split(";")[0]
    assert "https://fonts.gstatic.com" in csp.split("font-src")[1].split(";")[0]


def test_embed_se_propaga_a_la_navegacion_interna(cliente):
    """Despliegue integrado: al cargar el módulo incrustado en el Inventario
    (?embed=1), los enlaces internos deben conservar ese parámetro para que
    la navegación no "salga" del modo incrustado."""
    html_normal = cliente.get("/").get_data(as_text=True)
    assert 'href="/matriz?embed=1"' not in html_normal
    assert 'href="/matriz"' in html_normal

    html_incrustado = cliente.get("/?embed=1").get_data(as_text=True)
    assert 'href="/matriz?embed=1"' in html_incrustado
    # el encabezado y el enlace de vuelta al Inventario no se duplican
    assert "Volver al Inventario de Activos SGSI" not in html_incrustado


def test_url_del_catalogo_attack_respeta_el_prefijo_del_gateway(cliente):
    """Bug real detectado en producción: static/app.js pedía el catálogo
    MITRE con una ruta absoluta hardcodeada ("/static/attack_tecnicas.json"),
    que en el despliegue integrado apunta a la raíz del dominio — servida
    por el Inventario, no por RBAC — y devolvía 404. La URL ahora se
    resuelve en el servidor (url_for, ya sensible al prefijo) y se expone
    en un atributo data- del <body> para que app.js la use en vez de
    reconstruirla. Además lleva un parámetro ?v= (cache-busting, ver
    static_v() en app.py) — otra causa real de que un arreglo en el
    servidor no se vea reflejado en el navegador."""
    html_normal = cliente.get("/").get_data(as_text=True)
    m = re.search(r'data-attack-catalog-url="([^"]+)"', html_normal)
    assert m, "no se encontró el atributo data-attack-catalog-url"
    assert m.group(1).startswith("/static/attack_tecnicas.json?v=")

    html_tras_gateway = cliente.get("/", headers={
        "X-Forwarded-Prefix": "/rbac",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "suiin.cric.local",
    }).get_data(as_text=True)
    m2 = re.search(r'data-attack-catalog-url="([^"]+)"', html_tras_gateway)
    assert m2 and m2.group(1).startswith("/rbac/static/attack_tecnicas.json?v=")


def test_static_v_cambia_la_url_si_el_archivo_cambia(cliente):
    """El parámetro de versión de static_v() se basa en la fecha de
    modificación del archivo: si el archivo cambia, la URL cambia, y el
    navegador nunca sirve una copia en caché desactualizada."""
    import app as appmod

    ruta = os.path.join(appmod.app.static_folder, "app.js")
    mtime_original = os.path.getmtime(ruta)
    try:
        os.utime(ruta, (mtime_original + 1000, mtime_original + 1000))
        html_despues = cliente.get("/").get_data(as_text=True)
        m = re.search(r'src="(/static/app\.js\?v=(\d+))"', html_despues)
        assert m and int(m.group(2)) == int(mtime_original) + 1000
    finally:
        os.utime(ruta, (mtime_original, mtime_original))  # dejar el archivo como estaba


# ------------------------------------------------------------------- negocio
def test_editor_edita_matriz_y_queda_en_bitacora(cliente):
    tok, _ = token_de(cliente, "/matriz")
    cliente.post("/matriz/editar", data={"rol_id": 1, "sistema_id": 1,
                                         "nivel": "L", "_csrf": tok})
    con = sqlite3.connect(capa_db.DB)
    assert con.execute("SELECT nivel_codigo FROM matriz_acceso "
                       "WHERE rol_id=1 AND sistema_id=1").fetchone()[0] == "L"
    detalle, resp = con.execute(
        "SELECT detalle, responsable FROM log_auditoria "
        "ORDER BY id DESC LIMIT 1").fetchone()
    assert "— → L" in detalle and resp == "operador local"


def test_bitacora_registra_usuario_real_en_despliegue_integrado(cliente):
    """Despliegue integrado: cuando nginx reenvía la identidad ya autorizada
    del Inventario (header X-Usuario-SGSI), la bitácora debe quedar con ese
    usuario en vez de 'operador local' — trazabilidad real (ISO 8.15)."""
    tok, _ = token_de(cliente, "/matriz")
    cliente.post("/matriz/editar",
                 data={"rol_id": 1, "sistema_id": 1, "nivel": "C", "_csrf": tok},
                 headers={"X-Usuario-SGSI": "jljaramillo"})
    con = sqlite3.connect(capa_db.DB)
    resp = con.execute(
        "SELECT responsable FROM log_auditoria ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    assert resp == "jljaramillo"


def test_asignacion_sin_motivo_rechazada(cliente):
    tok, html = token_de(cliente, "/usuarios/5")
    campos = dict(re.findall(
        r'name="(nivel_\d+)".*?selected>([ACMLT—])', html, re.S))
    sid = int(list(campos)[0].split("_")[1])
    campos[f"nivel_{sid}"] = "A"
    campos.update({"motivo": "", "_csrf": tok})
    cliente.post("/usuarios/5/asignar", data=campos)
    con = sqlite3.connect(capa_db.DB)
    assert con.execute("SELECT COUNT(*) FROM acceso_excepcion "
                       "WHERE usuario_id=5").fetchone()[0] == 0


def test_asignacion_con_motivo_crea_excepcion(cliente):
    tok, html = token_de(cliente, "/usuarios/5")
    campos = dict(re.findall(
        r'name="(nivel_\d+)".*?selected>([ACMLT—])', html, re.S))
    sid = int(next(k for k, v in campos.items() if v == "—").split("_")[1])
    campos[f"nivel_{sid}"] = "L"
    campos.update({"motivo": "Prueba documentada", "_csrf": tok})
    cliente.post("/usuarios/5/asignar", data=campos)
    con = sqlite3.connect(capa_db.DB)
    assert con.execute(
        "SELECT nivel_codigo FROM acceso_excepcion WHERE usuario_id=5 "
        "AND sistema_id=?", (sid,)).fetchone()[0] == "L"


def test_no_eliminar_rol_con_usuarios(cliente):
    tok, _ = token_de(cliente, "/roles")
    cliente.post("/roles/14/eliminar", data={"_csrf": tok})  # DTG con usuario
    con = sqlite3.connect(capa_db.DB)
    assert con.execute("SELECT COUNT(*) FROM rol WHERE id=14").fetchone()[0] == 1


# -------------------------------------------------------------- vencimientos
def test_vencimientos_automaticos(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.execute("UPDATE usuario SET estado='Temporal', fecha_fin='2026-01-01' "
                "WHERE id=9")
    con.execute("INSERT INTO acceso_excepcion (usuario_id, sistema_id, "
                "nivel_codigo, motivo, fecha_fin) "
                "VALUES (5, 1, 'L', 'vencida', '2026-01-01')")
    con.commit(); con.close()

    from app import app as aplicacion  # cualquier petición dispara la revisión
    with aplicacion.test_request_context():
        capa_db.aplicar_vencimientos(forzar=True)
        capa_db.cerrar_db()

    con = sqlite3.connect(capa_db.DB)
    assert con.execute("SELECT estado FROM usuario WHERE id=9"
                       ).fetchone()[0] == "Suspendido"
    assert con.execute("SELECT COUNT(*) FROM acceso_excepcion "
                       "WHERE usuario_id=5 AND sistema_id=1").fetchone()[0] == 0


# ----------------------------------------------------------------- auditoría
def test_cadena_de_auditoria_detecta_alteraciones(cliente):
    tok, _ = token_de(cliente, "/matriz")
    cliente.post("/matriz/editar", data={"rol_id": 2, "sistema_id": 2,
                                         "nivel": "L", "_csrf": tok})
    from app import app as aplicacion
    with aplicacion.test_request_context():
        ok, total = capa_db.verificar_cadena()
        capa_db.cerrar_db()
    assert ok and total >= 2

    con = sqlite3.connect(capa_db.DB)   # alteración externa maliciosa
    con.execute("UPDATE log_auditoria SET detalle='manipulado' WHERE id=2")
    con.commit(); con.close()
    with aplicacion.test_request_context():
        ok2, donde = capa_db.verificar_cadena()
        capa_db.cerrar_db()
    assert not ok2 and donde == 2


# ------------------------------------------------------- alta de usuario (robustez)
def test_alta_usuario_rechaza_nombre_vacio(cliente):
    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear",
                     data={"nombre": "   ", "rol_id": "1", "estado": "Activo",
                           "_csrf": tok}, follow_redirects=True)
    assert r.status_code == 200
    assert "nombre completo es obligatorio" in r.get_data(as_text=True)


def test_alta_usuario_temporal_exige_fechas(cliente):
    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear",
                     data={"nombre": "Proveedor X", "rol_id": "1",
                           "estado": "Temporal", "_csrf": tok},
                     follow_redirects=True)
    assert r.status_code == 200
    assert "requiere fecha de inicio" in r.get_data(as_text=True)


def test_alta_usuario_rechaza_fechas_invertidas(cliente):
    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear",
                     data={"nombre": "Proveedor Y", "rol_id": "1",
                           "estado": "Temporal", "fecha_inicio": "2026-06-01",
                           "fecha_fin": "2026-01-01", "_csrf": tok},
                     follow_redirects=True)
    assert "no puede ser anterior" in r.get_data(as_text=True)


def test_alta_usuario_rol_inexistente_no_rompe(cliente):
    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear",
                     data={"nombre": "Z", "rol_id": "abc", "estado": "Activo",
                           "_csrf": tok}, follow_redirects=True)
    assert r.status_code == 200


def test_alta_usuario_valida_crea_registro(cliente):
    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear",
                     data={"nombre": "Persona Nueva", "rol_id": "1",
                           "mfa_activo": "No", "estado": "Activo",
                           "_csrf": tok}, follow_redirects=True)
    assert "Persona Nueva" in r.get_data(as_text=True)


# -------------------------------------------------------------- matriz (robustez)
def test_matriz_editar_rechaza_nivel_invalido(cliente):
    tok, _ = token_de(cliente, "/matriz")
    r = cliente.post("/matriz/editar",
                     data={"rol_id": "1", "sistema_id": "1", "nivel": "ZZZ",
                           "_csrf": tok}, follow_redirects=True)
    assert r.status_code == 200
    assert "no reconocido" in r.get_data(as_text=True)


# ------------------------------------------------------- matriz (ronda 7)
def test_matriz_editar_ajax_responde_json(cliente):
    tok, _ = token_de(cliente, "/matriz")
    r = cliente.post("/matriz/editar",
                     data={"rol_id": "1", "sistema_id": "1", "nivel": "M",
                           "_csrf": tok},
                     headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    cuerpo = r.get_json()
    assert cuerpo["ok"] is True
    assert cuerpo["nuevo"] == "M"
    assert "rol" in cuerpo and "sistema" in cuerpo and "anterior" in cuerpo


def test_matriz_editar_ajax_nivel_invalido_devuelve_error_json(cliente):
    tok, _ = token_de(cliente, "/matriz")
    r = cliente.post("/matriz/editar",
                     data={"rol_id": "1", "sistema_id": "1", "nivel": "ZZZ",
                           "_csrf": tok},
                     headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 400
    cuerpo = r.get_json()
    assert cuerpo["ok"] is False


def test_matriz_comparar_marca_diferencias(cliente):
    tok, _ = token_de(cliente, "/matriz")
    cliente.post("/matriz/editar", data={"rol_id": "1", "sistema_id": "1",
                                         "nivel": "A", "_csrf": tok})
    cliente.post("/matriz/editar", data={"rol_id": "2", "sistema_id": "1",
                                         "nivel": "L", "_csrf": tok})
    r = cliente.get("/matriz/comparar?rol_a=1&rol_b=2")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "diferencia" in body


# --------------------------------------------- interfaz (ronda 8): errores,
# 404 en fichas inexistentes, favicon e historial en rol/sistema
def test_ficha_inexistente_devuelve_404_estilizado(cliente):
    for ruta in ("/usuarios/99999", "/roles/99999", "/sistemas/99999",
                "/esto-no-existe"):
        r = cliente.get(ruta)
        assert r.status_code == 404
        assert "Volver al inicio" in r.get_data(as_text=True)


def test_csrf_rechazado_usa_pagina_de_error_403(cliente):
    cliente.get("/")
    r = cliente.post("/matriz/editar",
                     data={"rol_id": "1", "sistema_id": "1", "nivel": "L"})
    assert r.status_code == 403
    assert "Volver al inicio" in r.get_data(as_text=True)


def test_favicon_servido(cliente):
    r = cliente.get("/static/favicon.svg")
    assert r.status_code == 200
    assert "svg" in r.content_type


def test_rol_y_sistema_enlazan_a_su_historial(cliente):
    assert "historial de auditoría de este rol" in \
        cliente.get("/roles/1").get_data(as_text=True)
    assert "historial de auditoría de este sistema" in \
        cliente.get("/sistemas/1").get_data(as_text=True)


# ---------------------------------------------------------- exportación CSV
def test_export_csv_neutraliza_inyeccion_de_formulas(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.execute("UPDATE sistema SET nombre='=2+5+cmd' WHERE id=1")
    con.commit(); con.close()
    r = cliente.get("/export/matriz.csv")
    assert "'=2+5+cmd" in r.get_data(as_text=True)


# ---------------------------------------------- excepción "Sin acceso" (ficha de sistema)
def test_excepcion_sin_acceso_oculta_usuario_en_ficha_de_sistema(cliente):
    uid = 5
    tok, html = token_de(cliente, f"/usuarios/{uid}")
    campos = dict(re.findall(
        r'name="(nivel_\d+)".*?selected>([ACMLT—])', html, re.S))
    # sistema donde el usuario 5 ya tiene acceso efectivo por su rol (nivel != —)
    sid = int(next(k for k, v in campos.items() if v != "—").split("_")[1])
    nombre = sqlite3.connect(capa_db.DB).execute(
        "SELECT nombre FROM usuario WHERE id=?", (uid,)).fetchone()[0]

    r = cliente.get(f"/sistemas/{sid}")
    assert nombre in r.get_data(as_text=True)

    campos[f"nivel_{sid}"] = "—"
    campos.update({"motivo": "Baja de acceso solicitada", "_csrf": tok})
    cliente.post(f"/usuarios/{uid}/asignar", data=campos)

    r = cliente.get(f"/sistemas/{sid}")
    assert nombre not in r.get_data(as_text=True)


# --------------------------------------------- vencimientos próximos (tablero)
def test_inicio_alerta_usuario_temporal_por_vencer(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.row_factory = sqlite3.Row
    con.execute("UPDATE usuario SET estado='Temporal', "
                "fecha_fin=date('now','+3 days') WHERE id=1")
    con.commit()
    nombre = con.execute("SELECT nombre FROM usuario WHERE id=1").fetchone()["nombre"]
    con.close()
    r = cliente.get("/")
    body = r.get_data(as_text=True)
    assert "Vencimientos próximos" in body
    assert nombre in body


def test_inicio_no_alerta_vencimiento_lejano(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.execute("UPDATE usuario SET estado='Temporal', "
                "fecha_fin=date('now','+60 days') WHERE id=1")
    con.commit(); con.close()
    r = cliente.get("/")
    assert "Vencimientos próximos" not in r.get_data(as_text=True)


# ------------------------------------------------- catálogo MITRE ATT&CK
def test_catalogo_attack_json_servido(cliente):
    r = cliente.get("/static/attack_tecnicas.json")
    assert r.status_code == 200
    datos = r.get_json()
    assert len(datos) > 500
    assert any(t["id"] == "T1566" for t in datos)


def test_sistema_crear_acepta_tecnicas_del_catalogo(cliente):
    tok, _ = token_de(cliente, "/sistemas")
    r = cliente.post("/sistemas/crear", data={
        "nombre": "Sistema con tecnicas MITRE validas", "categoria_id": "1",
        "clasificacion": "Interna", "tecnicas_attack": "T1566/T1566.001",
        "_csrf": tok}, follow_redirects=True)
    assert r.status_code == 200
    assert "Sistema con tecnicas MITRE validas" in r.get_data(as_text=True)
    fila = sqlite3.connect(capa_db.DB).execute(
        "SELECT tecnicas_attack FROM sistema WHERE nombre='Sistema con tecnicas MITRE validas'"
    ).fetchone()
    assert fila[0] == "T1566/T1566.001"


def test_sistema_crear_rechaza_tecnica_desconocida(cliente):
    tok, _ = token_de(cliente, "/sistemas")
    r = cliente.post("/sistemas/crear", data={
        "nombre": "Sistema con tecnica invalida", "categoria_id": "1",
        "clasificacion": "Interna", "tecnicas_attack": "T9999",
        "_csrf": tok}, follow_redirects=True)
    assert r.status_code == 200
    assert "no reconocida" in r.get_data(as_text=True).lower()
    assert not sqlite3.connect(capa_db.DB).execute(
        "SELECT 1 FROM sistema WHERE nombre='Sistema con tecnica invalida'"
    ).fetchone()


# --------------------------------------------------- registro de usuarios
def test_ficha_usuario_tiene_formulario_por_secciones_y_enlace_historial(cliente):
    _, html = token_de(cliente, "/usuarios/1")
    assert 'id="form-editar-usuario"' in html
    assert "Identidad y rol" in html
    assert "/auditoria?q=" in html


def test_auditoria_busca_por_texto_libre(cliente):
    tok, _ = token_de(cliente, "/usuarios/1")
    cliente.post("/usuarios/1/editar", data={
        "nombre": "Persona Buscable En Bitacora", "rol_id": "1",
        "mfa_activo": "No", "_csrf": tok})
    r = cliente.get("/auditoria?q=Persona+Buscable+En+Bitacora")
    assert "Persona Buscable En Bitacora" in r.get_data(as_text=True)


# ------------------------------------------------------- validaciones (ronda 5)
def test_sistema_eliminar_bloqueado_si_tiene_excepciones(cliente):
    uid = 5
    tok, html = token_de(cliente, f"/usuarios/{uid}")
    campos = dict(re.findall(
        r'name="(nivel_\d+)".*?selected>([ACMLT—])', html, re.S))
    sid = int(next(k for k, v in campos.items() if v != "—").split("_")[1])
    campos[f"nivel_{sid}"] = "—"
    campos.update({"motivo": "Prueba de protección", "_csrf": tok})
    cliente.post(f"/usuarios/{uid}/asignar", data=campos)

    tok2, _ = token_de(cliente, "/sistemas")
    r = cliente.post(f"/sistemas/{sid}/eliminar", data={"_csrf": tok2},
                     follow_redirects=True)
    assert "No se puede eliminar" in r.get_data(as_text=True)
    assert sqlite3.connect(capa_db.DB).execute(
        "SELECT 1 FROM sistema WHERE id=?", (sid,)).fetchone()


def test_sistema_eliminar_permitido_sin_excepciones(cliente):
    tok, _ = token_de(cliente, "/sistemas")
    cliente.post("/sistemas/crear", data={
        "nombre": "Sistema desechable de prueba", "categoria_id": "1",
        "clasificacion": "Interna", "_csrf": tok})
    sid = sqlite3.connect(capa_db.DB).execute(
        "SELECT id FROM sistema WHERE nombre='Sistema desechable de prueba'"
    ).fetchone()[0]
    tok2, _ = token_de(cliente, "/sistemas")
    r = cliente.post(f"/sistemas/{sid}/eliminar", data={"_csrf": tok2},
                     follow_redirects=True)
    assert "eliminado definitivamente" in r.get_data(as_text=True)
    assert not sqlite3.connect(capa_db.DB).execute(
        "SELECT 1 FROM sistema WHERE id=?", (sid,)).fetchone()


def test_alta_usuario_avisa_duplicado_en_otro_rol(cliente):
    con = sqlite3.connect(capa_db.DB)
    con.row_factory = sqlite3.Row
    nombre_existente = con.execute(
        "SELECT nombre FROM usuario WHERE estado='Activo' LIMIT 1").fetchone()["nombre"]
    otro_rol = con.execute(
        "SELECT id FROM rol WHERE activo=1 AND id NOT IN "
        "(SELECT rol_id FROM usuario WHERE nombre=?)", (nombre_existente,)
    ).fetchone()["id"]
    con.close()

    tok, _ = token_de(cliente, "/usuarios")
    r = cliente.post("/usuarios/crear", data={
        "nombre": nombre_existente, "rol_id": str(otro_rol), "mfa_activo": "No",
        "estado": "Activo", "_csrf": tok}, follow_redirects=True)
    assert "distinto al que acaba de asignar" in r.get_data(as_text=True)


# --------------------------------------------- funcionalidad nueva (ronda 6)
def test_rol_revisar_marca_certificacion_y_bitacora(cliente):
    r = cliente.get("/roles")
    assert "nunca revisado" in r.get_data(as_text=True)

    tok, _ = token_de(cliente, "/roles/1")
    r = cliente.post("/roles/1/revisar", data={"nota": "Confirmado con el área",
                                                "_csrf": tok}, follow_redirects=True)
    assert "marcado como revisado" in r.get_data(as_text=True)

    fila = sqlite3.connect(capa_db.DB).execute(
        "SELECT ultima_revision FROM rol WHERE id=1").fetchone()
    assert fila[0] is not None

    detalle = sqlite3.connect(capa_db.DB).execute(
        "SELECT detalle FROM log_auditoria WHERE accion='REVISION'").fetchone()
    assert detalle and "Confirmado con el área" in detalle[0]


def test_rol_clonar_copia_la_matriz_del_origen(cliente):
    con = sqlite3.connect(capa_db.DB)
    origen = dict(con.execute(
        "SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=1"))
    con.close()

    tok, _ = token_de(cliente, "/roles")
    r = cliente.post("/roles/crear", data={
        "codigo": "900", "abreviatura": "CLONPRB", "denominacion": "Clon de prueba",
        "grupo_id": "1", "mfa_requerido": "No", "riesgo_attack": "Bajo",
        "revision_periodica": "Anual", "clonar_de": "1", "_csrf": tok},
        follow_redirects=True)
    assert r.status_code == 200

    con = sqlite3.connect(capa_db.DB)
    nuevo_id = con.execute(
        "SELECT id FROM rol WHERE abreviatura='CLONPRB'").fetchone()[0]
    clon = dict(con.execute(
        "SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=?",
        (nuevo_id,)))
    assert clon == origen


def test_matriz_importar_previsualiza_y_confirma_cambios(cliente):
    texto = cliente.get("/export/matriz.csv").get_data().decode("utf-8-sig")
    lineas = texto.splitlines()
    partes = lineas[1].split(";")
    partes[1] = "A" if partes[1] != "A" else "L"
    lineas[1] = ";".join(partes)
    csv_modificado = "\n".join(lineas).encode("utf-8")

    tok, _ = token_de(cliente, "/matriz")
    r = cliente.post("/matriz/importar", data={
        "archivo": (io.BytesIO(csv_modificado), "matriz.csv"), "_csrf": tok},
        content_type="multipart/form-data")
    body = r.get_data(as_text=True)
    assert "Cambios detectados (1)" in body

    tok2 = re.search(r'name="_csrf" value="([0-9a-f]+)"', body).group(1)
    campos = {"n": "1", "_csrf": tok2}
    campos["c0_rol"] = re.search(r'name="c0_rol" value="(\d+)"', body).group(1)
    campos["c0_sistema"] = re.search(r'name="c0_sistema" value="(\d+)"', body).group(1)
    campos["c0_nivel"] = re.search(r'name="c0_nivel" value="([^"]*)"', body).group(1)
    r2 = cliente.post("/matriz/importar/confirmar", data=campos, follow_redirects=True)
    assert "Importación aplicada" in r2.get_data(as_text=True)
    assert sqlite3.connect(capa_db.DB).execute(
        "SELECT 1 FROM log_auditoria WHERE accion='IMPORTACION'").fetchone()


def test_matriz_importar_rechaza_nivel_desconocido_sin_aplicarlo(cliente):
    texto = cliente.get("/export/matriz.csv").get_data().decode("utf-8-sig")
    lineas = texto.splitlines()
    partes = lineas[1].split(";")
    partes[1] = "ZZ"
    lineas[1] = ";".join(partes)
    csv_malo = "\n".join(lineas).encode("utf-8")

    tok, _ = token_de(cliente, "/matriz")
    r = cliente.post("/matriz/importar", data={
        "archivo": (io.BytesIO(csv_malo), "matriz.csv"), "_csrf": tok},
        content_type="multipart/form-data")
    body = r.get_data(as_text=True)
    assert "no es un nivel válido" in body
    assert "Cambios detectados (0)" in body


def test_excepcion_masiva_aplica_a_varios_usuarios(cliente):
    tok, html = token_de(cliente, "/excepciones/masiva")
    ids = re.findall(r'name="usuario_id" value="(\d+)"', html)[:3]
    r = cliente.post("/excepciones/masiva/aplicar", data={
        "sistema_id": "1", "nivel": "L", "motivo": "Contratistas externos",
        "usuario_id": ids, "_csrf": tok}, follow_redirects=True)
    assert f"Excepción aplicada a {len(ids)} usuario" in r.get_data(as_text=True)
    n = sqlite3.connect(capa_db.DB).execute(
        "SELECT COUNT(*) FROM acceso_excepcion WHERE sistema_id=1 AND nivel_codigo='L'"
    ).fetchone()[0]
    assert n == len(ids)


def test_excepcion_masiva_exige_motivo(cliente):
    tok, html = token_de(cliente, "/excepciones/masiva")
    ids = re.findall(r'name="usuario_id" value="(\d+)"', html)[:1]
    r = cliente.post("/excepciones/masiva/aplicar", data={
        "sistema_id": "1", "nivel": "L", "usuario_id": ids, "_csrf": tok},
        follow_redirects=True)
    assert "motivo" in r.get_data(as_text=True).lower()


# ------------------------------------------------------- despliegue integrado
def test_api_resumen_expone_los_kpis_esperados(cliente):
    """Despliegue integrado: el Inventario consume este endpoint para el
    badge de pendientes de la pestaña "Matriz RBAC" y para el Panel
    ejecutivo consolidado. Si cambian estas claves, hay que actualizar
    también inventario/views.py:dashboard_ejecutivo()."""
    r = cliente.get("/api/resumen")
    assert r.status_code == 200
    data = r.get_json()
    claves = {"roles_total", "sistemas_total", "usuarios_activos",
              "mfa_pct", "mfa_ok", "mfa_total", "proximos_vencimientos",
              "excepciones_vigentes", "excepciones_vencidas",
              "roles_certificacion_vencida", "pendientes_total"}
    assert claves.issubset(data.keys())
    assert data["pendientes_total"] == (
        data["proximos_vencimientos"] + data["excepciones_vencidas"]
        + data["roles_certificacion_vencida"])


def test_api_sistemas_expone_el_catalogo_canonico_con_accesos(cliente):
    """Despliegue integrado: el Inventario consulta este endpoint (por
    nombre de sistema) para mostrar los accesos reales de la matriz MCA en
    la ficha de cada Sistema de información, en vez de depender solo de su
    propia copia (Django RolMCA/AccesoRol)."""
    r = cliente.get("/api/sistemas")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) > 0
    primero = data[0]
    assert {"id", "nombre", "categoria", "clasificacion", "accesos",
            "excepciones_vigentes"} <= primero.keys()
    con_accesos = [s for s in data if s["accesos"]]
    assert con_accesos, "se esperaba al menos un sistema con accesos en la matriz"
    acceso = con_accesos[0]["accesos"][0]
    assert {"rol", "denominacion", "nivel"} <= acceso.keys()


def test_api_sistemas_cuenta_excepciones_vigentes_por_sistema(cliente):
    """Base de la Correlación de riesgo cruzado: el Inventario cruza esto
    con sus propios activos de riesgo Crítico/Alto."""
    tok, html = token_de(cliente, "/excepciones/masiva")
    ids = re.findall(r'name="usuario_id" value="(\d+)"', html)[:2]
    cliente.post("/excepciones/masiva/aplicar", data={
        "sistema_id": "1", "nivel": "L", "motivo": "prueba de correlacion",
        "usuario_id": ids, "_csrf": tok}, follow_redirects=True)

    data = cliente.get("/api/sistemas").get_json()
    sistema_1 = next(s for s in data if s["id"] == 1)
    assert sistema_1["excepciones_vigentes"] >= len(ids)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — capa de datos: conexión, auditoría encadenada y vencimientos."""
import hashlib
import os
import sqlite3
import time
from datetime import datetime

from flask import g, has_request_context, request

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "rbac.db")

_ultimo_vencimiento = 0.0  # limitador: la revisión corre a lo sumo 1 vez/min


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA busy_timeout = 10000")
        g.db.execute("PRAGMA synchronous = NORMAL")
        g.db.execute("PRAGMA cache_size = -8000")   # ~8 MB de caché de páginas
    return g.db


def cerrar_db(_exc=None):
    d = g.pop("db", None)
    if d:
        d.close()


# ------------------------------------------------------ auditoría encadenada
def _hash_registro(prev, fecha, entidad, accion, detalle, responsable):
    base = f"{prev}|{fecha}|{entidad}|{accion}|{detalle}|{responsable}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _responsable_actual():
    """Despliegue integrado: nginx protege /rbac/ delegando la autorización
    en la sesión y el rol del Inventario (ver auth_check_rbac en Django), y
    reenvía la identidad ya autorizada en el header X-Usuario-SGSI (nginx lo
    fija él mismo a partir de la subpetición interna, así que un cliente no
    puede falsificarlo). Si ese header no viene (uso local/pruebas/scripts
    de línea de comandos), se conserva el comportamiento original."""
    if has_request_context():
        usuario = request.headers.get("X-Usuario-SGSI")
        if usuario:
            return usuario
    return "operador local"


def audit(entidad, accion, detalle, con=None, responsable=None):
    """Registra en la bitácora encadenada. El responsable es la cuenta en
    sesión, salvo que se indique otro (p. ej. 'sistema' en tareas internas)."""
    c = con or db()
    if responsable is None:
        responsable = _responsable_actual()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev = c.execute(
        "SELECT hash FROM log_auditoria ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = prev["hash"] if prev else "GENESIS"
    h = _hash_registro(prev_hash, fecha, entidad, accion, detalle, responsable)
    c.execute(
        "INSERT INTO log_auditoria (fecha, entidad, accion, detalle, "
        "responsable, hash) VALUES (?,?,?,?,?,?)",
        (fecha, entidad, accion, detalle, responsable, h))
    c.commit()


def verificar_cadena(con=None):
    """Recorre la bitácora y verifica la cadena de hashes.
    Devuelve (True, total) o (False, id_del_primer_registro_alterado)."""
    c = con or db()
    prev = "GENESIS"
    total = 0
    for r in c.execute("SELECT * FROM log_auditoria ORDER BY id"):
        esperado = _hash_registro(prev, r["fecha"], r["entidad"], r["accion"],
                                  r["detalle"], r["responsable"])
        if r["hash"] != esperado:
            return False, r["id"]
        prev = r["hash"]
        total += 1
    return True, total


# ------------------------------------------------------ vencimientos
def aplicar_vencimientos(forzar=False):
    """Ejecuta a lo sumo una vez por minuto:
    - usuarios en estado Temporal con fecha_fin pasada → Suspendido;
    - excepciones de acceso con fecha_fin pasada → retiradas.
    Todo con registro en bitácora a nombre de 'sistema'."""
    global _ultimo_vencimiento
    ahora = time.time()
    if not forzar and ahora - _ultimo_vencimiento < 60:
        return
    _ultimo_vencimiento = ahora
    c = db()
    hoy = datetime.now().strftime("%Y-%m-%d")

    vencidos = c.execute(
        "SELECT u.id, u.nombre, u.fecha_fin, r.abreviatura rol FROM usuario u "
        "JOIN rol r ON r.id=u.rol_id "
        "WHERE u.estado='Temporal' AND u.fecha_fin IS NOT NULL "
        "AND date(u.fecha_fin) < date(?)", (hoy,)).fetchall()
    for v in vencidos:
        c.execute(
            "UPDATE usuario SET estado='Suspendido', "
            "notas=COALESCE(notas,'') || ' [Acceso temporal vencido el ' "
            "|| ? || '; suspendido automáticamente]', "
            "actualizado=datetime('now','localtime') WHERE id=?",
            (v["fecha_fin"], v["id"]))
        c.commit()
        audit("usuario", "REVOCACION",
              f"{v['nombre']} ({v['rol']}): acceso temporal vencido el "
              f"{v['fecha_fin']}; suspendido automáticamente.",
              con=c, responsable="sistema")

    exc = c.execute(
        """SELECT e.usuario_id, e.sistema_id, e.fecha_fin,
                  u.nombre usuario, s.nombre sistema
           FROM acceso_excepcion e
           JOIN usuario u ON u.id=e.usuario_id
           JOIN sistema s ON s.id=e.sistema_id
           WHERE e.fecha_fin IS NOT NULL
             AND date(e.fecha_fin) < date(?)""", (hoy,)).fetchall()
    for e in exc:
        c.execute("DELETE FROM acceso_excepcion "
                  "WHERE usuario_id=? AND sistema_id=?",
                  (e["usuario_id"], e["sistema_id"]))
        c.commit()
        audit("usuario", "REVOCACION",
              f"Excepción vencida el {e['fecha_fin']} retirada "
              f"automáticamente: {e['usuario']} sobre «{e['sistema']}» "
              "vuelve al nivel de su rol.", con=c, responsable="sistema")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUIIN-RBAC — Carga inicial de la base de datos.
Crea rbac.db aplicando schema.sql y carga los datos reales extraídos
del documento SUIIN-SGSI-MCA-001 v2.0 (rbac_data.json).

Uso:  python3 seed.py
"""
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime

import catalogo_attack

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "rbac.db")

GRUPOS = [
    ("GOB", "Gobierno"), ("ASE", "Asesoría"), ("LID", "Liderazgo"),
    ("PRO", "Profesional"), ("CON", "Conocimiento"), ("TEC", "Tecnología"),
    ("COL", "Colaboración"), ("OPE", "Operativo"),
    ("TI", "TI Privilegiado"), ("EXT", "Externo"),
]

NIVELES = [
    ("A", "Admin", "Acceso completo + configuración del sistema + gestión de cuentas. "
     "Exclusivo para roles TI autorizados. MFA obligatorio. Revisión trimestral.", 1),
    ("C", "Completo", "Crear, Leer, Actualizar y Eliminar (CRUD). "
     "Acceso operativo total al sistema o módulo asignado.", 2),
    ("M", "Modificar", "Leer y Actualizar. Sin creación ni eliminación de registros principales.", 3),
    ("L", "Lectura", "Solo consulta (Read Only). Sin modificación de ningún dato.", 4),
    ("T", "Temporal", "Acceso limitado por tiempo con NDA vigente. Solo proveedores o "
     "auditores autorizados. Fecha inicio/fin obligatoria.", 5),
    ("—", "Sin acceso", "El rol no tiene ningún nivel de acceso a este sistema o módulo.", 6),
]


def crear(db_path):
    """Crea la base en db_path con los datos del documento MCA-001 v2.0."""
    with open(os.path.join(BASE, "rbac_data.json"), encoding="utf-8") as f:
        data = json.load(f)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())

    cur = con.cursor()
    cur.executemany("INSERT INTO grupo_rol (codigo, nombre) VALUES (?,?)", GRUPOS)
    cur.executemany(
        "INSERT INTO nivel_acceso (codigo, nombre, descripcion, orden) VALUES (?,?,?,?)",
        NIVELES,
    )
    gid = {n: cur.execute("SELECT id FROM grupo_rol WHERE nombre=?", (n,)).fetchone()[0]
           for _, n in GRUPOS}

    rid = {}
    for r in data["roles"]:
        cur.execute(
            """INSERT INTO rol (codigo, abreviatura, denominacion, grupo_id, cosecha,
                                en_det7, funcion, mfa_requerido, riesgo_attack,
                                revision_periodica, observaciones)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (r["codigo"], r["abrev"], r["denominacion"], gid[r["grupo"]],
             r["cosecha"], 1 if r["en_det7"] else 0, r.get("funcion", ""),
             r["mfa"], r["riesgo"], r["revision"], r.get("nota", "")),
        )
        rid[r["codigo"]] = cur.lastrowid

    cat_id = {}
    sid = {}
    for s in data["sistemas"]:
        c = s["categoria"]
        if c not in cat_id:
            cur.execute("INSERT INTO categoria_sistema (nombre) VALUES (?)", (c,))
            cat_id[c] = cur.lastrowid
        cur.execute(
            "INSERT INTO sistema (nombre, categoria_id, clasificacion, tecnicas_attack) "
            "VALUES (?,?,?,?)",
            (s["nombre"], cat_id[c], s["clasificacion"], s["attck"]),
        )
        sid[s["nombre"]] = cur.lastrowid

    cur.executemany(
        "INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo) VALUES (?,?,?)",
        [(rid[m["rol_codigo"]], sid[m["sistema"]], m["nivel"]) for m in data["matriz"]],
    )

    for u in data["usuarios"]:
        estado = ("Revocado" if "REVOCADO" in u["estado"].upper()
                  else "Temporal" if u["estado"].startswith("Temporal")
                  else "Activo")
        cur.execute(
            "INSERT INTO usuario (nombre, rol_id, mfa_activo, nda, estado, notas) "
            "VALUES (?,?,?,?,?,?)",
            (u["nombre"], rid[u["rol_codigo"]], u["mfa_activo"], u["nda"],
             estado, u["estado"] if estado != "Activo" or "—" in u["estado"] else ""),
        )

    # Primer registro de la bitácora encadenada
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detalle = ("Carga inicial desde SUIIN-SGSI-MCA-001 v2.0: "
               f"{len(data['roles'])} roles, {len(data['sistemas'])} sistemas, "
               f"{len(data['matriz'])} celdas de matriz, "
               f"{len(data['usuarios'])} usuarios.")
    h = hashlib.sha256(
        f"GENESIS|{fecha}|sistema|ALTA|{detalle}|sistema".encode()).hexdigest()
    cur.execute(
        "INSERT INTO log_auditoria (fecha, entidad, accion, detalle, "
        "responsable, hash) VALUES (?,?,?,?,?,?)",
        (fecha, "sistema", "ALTA", detalle, "sistema", h))
    con.commit()

    n = cur.execute(
        "SELECT COUNT(*) FROM matriz_acceso WHERE nivel_codigo<>'—'"
    ).fetchone()[0]
    n_attack = catalogo_attack.sincronizar(con)
    print(f"Base creada: {db_path}")
    print(f"  Roles: {len(rid)} | Sistemas: {len(sid)} | "
          f"Accesos definidos: {n} | Catálogo ATT&CK: {n_attack} técnicas")
    con.close()


def main():
    if os.path.exists(DB):
        print(f"Ya existe {DB}. Elimínelo si desea recargar desde cero.")
        sys.exit(1)
    crear(DB)


if __name__ == "__main__":
    main()

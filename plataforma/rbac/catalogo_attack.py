#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — catálogo de técnicas MITRE ATT&CK (Enterprise).

Los datos oficiales se generan con catalogo_attack_actualizar.py a partir
del Excel de MITRE y se guardan en static/attack_tecnicas.json. Este
módulo replica ese archivo en la tabla attack_tecnica para poder validar
del lado del servidor las técnicas que se asignan a cada sistema, y lo
usan tanto seed.py (carga inicial) como migrar_v2_1.py (bases existentes).
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_CATALOGO = os.path.join(BASE, "static", "attack_tecnicas.json")


def cargar_json():
    with open(ARCHIVO_CATALOGO, encoding="utf-8") as f:
        return json.load(f)


def sincronizar(con):
    """Crea attack_tecnica si falta y la repuebla desde el JSON del
    catálogo. Idempotente: puede llamarse en cada arranque/migración."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS attack_tecnica (
            id             TEXT PRIMARY KEY,
            nombre         TEXT NOT NULL,
            tactica        TEXT,
            es_subtecnica  INTEGER NOT NULL DEFAULT 0,
            padre          TEXT
        )""")
    tecnicas = cargar_json()
    con.execute("DELETE FROM attack_tecnica")
    con.executemany(
        "INSERT INTO attack_tecnica (id, nombre, tactica, es_subtecnica, padre) "
        "VALUES (?,?,?,?,?)",
        [(t["id"], t["nombre"], t.get("tactica", ""),
          1 if t.get("es_subtecnica") else 0, t.get("padre")) for t in tecnicas])
    con.commit()
    return len(tecnicas)

#!/usr/bin/env python3
"""Migración: columna espacio_codigo en sistema, usuario y acceso_excepcion.

Los datos demo existentes quedan en espacio «organizacion». Las cuentas nuevas
reciben su propio espacio vacío vía header X-Espacio-Datos.

Uso: python3 migrar_espacio_datos.py
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "rbac.db")
ESPACIO_DEFAULT = "organizacion"


def _columnas(con, tabla):
    return [r[1] for r in con.execute(f"PRAGMA table_info({tabla})")]


def _agregar_columna_espacio(con, tabla):
    if "espacio_codigo" in _columnas(con, tabla):
        return False
    con.execute(
        f"ALTER TABLE {tabla} ADD COLUMN espacio_codigo TEXT NOT NULL "
        f"DEFAULT '{ESPACIO_DEFAULT}'"
    )
    print(f"Columna espacio_codigo agregada a {tabla}.")
    return True


def _recrear_sistema_unicidad_espacio(con):
    """Nombre único por espacio, no globalmente."""
    idx = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='sistema' "
        "AND sql LIKE '%UNIQUE%' AND sql LIKE '%nombre%'"
    ).fetchall()
    if not idx and "espacio_codigo" in _columnas(con, "sistema"):
        # Comprobar si ya hay índice compuesto
        comp = con.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_sistema_espacio_nombre'"
        ).fetchone()
        if comp:
            return False

    con.executescript("""
    CREATE TABLE IF NOT EXISTS sistema_new (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre           TEXT NOT NULL,
        categoria_id     INTEGER NOT NULL REFERENCES categoria_sistema(id),
        clasificacion    TEXT NOT NULL CHECK (clasificacion IN
                           ('Altamente Confidencial','Confidencial','Interna','Pública')),
        tecnicas_attack  TEXT,
        activo           INTEGER NOT NULL DEFAULT 1,
        espacio_codigo   TEXT NOT NULL DEFAULT 'organizacion',
        UNIQUE (espacio_codigo, nombre)
    );
    INSERT INTO sistema_new (id, nombre, categoria_id, clasificacion, tecnicas_attack,
                             activo, espacio_codigo)
    SELECT id, nombre, categoria_id, clasificacion, tecnicas_attack, activo,
           COALESCE(espacio_codigo, 'organizacion')
    FROM sistema;
    DROP TABLE sistema;
    ALTER TABLE sistema_new RENAME TO sistema;
    CREATE INDEX IF NOT EXISTS idx_sistema_espacio ON sistema(espacio_codigo);
    """)
    print("Tabla sistema: unicidad (espacio_codigo, nombre) aplicada.")
    return True


def migrar(db_path=DB):
    if not os.path.exists(db_path):
        print(f"No existe {db_path} — omitiendo migración de espacio.")
        return
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        for tabla in ("sistema", "usuario", "acceso_excepcion"):
            _agregar_columna_espacio(con, tabla)
        _recrear_sistema_unicidad_espacio(con)
        con.commit()
        print("Migración de espacio de datos RBAC completa.")
    finally:
        con.close()


if __name__ == "__main__":
    migrar()

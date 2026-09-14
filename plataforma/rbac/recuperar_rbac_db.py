#!/usr/bin/env python3
"""Detecta rbac.db corrupta (p. ej. tabla sistema ausente) y la restaura.

La migración migrar_espacio_datos.py puede dejar la base inconsistente si se
interrumpe tras DROP TABLE sistema. Este script hace respaldo del archivo
dañado y lo reemplaza por rbac.db.referencia (copia embebida en la imagen).

Uso: python3 recuperar_rbac_db.py
"""
import os
import shutil
import sqlite3
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "rbac.db")
REFERENCIA = os.path.join(BASE, "rbac.db.referencia")

_TABLAS_CRITICAS = ("sistema", "rol", "usuario", "matriz_acceso", "acceso_excepcion")
_COLUMNAS_ESPACIO = ("sistema", "usuario", "acceso_excepcion")
_VISTAS_CRITICAS = ("v_accesos_usuario", "v_roles_criticos", "v_alertas_mfa")


def _tabla_existe(con, nombre):
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,),
        ).fetchone()
        is not None
    )


def _columnas(con, tabla):
    return [r[1] for r in con.execute(f"PRAGMA table_info({tabla})")]


def _vistas_ok(con):
    return all(
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' AND name=?",
            (vista,),
        ).fetchone()
        for vista in _VISTAS_CRITICAS
    )


def integridad_ok(db_path=DB):
    if not os.path.exists(db_path):
        return False
    con = sqlite3.connect(db_path)
    try:
        if not all(_tabla_existe(con, t) for t in _TABLAS_CRITICAS):
            return False
        for tabla in _COLUMNAS_ESPACIO:
            if "espacio_codigo" not in _columnas(con, tabla):
                return False
        return _vistas_ok(con)
    finally:
        con.close()


def recuperar_si_corrupta(db_path=DB, referencia=REFERENCIA):
    """Restaura desde referencia si faltan tablas críticas. Devuelve True si restauró."""
    if integridad_ok(db_path):
        print("Integridad RBAC OK.")
        return False

    con = sqlite3.connect(db_path) if os.path.exists(db_path) else None
    tablas_ok = False
    if con is not None:
        try:
            tablas_ok = all(_tabla_existe(con, t) for t in _TABLAS_CRITICAS)
        finally:
            con.close()

    if tablas_ok:
        print("RBAC incompleta (columnas/vistas) — se reparará con migrar_espacio_datos.py.")
        return False

    if not os.path.exists(referencia):
        raise SystemExit(
            f"No existe {referencia}. Reconstruya la imagen rbac o restaure rbac.db desde git."
        )

    if os.path.exists(db_path):
        marca = int(time.time())
        respaldo = f"{db_path}.corrupt.{marca}"
        shutil.copy2(db_path, respaldo)
        print(f"Respaldo de base dañada: {respaldo}")

    shutil.copy2(referencia, db_path)
    print(f"rbac.db restaurada desde {referencia}.")
    print("Ejecute migrar_espacio_datos.py para aplicar columnas espacio_codigo y vistas.")
    return True


if __name__ == "__main__":
    recuperar_si_corrupta()

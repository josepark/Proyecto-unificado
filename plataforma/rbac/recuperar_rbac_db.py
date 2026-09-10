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


def _tabla_existe(con, nombre):
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,),
        ).fetchone()
        is not None
    )


def integridad_ok(db_path=DB):
    if not os.path.exists(db_path):
        return False
    con = sqlite3.connect(db_path)
    try:
        return all(_tabla_existe(con, t) for t in _TABLAS_CRITICAS)
    finally:
        con.close()


def recuperar_si_corrupta(db_path=DB, referencia=REFERENCIA):
    """Restaura desde referencia si faltan tablas críticas. Devuelve True si restauró."""
    if integridad_ok(db_path):
        print("Integridad RBAC OK.")
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
    if not integridad_ok(db_path):
        raise SystemExit("La referencia RBAC tampoco es válida — revise rbac.db.referencia.")
    return True


if __name__ == "__main__":
    recuperar_si_corrupta()

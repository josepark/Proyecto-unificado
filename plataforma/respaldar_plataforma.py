#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plataforma SUIIN-SGSI — Respaldo único de las dos aplicaciones.

Antes de la unificación, cada app tenía su propia rutina de respaldo
(rbac/respaldar.py, y una copia manual del db.sqlite3/media del
Inventario). Este script las reemplaza con una sola rutina que respalda
ambas bases de datos (con el método de "online backup" de SQLite, seguro
de correr aunque la aplicación esté en uso) más los archivos multimedia
del Inventario (diagramas, documentos de hoja de vida), todo en un único
.tar.gz fechado.

Uso manual:
    python3 respaldar_plataforma.py

Programado en cron (ejemplo, diario a las 02:00), corriendo directamente
sobre los archivos del host — no hace falta que los contenedores estén
arriba, y si lo están, no hay que detenerlos:

    0 2 * * *  cd /ruta/suiin-plataforma && python3 respaldar_plataforma.py >> respaldos/respaldar.log 2>&1

Conserva las últimas 30 copias (igual que ya hacía rbac/respaldar.py).
"""
import os
import shutil
import sqlite3
import tarfile
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_RESPALDOS = os.path.join(BASE, "respaldos")
RETENCION = 30


def _copia_consistente_sqlite(origen_path, destino_path):
    """Copia consistente de una base SQLite usando el Online Backup API
    (seguro incluso con la aplicación escribiendo al mismo tiempo)."""
    origen = sqlite3.connect(origen_path)
    copia = sqlite3.connect(destino_path)
    origen.backup(copia)
    copia.close()
    origen.close()


def respaldar():
    os.makedirs(DIR_RESPALDOS, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = os.path.join(DIR_RESPALDOS, f".tmp_{marca}")
    os.makedirs(tmp, exist_ok=True)

    db_inventario = os.path.join(BASE, "inventario", "db.sqlite3")
    db_rbac = os.path.join(BASE, "rbac", "rbac.db")
    media_inventario = os.path.join(BASE, "inventario", "media")

    if os.path.exists(db_inventario):
        _copia_consistente_sqlite(db_inventario, os.path.join(tmp, "inventario_db.sqlite3"))
    else:
        print(f"AVISO: no se encontró {db_inventario}, se omite.")

    if os.path.exists(db_rbac):
        _copia_consistente_sqlite(db_rbac, os.path.join(tmp, "rbac.db"))
    else:
        print(f"AVISO: no se encontró {db_rbac}, se omite.")

    if os.path.isdir(media_inventario):
        shutil.copytree(media_inventario, os.path.join(tmp, "media"))

    destino = os.path.join(DIR_RESPALDOS, f"suiin_plataforma_{marca}.tar.gz")
    with tarfile.open(destino, "w:gz") as tar:
        tar.add(tmp, arcname=marca)
    shutil.rmtree(tmp)
    print(f"Respaldo creado: {destino}")

    copias = sorted(
        f for f in os.listdir(DIR_RESPALDOS)
        if f.startswith("suiin_plataforma_") and f.endswith(".tar.gz"))
    for viejo in copias[:-RETENCION]:
        os.remove(os.path.join(DIR_RESPALDOS, viejo))
        print(f"Retención: eliminado {viejo}")


if __name__ == "__main__":
    respaldar()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plataforma SUIIN-SGSI — Respaldo único de las tres aplicaciones.

Antes de la unificación, cada app tenía su propia rutina de respaldo
(rbac/respaldar.py, y una copia manual del db.sqlite3/media del
Inventario). Este script las reemplaza con una sola rutina que respalda
las tres bases de datos (Inventario, RBAC y Riesgos — con el método de
"online backup" de SQLite, seguro de correr aunque la aplicación esté
en uso) más los archivos multimedia del Inventario y de Riesgos, todo en
un único .tar.gz fechado.

Uso manual:
    python3 respaldar_plataforma.py
    python3 respaldar_plataforma.py --verificar   # solo comprueba el último respaldo

Programado en cron (ejemplo, diario a las 02:00), corriendo directamente
sobre los archivos del host — no hace falta que los contenedores estén
arriba, y si lo están, no hay que detenerlos:

    0 2 * * *  cd /ruta/suiin-plataforma && python3 respaldar_plataforma.py >> respaldos/respaldar.log 2>&1

Conserva las últimas 30 copias (igual que ya hacía rbac/respaldar.py).
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_RESPALDOS = os.path.join(BASE, "respaldos")
RETENCION = 30
MIEMBROS_SQLITE = (
    "inventario_db.sqlite3",
    "rbac.db",
    "riesgos_db.sqlite3",
)
MIEMBROS_POSTGRES = (
    "inventario_pg.sql",
    "riesgos_pg.sql",
    "rbac_pg.sql",
    "rbac.db",
)


def _leer_env():
    valores = {}
    ruta = os.path.join(BASE, ".env")
    if not os.path.isfile(ruta):
        return valores
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip()
    return valores


def _usa_postgresql(env):
    return env.get("DJANGO_DB_ENGINE") == "postgresql"


def _pg_dump(env, database, destino_path):
    usuario = env.get("DJANGO_DB_USER", "suiin")
    password = env.get("DJANGO_DB_PASSWORD", "")
    cmd = [
        "docker", "compose",
        "-f", os.path.join(BASE, "docker-compose.yml"),
        "-f", os.path.join(BASE, "docker-compose.postgres.yml"),
        "exec", "-T", "postgres",
        "pg_dump", "-U", usuario, "--no-owner", "--no-acl", database,
    ]
    entorno = os.environ.copy()
    entorno["PGPASSWORD"] = password
    with open(destino_path, "w", encoding="utf-8") as salida:
        subprocess.run(cmd, check=True, stdout=salida, env=entorno)


def _copia_consistente_sqlite(origen_path, destino_path):
    """Copia consistente de una base SQLite usando el Online Backup API
    (seguro incluso con la aplicación escribiendo al mismo tiempo)."""
    origen = sqlite3.connect(origen_path)
    copia = sqlite3.connect(destino_path)
    origen.backup(copia)
    copia.close()
    origen.close()


def _verificar_archivo(destino: str, miembros_esperados) -> None:
    if not os.path.isfile(destino):
        raise RuntimeError(f"No se creó el respaldo: {destino}")
    with tarfile.open(destino, "r:gz") as tar:
        nombres = {m.split("/")[-1] for m in tar.getnames() if "/" in m}
        faltantes = [m for m in miembros_esperados if m not in nombres]
        if len(faltantes) == len(miembros_esperados):
            raise RuntimeError(f"El tar no contiene bases reconocibles: {destino}")
        if faltantes:
            print(f"AVISO: faltan en el tar: {', '.join(faltantes)}")


def respaldar() -> str:
    os.makedirs(DIR_RESPALDOS, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = os.path.join(DIR_RESPALDOS, f".tmp_{marca}")
    os.makedirs(tmp, exist_ok=True)

    env = _leer_env()
    postgres = _usa_postgresql(env)

    db_inventario = os.path.join(BASE, "inventario", "db.sqlite3")
    db_rbac = os.path.join(BASE, "rbac", "rbac.db")
    db_riesgos = os.path.join(BASE, "riesgos", "backend", "db.sqlite3")
    media_inventario = os.path.join(BASE, "inventario", "media")
    media_riesgos = os.path.join(BASE, "riesgos", "backend", "media")

    if postgres:
        try:
            _pg_dump(env, env.get("DJANGO_DB_NAME", "suiin_inventario"),
                     os.path.join(tmp, "inventario_pg.sql"))
            _pg_dump(env, env.get("RIESGOS_DB_NAME", "suiin_riesgos"),
                     os.path.join(tmp, "riesgos_pg.sql"))
            _pg_dump(env, env.get("RBAC_DB_NAME", "suiin_rbac"),
                     os.path.join(tmp, "rbac_pg.sql"))
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"AVISO: pg_dump falló ({exc}) — ¿postgres arriba?")
    else:
        if os.path.exists(db_inventario):
            _copia_consistente_sqlite(db_inventario, os.path.join(tmp, "inventario_db.sqlite3"))
        else:
            print(f"AVISO: no se encontró {db_inventario}, se omite.")

        if os.path.exists(db_riesgos):
            _copia_consistente_sqlite(db_riesgos, os.path.join(tmp, "riesgos_db.sqlite3"))
        else:
            print(f"AVISO: no se encontró {db_riesgos}, se omite.")

    if os.path.exists(db_rbac):
        _copia_consistente_sqlite(db_rbac, os.path.join(tmp, "rbac.db"))
    else:
        print(f"AVISO: no se encontró {db_rbac}, se omite.")

    if os.path.isdir(media_inventario):
        shutil.copytree(media_inventario, os.path.join(tmp, "media_inventario"))

    if os.path.isdir(media_riesgos):
        shutil.copytree(media_riesgos, os.path.join(tmp, "media_riesgos"))

    destino = os.path.join(DIR_RESPALDOS, f"suiin_plataforma_{marca}.tar.gz")
    miembros = MIEMBROS_POSTGRES if postgres else MIEMBROS_SQLITE
    with tarfile.open(destino, "w:gz") as tar:
        tar.add(tmp, arcname=marca)
    shutil.rmtree(tmp)
    print(f"Respaldo creado: {destino}")

    _verificar_archivo(destino, miembros)

    copias = sorted(
        f for f in os.listdir(DIR_RESPALDOS)
        if f.startswith("suiin_plataforma_") and f.endswith(".tar.gz"))
    for viejo in copias[:-RETENCION]:
        os.remove(os.path.join(DIR_RESPALDOS, viejo))
        print(f"Retención: eliminado {viejo}")

    return destino


def verificar_ultimo() -> int:
    copias = sorted(
        f for f in os.listdir(DIR_RESPALDOS)
        if f.startswith("suiin_plataforma_") and f.endswith(".tar.gz")
    ) if os.path.isdir(DIR_RESPALDOS) else []
    if not copias:
        print("ERROR: no hay respaldos en respaldos/", file=sys.stderr)
        return 1
    ultimo = os.path.join(DIR_RESPALDOS, copias[-1])
    env = _leer_env()
    miembros = MIEMBROS_POSTGRES if _usa_postgresql(env) else MIEMBROS_SQLITE
    try:
        _verificar_archivo(ultimo, miembros)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"OK — último respaldo verificado: {copias[-1]}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verificar", action="store_true", help="Verificar el último .tar.gz sin crear uno nuevo")
    args = parser.parse_args()
    if args.verificar:
        sys.exit(verificar_ultimo())
    respaldar()


if __name__ == "__main__":
    main()

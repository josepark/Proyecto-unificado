#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plataforma SUIIN-SGSI — Restauración desde respaldo unificado.

Restaura bases SQLite o volcados PostgreSQL (Inventario/Riesgos), RBAC
(SQLite) y carpetas media desde un .tar.gz creado por respaldar_plataforma.py.
Crea un respaldo de seguridad inmediatamente antes de sobrescribir datos.

Uso:
    python3 restaurar_plataforma.py respaldos/suiin_plataforma_20260101_020000.tar.gz --confirmar
    python3 restaurar_plataforma.py --ultimo --confirmar

Requiere --confirmar (evita restauraciones accidentales).
Con PostgreSQL activo, el contenedor postgres debe estar en ejecución.
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIR_RESPALDOS = BASE / "respaldos"

DESTINOS_SQLITE = {
    "inventario_db.sqlite3": BASE / "inventario" / "db.sqlite3",
    "rbac.db": BASE / "rbac" / "rbac.db",
    "riesgos_db.sqlite3": BASE / "riesgos" / "backend" / "db.sqlite3",
    "media_inventario": BASE / "inventario" / "media",
    "media_riesgos": BASE / "riesgos" / "backend" / "media",
}

DESTINOS_POSTGRES = {
    "inventario_pg.sql": ("inventario", "DJANGO_DB_NAME", "suiin_inventario"),
    "riesgos_pg.sql": ("riesgos", "RIESGOS_DB_NAME", "suiin_riesgos"),
    "rbac.db": BASE / "rbac" / "rbac.db",
    "media_inventario": BASE / "inventario" / "media",
    "media_riesgos": BASE / "riesgos" / "backend" / "media",
}

MIEMBROS_SQLITE = frozenset(DESTINOS_SQLITE.keys())
MIEMBROS_POSTGRES = frozenset(DESTINOS_POSTGRES.keys())


def _leer_env():
    valores = {}
    ruta = BASE / ".env"
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip()
    return valores


def _usa_postgresql(env):
    return env.get("DJANGO_DB_ENGINE") == "postgresql"


def _ultimo_respaldo() -> Path:
    copias = sorted(DIR_RESPALDOS.glob("suiin_plataforma_*.tar.gz"))
    if not copias:
        raise FileNotFoundError(f"No hay respaldos en {DIR_RESPALDOS}/")
    return copias[-1]


def _miembros_tar(ruta: Path) -> set[str]:
    with tarfile.open(ruta, "r:gz") as tar:
        miembros = tar.getnames()
        if not miembros:
            raise ValueError("El archivo tar está vacío.")
        return {m.split("/")[-1] for m in miembros if "/" in m}


def _formato_respaldo(presentes: set[str]) -> str:
    if presentes & {"inventario_pg.sql", "riesgos_pg.sql"}:
        return "postgresql"
    if presentes & {"inventario_db.sqlite3", "riesgos_db.sqlite3"}:
        return "sqlite"
    raise ValueError(
        f"El respaldo no contiene archivos reconocibles. Encontrados: {sorted(presentes)}"
    )


def _verificar_tar(ruta: Path) -> str:
    presentes = _miembros_tar(ruta)
    return _formato_respaldo(presentes)


def _respaldar_antes() -> None:
    script = BASE / "respaldar_plataforma.py"
    if script.exists():
        print("Creando respaldo de seguridad antes de restaurar…")
        subprocess.run([sys.executable, str(script)], check=True)
    else:
        print("AVISO: respaldar_plataforma.py no encontrado — sin respaldo previo.")


def _restaurar_sqlite(origen: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    shutil.copy2(origen, destino)
    with sqlite3.connect(destino) as conn:
        conn.execute("PRAGMA integrity_check")


def _restaurar_media(origen_dir: Path, destino_dir: Path) -> None:
    if destino_dir.exists():
        shutil.rmtree(destino_dir)
    shutil.copytree(origen_dir, destino_dir)


def _compose_cmd(*args):
    return [
        "docker", "compose",
        "-f", str(BASE / "docker-compose.yml"),
        "-f", str(BASE / "docker-compose.postgres.yml"),
        *args,
    ]


def _pg_recrear_db(env, database: str) -> None:
    if not database.replace("_", "").isalnum():
        raise ValueError(f"Nombre de base inválido: {database!r}")
    usuario = env.get("DJANGO_DB_USER", "suiin")
    password = env.get("DJANGO_DB_PASSWORD", "")
    sql = (
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{database}' AND pid <> pg_backend_pid();\n"
        f"DROP DATABASE IF EXISTS {database};\n"
        f"CREATE DATABASE {database} OWNER {usuario};\n"
    )
    entorno = os.environ.copy()
    entorno["PGPASSWORD"] = password
    subprocess.run(
        _compose_cmd("exec", "-T", "postgres", "psql", "-U", usuario, "-d", "postgres", "-v", "ON_ERROR_STOP=1"),
        input=sql.encode("utf-8"),
        check=True,
        env=entorno,
    )


def _postgres_en_ejecucion() -> bool:
    try:
        resultado = subprocess.run(
            _compose_cmd("ps", "--status", "running", "postgres"),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return resultado.returncode == 0 and "postgres" in resultado.stdout


def _pg_restaurar_dump(env, database: str, origen_sql: Path) -> None:
    usuario = env.get("DJANGO_DB_USER", "suiin")
    password = env.get("DJANGO_DB_PASSWORD", "")
    entorno = os.environ.copy()
    entorno["PGPASSWORD"] = password
    with origen_sql.open("rb") as entrada:
        subprocess.run(
            _compose_cmd(
                "exec", "-T", "postgres",
                "psql", "-U", usuario, "-d", database, "-v", "ON_ERROR_STOP=1",
            ),
            stdin=entrada,
            check=True,
            env=entorno,
        )


def _restaurar_postgres(contenido: Path, env) -> None:
    if not _usa_postgresql(env):
        raise RuntimeError(
            "El respaldo contiene volcados PostgreSQL pero .env no tiene "
            "DJANGO_DB_ENGINE=postgresql. Ejecute ./scripts/activar-postgresql.sh "
            "y levante postgres antes de restaurar."
        )
    if not _postgres_en_ejecucion():
        raise RuntimeError(
            "El contenedor postgres no está disponible. Levante el stack con "
            "./desplegar.sh --postgres antes de restaurar."
        )

    for nombre, destino in DESTINOS_POSTGRES.items():
        origen = contenido / nombre
        if not origen.exists():
            print(f"AVISO: {nombre} no está en el respaldo, se omite.")
            continue
        if isinstance(destino, tuple):
            _, clave_env, default_db = destino
            database = env.get(clave_env, default_db)
            print(f"Restaurando {nombre} → PostgreSQL/{database}")
            _pg_recrear_db(env, database)
            _pg_restaurar_dump(env, database, origen)
        elif origen.is_dir():
            print(f"Restaurando {nombre} → {destino}")
            _restaurar_media(origen, destino)
        else:
            print(f"Restaurando {nombre} → {destino}")
            _restaurar_sqlite(origen, destino)


def _restaurar_sqlite_backup(contenido: Path) -> None:
    for nombre, destino in DESTINOS_SQLITE.items():
        origen = contenido / nombre
        if not origen.exists():
            print(f"AVISO: {nombre} no está en el respaldo, se omite.")
            continue
        if origen.is_dir():
            print(f"Restaurando {nombre} → {destino}")
            _restaurar_media(origen, destino)
        else:
            print(f"Restaurando {nombre} → {destino}")
            _restaurar_sqlite(origen, destino)


def restaurar(ruta_respaldo: Path) -> None:
    formato = _verificar_tar(ruta_respaldo)
    env = _leer_env()
    _respaldar_antes()

    with tempfile.TemporaryDirectory(prefix="suiin_restore_") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(ruta_respaldo, "r:gz") as tar:
            tar.extractall(tmp_path)

        subdirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        if len(subdirs) != 1:
            raise RuntimeError("Estructura de respaldo inesperada (se esperaba un solo subdirectorio).")
        contenido = subdirs[0]

        if formato == "postgresql":
            _restaurar_postgres(contenido, env)
        else:
            if _usa_postgresql(env):
                print(
                    "AVISO: .env usa PostgreSQL pero el respaldo es SQLite. "
                    "Se restauran archivos .sqlite3 en disco (RBAC/media siempre); "
                    "para volver a PostgreSQL use ./scripts/migrar-sqlite-a-postgresql.sh."
                )
            _restaurar_sqlite_backup(contenido)

    print(f"Restauración completada desde {ruta_respaldo.name}")
    if _usa_postgresql(env):
        print("Reinicie los contenedores: ./desplegar.sh --postgres")
    else:
        print("Reinicie los contenedores: docker compose up -d --build")


def main():
    parser = argparse.ArgumentParser(description="Restaura un respaldo unificado de la plataforma.")
    parser.add_argument("respaldo", nargs="?", help="Ruta al .tar.gz (omitir con --ultimo)")
    parser.add_argument("--ultimo", action="store_true", help="Usar el respaldo más reciente")
    parser.add_argument("--confirmar", action="store_true", help="Confirmar sobrescritura de datos")
    args = parser.parse_args()

    if not args.confirmar:
        print("ERROR: agregue --confirmar para ejecutar la restauración.", file=sys.stderr)
        sys.exit(2)

    if args.ultimo:
        ruta = _ultimo_respaldo()
    elif args.respaldo:
        ruta = Path(args.respaldo)
        if not ruta.is_absolute():
            ruta = BASE / ruta
    else:
        parser.error("Indique un archivo de respaldo o use --ultimo")

    if not ruta.exists():
        print(f"No se encontró {ruta}", file=sys.stderr)
        sys.exit(1)

    restaurar(ruta)


if __name__ == "__main__":
    main()

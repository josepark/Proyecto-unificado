#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plataforma SUIIN-SGSI — Restauración desde respaldo unificado.

Restaura las bases SQLite y carpetas media desde un .tar.gz creado por
respaldar_plataforma.py. Crea un respaldo de seguridad inmediatamente
antes de sobrescribir archivos en disco.

Uso:
    python3 restaurar_plataforma.py respaldos/suiin_plataforma_20260101_020000.tar.gz --confirmar
    python3 restaurar_plataforma.py --ultimo --confirmar

Requiere --confirmar (evita restauraciones accidentales).
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

DESTINOS = {
    "inventario_db.sqlite3": BASE / "inventario" / "db.sqlite3",
    "rbac.db": BASE / "rbac" / "rbac.db",
    "riesgos_db.sqlite3": BASE / "riesgos" / "backend" / "db.sqlite3",
    "media_inventario": BASE / "inventario" / "media",
    "media_riesgos": BASE / "riesgos" / "backend" / "media",
}


def _ultimo_respaldo() -> Path:
    copias = sorted(
        f for f in DIR_RESPALDOS.glob("suiin_plataforma_*.tar.gz")
    )
    if not copias:
        raise FileNotFoundError(f"No hay respaldos en {DIR_RESPALDOS}/")
    return copias[-1]


def _verificar_tar(ruta: Path) -> None:
    with tarfile.open(ruta, "r:gz") as tar:
        miembros = tar.getnames()
        if not miembros:
            raise ValueError("El archivo tar está vacío.")
        raiz = miembros[0].split("/")[0]
        esperados = set(DESTINOS.keys())
        presentes = {m.split("/")[-1] for m in miembros if "/" in m}
        if not esperados & presentes:
            raise ValueError(
                f"El respaldo no contiene archivos reconocibles. Encontrados: {sorted(presentes)}"
            )


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


def restaurar(ruta_respaldo: Path) -> None:
    _verificar_tar(ruta_respaldo)
    _respaldar_antes()

    with tempfile.TemporaryDirectory(prefix="suiin_restore_") as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(ruta_respaldo, "r:gz") as tar:
            tar.extractall(tmp_path)

        subdirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        if len(subdirs) != 1:
            raise RuntimeError("Estructura de respaldo inesperada (se esperaba un solo subdirectorio).")
        contenido = subdirs[0]

        for nombre, destino in DESTINOS.items():
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

    print(f"Restauración completada desde {ruta_respaldo.name}")
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

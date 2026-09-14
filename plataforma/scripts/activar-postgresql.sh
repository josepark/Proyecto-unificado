#!/bin/bash
# Activa PostgreSQL para Inventario y Riesgos (opcional — producción concurrente).
#
# Uso (desde plataforma/):
#   ./scripts/activar-postgresql.sh
#   docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
#   docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec inventario python manage.py migrate
#
# Requiere contraseña en .env: DJANGO_DB_PASSWORD

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

if [ ! -f .env ]; then
    rojo "Copie .env.example a .env primero."
    exit 1
fi

python3 - <<'PY'
import re
from pathlib import Path
ruta = Path(".env")
lineas = ruta.read_text(encoding="utf-8").splitlines()
cambios = {
    "DJANGO_DB_ENGINE": "postgresql",
    "DJANGO_DB_NAME": "suiin_inventario",
    "DJANGO_DB_USER": "suiin",
    "DJANGO_DB_HOST": "postgres",
    "DJANGO_DB_PORT": "5432",
}
for clave, valor in cambios.items():
    patron = re.compile(rf"^{re.escape(clave)}=.*$")
    encontrada = False
    for i, linea in enumerate(lineas):
        if patron.match(linea):
            lineas[i] = f"{clave}={valor}"
            encontrada = True
            break
    if not encontrada:
        lineas.append(f"{clave}={valor}")
    print(f"  .env → {clave}={valor}")
if not any(l.startswith("DJANGO_DB_PASSWORD=") and not l.endswith("=") for l in lineas):
    import secrets
    pwd = secrets.token_urlsafe(24)
    lineas.append(f"DJANGO_DB_PASSWORD={pwd}")
    print(f"  .env → DJANGO_DB_PASSWORD=<generada>")
ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
PY

verde "PostgreSQL configurado en .env."
echo ""
echo "Arranque con override:"
echo "  docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build"
echo ""
echo "Migración inicial (SQLite → PostgreSQL requiere pgloader o dump manual — ver README-DESPLIEGUE.md)."

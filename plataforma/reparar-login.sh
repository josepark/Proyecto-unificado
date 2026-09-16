#!/bin/bash
# Repara login 401 sin re-migrar PostgreSQL (admin / SUIIN2026#).
# Uso: ./reparar-login.sh   (desde plataforma/)

set -euo pipefail

cd "$(dirname "$0")"

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

if [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
    COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)
else
    COMPOSE=(docker compose)
fi

if ! "${COMPOSE[@]}" ps inventario 2>/dev/null | grep -qE 'Up|running'; then
    rojo "Contenedor inventario no está Up. Ejecute primero: ./desplegar.sh --postgres"
    exit 1
fi

echo "=== Reparar acceso demo (admin / SUIIN2026#) ==="
"${COMPOSE[@]}" exec -T inventario python manage.py reparar_acceso_demo --probar-http

verde "Login reparado. Pruebe: http://localhost/login/  →  admin / SUIIN2026#"

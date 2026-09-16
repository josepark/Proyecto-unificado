#!/bin/bash
# Repara login 401 sin re-migrar PostgreSQL (admin / SUIIN2026#).
# Uso: ./reparar-login.sh   (desde plataforma/)

set -euo pipefail

cd "$(dirname "$0")"

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

# shellcheck disable=SC1091
source scripts/lib/probar-login-nginx.sh

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
    rojo "Contenedor inventario no está Up. Ejecute: ./desplegar.sh --postgres"
    exit 1
fi

echo "=== Reparar acceso demo (admin / SUIIN2026#) ==="
"${COMPOSE[@]}" exec -T inventario python manage.py reparar_acceso_demo

echo ""
echo "=== Prueba login vía nginx (como el navegador) ==="
if probar_login_nginx admin 'SUIIN2026#'; then
    verde "Login reparado. Abra http://localhost/login/ → admin / SUIIN2026#"
else
    amarillo "La contraseña quedó restablecida pero nginx no respondió 200."
    amarillo "Revise: docker compose ps nginx inventario && ./diagnostico_login.sh"
    exit 1
fi

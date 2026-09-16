#!/bin/bash
# Crea suiin_riesgos y suiin_rbac si faltan (volúmenes PG creados antes de Fase 1.1).
#
# Los scripts en postgres/init/ solo corren la primera vez que el volumen está vacío.
# Este script es idempotente y se ejecuta en cada despliegue con PostgreSQL.
#
# Uso (desde plataforma/, con postgres Up):
#   ./scripts/asegurar-bases-postgresql.sh

set -euo pipefail

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

if [ "${DJANGO_DB_ENGINE:-}" != "postgresql" ]; then
    echo "DJANGO_DB_ENGINE no es postgresql — omitiendo."
    exit 0
fi

DB_USER="${DJANGO_DB_USER:-suiin}"
DB_MAIN="${DJANGO_DB_NAME:-suiin_inventario}"
DB_RIES="${RIESGOS_DB_NAME:-suiin_riesgos}"
DB_RBAC="${RBAC_DB_NAME:-suiin_rbac}"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)

if ! "${COMPOSE[@]}" ps postgres 2>/dev/null | grep -qE 'Up|running'; then
    rojo "El servicio postgres no está en ejecución."
    exit 1
fi

crear_si_falta() {
    local nombre=$1
    "${COMPOSE[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 \
        --username "$DB_USER" --dbname "$DB_MAIN" <<-EOSQL
SELECT 'CREATE DATABASE ${nombre} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${nombre}')\gexec
EOSQL
    verde "Base ${nombre} verificada."
}

crear_si_falta "$DB_RIES"
crear_si_falta "$DB_RBAC"

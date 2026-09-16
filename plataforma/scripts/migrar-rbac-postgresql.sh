#!/bin/bash
# Migra rbac/rbac.db (Flask SQLite) → PostgreSQL suiin_rbac (Django rbac).
#
# Uso (desde plataforma/, con stack PostgreSQL arriba):
#   ./scripts/migrar-rbac-postgresql.sh
#   ./scripts/migrar-rbac-postgresql.sh --dry-run

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)
ORIGEN_CONTAINER="/app/rbac_origen/rbac.db"

if [ ! -f rbac/rbac.db ]; then
    rojo "No se encontró rbac/rbac.db — nada que migrar."
    exit 1
fi

"${COMPOSE[@]}" exec -T inventario python manage.py migrate rbac --database=rbac --noinput

ARGS=(--origen "$ORIGEN_CONTAINER")
if [ "${1:-}" = "--dry-run" ]; then
    ARGS+=(--dry-run)
elif [ "${1:-}" = "--forzar" ] || [ -z "${1:-}" ]; then
    ARGS+=(--forzar)
else
    rojo "Uso: $0 [--dry-run|--forzar]"
    exit 1
fi

"${COMPOSE[@]}" exec -T inventario python manage.py migrar_rbac_sqlite "${ARGS[@]}"
verde "RBAC migrado a suiin_rbac (alias rbac). Flask sigue usando rbac.db hasta Fase 1.5."

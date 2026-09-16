#!/bin/bash
# Migra datos SQLite → PostgreSQL (Inventario + Riesgos).
# RBAC sigue en SQLite (rbac.db) — ver README-DESPLIEGUE.md.
#
# Uso (desde plataforma/):
#   ./scripts/migrar-sqlite-a-postgresql.sh
#   ./scripts/migrar-sqlite-a-postgresql.sh --solo-vacio   # sin pgloader (BD nueva)
#
# Requisitos: Docker, .env con DJANGO_DB_PASSWORD (activar-postgresql.sh lo genera).

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

SOLO_VACIO=false
if [ "${1:-}" = "--solo-vacio" ]; then
    SOLO_VACIO=true
fi

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)

cargar_env() {
    set -a
    # shellcheck disable=SC1091
    [ -f .env ] && source .env
    set +a
}

paso() { echo ""; echo "=== $1 ==="; }

paso "1/7 · Respaldo SQLite antes de migrar"
python3 respaldar_plataforma.py

paso "2/7 · Configurar .env para PostgreSQL"
if [ "${DJANGO_DB_ENGINE:-}" != "postgresql" ]; then
    ./scripts/activar-postgresql.sh
fi
cargar_env

if [ -z "${DJANGO_DB_PASSWORD:-}" ]; then
    rojo "Falta DJANGO_DB_PASSWORD en .env"
    exit 1
fi

DB_INV="${DJANGO_DB_NAME:-suiin_inventario}"
DB_RIES="${RIESGOS_DB_NAME:-suiin_riesgos}"
DB_USER="${DJANGO_DB_USER:-suiin}"
DB_HOST="${DJANGO_DB_HOST:-postgres}"

uri_pg() {
    local db=$1
    printf 'postgresql://%s:%s@%s:5432/%s' "$DB_USER" "$DJANGO_DB_PASSWORD" "$DB_HOST" "$db"
}

paso "3/7 · Levantar PostgreSQL"
"${COMPOSE[@]}" down 2>/dev/null || true
"${COMPOSE[@]}" up -d postgres --wait

sqlite_tiene_datos() {
    local f=$1
    [ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)" -gt 8192 ]
}

if $SOLO_VACIO; then
    amarillo "Modo --solo-vacio: se omitirá pgloader."
else
    paso "4/7 · pgloader SQLite → PostgreSQL"
    if sqlite_tiene_datos inventario/db.sqlite3; then
        amarillo "Migrando Inventario…"
        "${COMPOSE[@]}" --profile migrate run --rm pgloader \
            pgloader /sqlite/inventario.db "$(uri_pg "$DB_INV")"
    else
        amarillo "inventario/db.sqlite3 vacío o ausente — se creará esquema con migrate."
    fi
    if sqlite_tiene_datos riesgos/backend/db.sqlite3; then
        amarillo "Migrando Riesgos…"
        "${COMPOSE[@]}" --profile migrate run --rm pgloader \
            pgloader /sqlite/riesgos.db "$(uri_pg "$DB_RIES")"
    else
        amarillo "riesgos/backend/db.sqlite3 vacío o ausente — se creará esquema con migrate."
    fi
fi

paso "5/7 · Arrancar stack completo con PostgreSQL"
"${COMPOSE[@]}" up -d --build --wait --wait-timeout 240

paso "6/7 · Alinear migraciones Django"
if sqlite_tiene_datos inventario/db.sqlite3 && ! $SOLO_VACIO; then
    "${COMPOSE[@]}" exec -T inventario python manage.py migrate --fake-initial --noinput
else
    "${COMPOSE[@]}" exec -T inventario python manage.py migrate --noinput
fi
if sqlite_tiene_datos riesgos/backend/db.sqlite3 && ! $SOLO_VACIO; then
    "${COMPOSE[@]}" exec -T riesgos-backend python manage.py migrate --fake-initial --noinput
else
    "${COMPOSE[@]}" exec -T riesgos-backend python manage.py migrate --noinput
fi

paso "6b/7 · Usuarios demo (admin suele faltar si SQLite de Inventario estaba vacío)"
"${COMPOSE[@]}" exec -T inventario python manage.py crear_roles
"${COMPOSE[@]}" exec -T inventario python manage.py desbloquear_login admin || true

paso "7/7 · Verificación"
./scripts/verificar-postgresql.sh

verde "Migración a PostgreSQL completada."
echo ""
echo "Despliegues futuros:"
echo "  ./desplegar.sh --postgres --purgar --desbloquear admin"
echo ""
echo "RBAC permanece en rbac/rbac.db (SQLite)."

#!/bin/bash
# Plataforma SUIIN-SGSI — PostgreSQL en un solo comando
#
# Hace TODO: secretos, respaldo SQLite, activar .env, pgloader, despliegue
# completo, usuarios demo (admin), MITRE, sync activos y verificación.
#
# Uso (desde plataforma/):
#   ./postgresql.sh
#   ./postgresql.sh --solo-vacio          # BD nueva, sin pgloader
#   ./postgresql.sh --reset-passwords     # restablece admin / SUIIN2026#
#
# Equivalente: ./scripts/postgresql-completo.sh

set -euo pipefail

SOLO_VACIO=false
RESET_PASSWORDS=false

mostrar_ayuda() {
    cat <<'EOF'
PostgreSQL — un solo script para migrar y desplegar la plataforma.

  ./postgresql.sh                         # migración + despliegue completo
  ./postgresql.sh --solo-vacio            # sin pgloader (bases vacías)
  ./postgresql.sh --reset-passwords         # restablece contraseñas demo

Incluye: respaldo, activar .env, pgloader, desplegar.sh --postgres,
usuarios admin/consultor/dinamizador, MITRE, sync activos y verificación.

Login demo tras ejecutar: admin / SUIIN2026#

Despliegues posteriores (PostgreSQL ya activo):
  ./desplegar.sh --postgres --purgar --desbloquear admin
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --solo-vacio) SOLO_VACIO=true; shift ;;
        --reset-passwords) RESET_PASSWORDS=true; shift ;;
        -h|--help) mostrar_ayuda; exit 0 ;;
        *) echo "Argumento desconocido: $1 (use --help)" >&2; exit 1 ;;
    esac
done

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }
paso() { echo ""; echo "=== $1 ==="; }

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

sqlite_tiene_datos() {
    local f=$1
    [ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)" -gt 8192 ]
}

paso "1/8 · Requisitos"
if ! command -v docker >/dev/null 2>&1; then
    rojo "docker no está instalado."
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    rojo "Se requiere docker compose v2."
    exit 1
fi

paso "2/8 · .env y secretos"
if [ ! -f .env ]; then
    cp .env.example .env
    amarillo "Creado .env desde .env.example"
fi
python3 generar_secretos.py
python3 validar_secretos.py

paso "3/8 · Respaldo SQLite antes de migrar"
python3 respaldar_plataforma.py

paso "4/8 · Activar PostgreSQL en .env"
./scripts/activar-postgresql.sh
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

MIGRO_INVENTARIO=false
MIGRO_RIESGOS=false
if ! $SOLO_VACIO; then
    sqlite_tiene_datos inventario/db.sqlite3 && MIGRO_INVENTARIO=true
    sqlite_tiene_datos riesgos/backend/db.sqlite3 && MIGRO_RIESGOS=true
fi

paso "5/8 · Levantar PostgreSQL y pgloader"
"${COMPOSE[@]}" down 2>/dev/null || true
"${COMPOSE[@]}" up -d postgres --wait

if $SOLO_VACIO; then
    amarillo "Modo --solo-vacio: se omitirá pgloader."
elif $MIGRO_INVENTARIO || $MIGRO_RIESGOS; then
    if $MIGRO_INVENTARIO; then
        amarillo "Migrando Inventario (SQLite → PostgreSQL)…"
        "${COMPOSE[@]}" --profile migrate run --rm pgloader \
            pgloader /sqlite/inventario.db "$(uri_pg "$DB_INV")"
    else
        amarillo "inventario/db.sqlite3 vacío — esquema se creará con migrate."
    fi
    if $MIGRO_RIESGOS; then
        amarillo "Migrando Riesgos (SQLite → PostgreSQL)…"
        "${COMPOSE[@]}" --profile migrate run --rm pgloader \
            pgloader /sqlite/riesgos.db "$(uri_pg "$DB_RIES")"
    else
        amarillo "riesgos/backend/db.sqlite3 vacío — esquema se creará con migrate."
    fi
else
    amarillo "Sin datos SQLite que migrar — esquemas se crearán con migrate."
fi

paso "6/8 · Despliegue completo (stack + MITRE + sync + login)"
DESPLEGAR_ARGS=(--postgres --purgar --desbloquear admin --reset-passwords)
if $MIGRO_INVENTARIO || $MIGRO_RIESGOS; then
    DESPLEGAR_ARGS+=(--migrate-fake-initial)
fi
./desplegar.sh "${DESPLEGAR_ARGS[@]}"

paso "7/8 · Reparar login demo (contraseña + MFA + axes)"
"${COMPOSE[@]}" exec -T inventario python manage.py reparar_acceso_demo --probar-http

paso "8/8 · Verificación PostgreSQL"
./scripts/verificar-postgresql.sh

verde "PostgreSQL listo — plataforma desplegada."
echo ""
echo "Acceda en: http://localhost/login/"
echo "  admin / SUIIN2026#"
echo "  dinamizador / Dinamizador2026#"
echo "  consultor / Consultor2026#"
echo ""
echo "Despliegues futuros:"
echo "  ./desplegar.sh --postgres --purgar --desbloquear admin"
echo ""
echo "RBAC permanece en rbac/rbac.db (SQLite)."

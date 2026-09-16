#!/bin/bash
# Verifica PostgreSQL activo y conectividad desde los contenedores Django.
# Uso: ./scripts/verificar-postgresql.sh   (desde plataforma/)

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

FALLOS=0
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)

if [ "${DJANGO_DB_ENGINE:-}" != "postgresql" ]; then
    rojo "DJANGO_DB_ENGINE no es postgresql — ejecute ./scripts/activar-postgresql.sh"
    exit 1
fi

echo "=== PostgreSQL · Configuración .env ==="
verde "DJANGO_DB_ENGINE=postgresql"
verde "Inventario → ${DJANGO_DB_NAME:-suiin_inventario} @ ${DJANGO_DB_HOST:-postgres}"
verde "Riesgos   → ${RIESGOS_DB_NAME:-suiin_riesgos} @ ${DJANGO_DB_HOST:-postgres}"
verde "RBAC      → ${RBAC_DB_NAME:-suiin_rbac} @ ${DJANGO_DB_HOST:-postgres} (Django en Inventario)"

echo ""
echo "=== PostgreSQL · Contenedor ==="
if "${COMPOSE[@]}" ps postgres 2>/dev/null | grep -qE 'Up|running'; then
    verde "Servicio postgres en ejecución"
else
    rojo "postgres no está Up"
    FALLOS=$((FALLOS + 1))
fi

echo ""
echo "=== PostgreSQL · Conexión Django ==="
if "${COMPOSE[@]}" exec -T inventario python manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('inventario OK')" 2>/dev/null | grep -q inventario; then
    verde "Inventario conectado a PostgreSQL"
else
    rojo "Inventario no conecta a PostgreSQL"
    FALLOS=$((FALLOS + 1))
fi

if "${COMPOSE[@]}" exec -T riesgos-backend python manage.py shell -c \
    "from django.db import connection; connection.ensure_connection(); print('riesgos OK')" 2>/dev/null | grep -q riesgos; then
    verde "Riesgos conectado a PostgreSQL"
else
    rojo "Riesgos no conecta a PostgreSQL"
    FALLOS=$((FALLOS + 1))
fi

if "${COMPOSE[@]}" exec -T inventario python manage.py shell -c \
    "from django.db import connections; c=connections['rbac']; c.ensure_connection(); print('rbac OK')" 2>/dev/null | grep -q rbac; then
    verde "RBAC Django conectado a PostgreSQL (alias rbac)"
    ROLES=$("${COMPOSE[@]}" exec -T inventario python manage.py shell -c \
        "from django.db import connections; cur=connections['rbac'].cursor(); cur.execute('SELECT COUNT(*) FROM rol'); print(cur.fetchone()[0])" 2>/dev/null | tail -1 || echo 0)
    if [ "${ROLES:-0}" -gt 0 ] 2>/dev/null; then
        verde "RBAC suiin_rbac: ${ROLES} roles"
    else
        amarillo "RBAC suiin_rbac vacío — ejecute ./scripts/migrar-rbac-postgresql.sh"
    fi
else
    rojo "Inventario no conecta al alias rbac en PostgreSQL"
    FALLOS=$((FALLOS + 1))
fi

echo ""
if [ "$FALLOS" -eq 0 ]; then
    verde "Verificación PostgreSQL: OK"
    exit 0
fi
rojo "Verificación PostgreSQL: $FALLOS fallo(s)"
exit 1

#!/bin/bash
# Recuperación rápida: usuarios demo y desbloqueo axes (sin re-migrar).
# Para migración + despliegue completo use: ./postgresql.sh
#
# Uso: ./scripts/asegurar-usuarios-postgresql.sh [--reset-passwords]

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
    rojo "DJANGO_DB_ENGINE no es postgresql — use ./postgresql.sh para migrar."
    exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.postgres.yml)
RESET=()
if [ "${1:-}" = "--reset-passwords" ]; then
    RESET=(--reset-passwords)
fi

echo "=== Usuarios demo en PostgreSQL ==="
"${COMPOSE[@]}" exec -T inventario python manage.py crear_roles "${RESET[@]}"
"${COMPOSE[@]}" exec -T inventario python manage.py desbloquear_login admin || true

"${COMPOSE[@]}" exec -T inventario python manage.py shell -c "
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
u = User.objects.filter(username='admin').first()
print('admin existe:', bool(u))
if u:
    ok = authenticate(username='admin', password='SUIIN2026#') is not None
    print('admin + SUIIN2026# autentica:', ok)
"

verde "Listo. Pruebe login: admin / SUIIN2026#"

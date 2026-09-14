#!/bin/bash
# Sincronización periódica Inventario → Riesgos (todos los espacios).
# Carga JWT_SHARED_SECRET desde .env — usar en cron vía instalar-cron.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f docker-compose.yml ]; then
    echo "Ejecute desde plataforma/ (falta docker-compose.yml)" >&2
    exit 1
fi
set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a
if [ -z "${JWT_SHARED_SECRET:-}" ] || [[ "${JWT_SHARED_SECRET}" == defina-* ]]; then
    echo "ERROR: JWT_SHARED_SECRET no configurado en .env" >&2
    exit 1
fi
exec docker compose exec -T \
    -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
    riesgos-backend python manage.py sincronizar_activos_inventario --todos-espacios

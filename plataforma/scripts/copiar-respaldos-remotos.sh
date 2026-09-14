#!/bin/bash
# Copia respaldos locales a un destino remoto (rsync). Opcional — prioridad 2.
#
# Configure en .env:
#   SUIIN_RESPALDO_RSYNC_DEST=usuario@servidor:/ruta/respaldos/suiin/
#
# Uso manual o cron semanal:
#   ./scripts/copiar-respaldos-remotos.sh

set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

DEST="${SUIIN_RESPALDO_RSYNC_DEST:-}"
if [ -z "$DEST" ]; then
    echo "SUIIN_RESPALDO_RSYNC_DEST no está definido en .env — omitiendo copia remota." >&2
    exit 0
fi

if ! command -v rsync >/dev/null 2>&1; then
    echo "ERROR: rsync no está instalado." >&2
    exit 1
fi

mkdir -p respaldos
ultimo=$(ls -t respaldos/suiin_plataforma_*.tar.gz 2>/dev/null | head -1 || true)
if [ -z "$ultimo" ]; then
    echo "ERROR: no hay respaldos en respaldos/" >&2
    exit 1
fi

rsync -av --progress respaldos/suiin_plataforma_*.tar.gz "$DEST"
echo "Copiados respaldos a $DEST (último: $(basename "$ultimo"))"

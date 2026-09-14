#!/bin/bash
# Genera /etc/cron.d/suiin-sgsi a partir de la plantilla con la ruta real del proyecto.
#
# Uso (como root o con sudo):
#   sudo ./scripts/instalar-cron.sh
#   sudo ./scripts/instalar-cron.sh --destino /etc/cron.d/suiin-sgsi

set -euo pipefail

DESTINO="/etc/cron.d/suiin-sgsi"
if [ "${1:-}" = "--destino" ]; then
    DESTINO="${2:?Indique ruta destino}"
    shift 2
fi

cd "$(dirname "$0")/.."
RUTA="$(pwd)"

if [ ! -f cron/suiin-sgsi.cron.example ]; then
    echo "Falta cron/suiin-sgsi.cron.example" >&2
    exit 1
fi

chmod +x scripts/cron-respaldar.sh scripts/cron-sync-activos.sh sincronizar_catalogos_mitre.sh 2>/dev/null || true

sed "s|/ruta/suiin-plataforma|${RUTA}|g" cron/suiin-sgsi.cron.example > "/tmp/suiin-sgsi.cron.$$"
echo "SHELL=/bin/bash" > "$DESTINO"
echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" >> "$DESTINO"
echo "" >> "$DESTINO"
cat "/tmp/suiin-sgsi.cron.$$" >> "$DESTINO"
rm -f "/tmp/suiin-sgsi.cron.$$"
chmod 644 "$DESTINO"

echo "Cron instalado en $DESTINO (ruta del proyecto: $RUTA)"
echo "Revise: cat $DESTINO"

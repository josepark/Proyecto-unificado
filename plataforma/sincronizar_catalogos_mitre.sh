#!/bin/bash
# Sincroniza el catálogo MITRE ATT&CK desde el Inventario hacia Riesgos y RBAC.
# Fuente canónica: AmenazaMITRE en Inventario (/api/amenazas/).
#
# Uso (desde la raíz de plataforma/, con docker compose arriba):
#   ./sincronizar_catalogos_mitre.sh
#
# Variables opcionales:
#   INVENTARIO_URL   — base del Inventario (default http://inventario:8000 dentro de compose)

set -euo pipefail

if [ ! -f docker-compose.yml ]; then
    echo "Ejecute este script desde la raíz de plataforma/ (donde está docker-compose.yml)." >&2
    exit 1
fi

paso() { echo ""; echo "=== $1 ==="; }

paso "1/3 · Riesgos — espejo local TecnicaMitre"
docker compose exec -T riesgos-backend python manage.py sincronizar_tecnicas_mitre

paso "2/3 · RBAC — regenerar static/attack_tecnicas.json desde Inventario"
docker compose exec -T -e INVENTARIO_URL="${INVENTARIO_URL:-http://inventario:8000}" rbac \
    python3 catalogo_attack_desde_inventario.py

paso "3/3 · RBAC — recargar catálogo en rbac.db"
docker compose exec -T rbac python3 migrar_v2_1.py

paso "Listo"
echo "Catálogo MITRE propagado: Inventario → Riesgos + RBAC."

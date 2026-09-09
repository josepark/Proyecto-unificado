#!/bin/bash
# Sincroniza el catálogo MITRE ATT&CK desde el Inventario hacia Riesgos y RBAC.
# Fuente canónica: AmenazaMITRE en Inventario (/api/amenazas/).
#
# Uso (desde la raíz de plataforma/, con docker compose arriba):
#   ./sincronizar_catalogos_mitre.sh
#   ./sincronizar_catalogos_mitre.sh --reconstruir   # rebuild imágenes antes de sync
#
# Requisitos:
#   - JWT_SHARED_SECRET definido en .env (mismo valor en los tres servicios)
#   - Código con RolPermisoOServicioInterno (fix post-Ola 1) y requests en rbac/
#   - Catálogo ya importado: docker compose exec inventario python manage.py importar_mitre ...

set -euo pipefail

RECONSTRUIR=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reconstruir|--build) RECONSTRUIR=true; shift ;;
        -h|--help)
            sed -n '2,14p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Opción desconocida: $1 (use --help)" >&2; exit 1 ;;
    esac
done

if [ ! -f docker-compose.yml ]; then
    echo "Ejecute este script desde la raíz de plataforma/ (donde está docker-compose.yml)." >&2
    exit 1
fi

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

if [ -z "${JWT_SHARED_SECRET:-}" ]; then
    echo "ERROR: JWT_SHARED_SECRET no está definido en .env." >&2
    echo "Ejecute: python3 generar_secretos.py" >&2
    echo "Luego reinicie: docker compose up -d --build" >&2
    exit 1
fi

if [[ "${JWT_SHARED_SECRET}" == defina-* ]]; then
    echo "ERROR: JWT_SHARED_SECRET sigue siendo el placeholder de .env.example." >&2
    echo "Ejecute: python3 generar_secretos.py" >&2
    exit 1
fi

paso() { echo ""; echo "=== $1 ==="; }

if $RECONSTRUIR; then
    paso "0/3 · Reconstruyendo inventario, riesgos-backend y rbac"
    docker compose build inventario riesgos-backend rbac
    docker compose up -d
fi

paso "Verificando dependencias en contenedor rbac"
if ! docker compose exec -T rbac python3 -c "import requests" 2>/dev/null; then
    echo "ERROR: el contenedor rbac no tiene el paquete 'requests'." >&2
    echo "Su imagen es antigua — reconstruya y reintente:" >&2
    echo "  ./sincronizar_catalogos_mitre.sh --reconstruir" >&2
    echo "  # o: docker compose build rbac && docker compose up -d rbac" >&2
    exit 1
fi

paso "Verificando acceso interno a /api/amenazas/"
if ! docker compose exec -T \
    -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
    riesgos-backend python3 -c "
import os, urllib.request
secret = os.environ['JWT_SHARED_SECRET']
req = urllib.request.Request(
    'http://inventario:8000/api/amenazas/?page_size=1',
    headers={'X-Plataforma-Secret': secret},
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        assert r.status == 200, r.status
except Exception as e:
    raise SystemExit(
        'No se pudo leer /api/amenazas/ con X-Plataforma-Secret: ' + str(e) + '\n'
        '¿Tiene el código actualizado (RolPermisoOServicioInterno)? '
        'Reconstruya inventario: docker compose build inventario && docker compose up -d inventario'
    )
"; then
    exit 1
fi

paso "1/3 · Riesgos — espejo local TecnicaMitre"
docker compose exec -T \
    -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
    riesgos-backend python manage.py sincronizar_tecnicas_mitre

paso "2/3 · RBAC — regenerar static/attack_tecnicas.json desde Inventario"
docker compose exec -T \
    -e INVENTARIO_URL="${INVENTARIO_URL:-http://inventario:8000}" \
    -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
    rbac python3 catalogo_attack_desde_inventario.py

paso "3/3 · RBAC — recargar catálogo en rbac.db"
docker compose exec -T rbac python3 migrar_v2_1.py

paso "Listo"
echo "Catálogo MITRE propagado: Inventario → Riesgos + RBAC."

#!/bin/bash
# Plataforma SUIIN-SGSI — Despliegue automatizado
#
# Encadena la secuencia completa que se arma a mano en README-DESPLIEGUE.md:
# generar secretos que falten, detener lo que esté corriendo, reconstruir,
# esperar a que los servicios con healthcheck queden sanos, y opcionalmente
# desbloquear una cuenta y/o sincronizar el catálogo de activos.
#
# Uso:
#   ./desplegar.sh                        # despliegue normal (sin purgar imágenes)
#   ./desplegar.sh --purgar               # además purga imágenes antes de reconstruir
#                                          #   (recomendado tras actualizar el código —
#                                          #   garantiza que no quede nada en caché de un
#                                          #   build anterior; NO borra sus bases de datos,
#                                          #   son archivos del host, no volúmenes)
#   ./desplegar.sh --desbloquear admin    # además desbloquea esa cuenta al final
#   ./desplegar.sh --no-sincronizar          # omite la sincronización de activos al final
#   ./desplegar.sh --no-sincronizar-mitre    # omite la propagación MITRE Inventario→Riesgos/RBAC
#   ./desplegar.sh --purgar --desbloquear admin   # todo junto (sync activos va por defecto)
#
# Requiere: docker, el plugin "docker compose" (v2.17+, para --wait), y correrse
# desde la raíz de la plataforma (donde está este script y docker-compose.yml).

set -euo pipefail

PURGAR=false
DESBLOQUEAR_USUARIO=""
SINCRONIZAR=true
SINCRONIZAR_MITRE=true

mostrar_ayuda() {
    sed -n '2,21p' "$0" | sed 's/^# \?//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purgar) PURGAR=true; shift ;;
        --desbloquear)
            if [[ $# -lt 2 ]]; then echo "--desbloquear necesita un usuario" >&2; exit 1; fi
            DESBLOQUEAR_USUARIO="$2"; shift 2 ;;
        --sincronizar) SINCRONIZAR=true; shift ;;
        --no-sincronizar) SINCRONIZAR=false; shift ;;
        --no-sincronizar-mitre) SINCRONIZAR_MITRE=false; shift ;;
        -h|--help) mostrar_ayuda; exit 0 ;;
        *) echo "Argumento desconocido: $1 (use --help)" >&2; exit 1 ;;
    esac
done

paso() { echo ""; echo "=== $1 ==="; }

paso "1/8 · Verificando requisitos"
if ! command -v docker >/dev/null 2>&1; then
    echo "docker no está instalado o no está en el PATH." >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "El plugin 'docker compose' (v2) no está disponible — ¿tiene una versión reciente de Docker?" >&2
    exit 1
fi
if [ ! -f docker-compose.yml ]; then
    echo "No se encontró docker-compose.yml en este directorio — corra este script desde la raíz de la plataforma." >&2
    exit 1
fi

paso "2/8 · Verificando .env"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "No hay .env — copiando desde .env.example..."
        cp .env.example .env
    else
        echo ".env.example tampoco existe en este directorio." >&2
        exit 1
    fi
fi

paso "3/8 · Generando secretos que falten"
python3 generar_secretos.py

if $PURGAR; then
    paso "4/8 · Deteniendo y purgando contenedores + imágenes anteriores"
    docker compose down --rmi all
else
    paso "4/8 · Deteniendo contenedores actuales (sin purgar imágenes — use --purgar si acaba de actualizar el código)"
    docker compose down
fi

paso "5/8 · Reconstruyendo y esperando a que todo quede sano"
if docker compose up -d --build --wait --wait-timeout 180; then
    echo "Todos los servicios con healthcheck quedaron 'healthy'."
else
    echo "⚠ Algún servicio no quedó sano dentro del tiempo de espera." >&2
    echo "" >&2
    echo "--- docker compose ps ---" >&2
    docker compose ps >&2 || true
    echo "" >&2
    echo "--- Últimas 40 líneas de log de cada servicio no saludable ---" >&2
    for servicio in $(docker compose ps --format '{{.Service}}' --filter "health=unhealthy" 2>/dev/null || true); do
        echo "" >&2
        echo ">> $servicio:" >&2
        docker compose logs --tail=40 "$servicio" >&2 || true
    done
    echo "" >&2
    echo "(si no se listó ningún servicio arriba, corra manualmente: docker compose logs -f <servicio>)" >&2
    exit 1
fi

if [ -n "$DESBLOQUEAR_USUARIO" ]; then
    paso "6/8 · Desbloqueando la cuenta '$DESBLOQUEAR_USUARIO'"
    docker compose exec -T inventario python manage.py desbloquear_login "$DESBLOQUEAR_USUARIO" || true
    docker compose exec -T riesgos-backend python manage.py desbloquear_login "$DESBLOQUEAR_USUARIO" || true
else
    paso "6/8 · (sin --desbloquear, se omite)"
fi

if $SINCRONIZAR; then
    paso "7/8 · Sincronizando catálogo de activos desde el Inventario"
    docker compose exec -T riesgos-backend python manage.py sincronizar_activos_inventario
else
    paso "7/8 · (sin sincronización de activos — omita --no-sincronizar para habilitarla)"
fi

if $SINCRONIZAR_MITRE; then
    paso "8/8 · Propagando catálogo MITRE (Inventario → Riesgos + RBAC)"
    INVENTARIO_URL="${INVENTARIO_URL:-http://inventario:8000}" ./sincronizar_catalogos_mitre.sh
else
    paso "8/8 · (sin sincronización MITRE — omita --no-sincronizar-mitre para habilitarla)"
fi

paso "Listo"
cat << 'EOF'
Plataforma arriba, en el host/dominio configurado en DJANGO_ALLOWED_HOSTS:
  - Inicio de sesión (Inventario):  http://<host>/login/
  - Gestión de Riesgos:             http://<host>/riesgos/  (sesión única con lo de arriba)
  - Matriz RBAC:                    pestaña dentro del Inventario

Si algo no arranca, revise primero:
  docker compose ps
  docker compose logs -f <servicio>
EOF

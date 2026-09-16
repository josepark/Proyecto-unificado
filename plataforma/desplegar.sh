#!/bin/bash
# Plataforma SUIIN-SGSI — Despliegue automatizado (único punto de entrada)
#
# Hace TODO en un solo comando: secretos, rebuild, healthchecks, desbloqueo
# opcional, sync activos, import MITRE (si falta), propagación MITRE a
# Riesgos/RBAC y verificación del login.
#
# Uso:
#   ./desplegar.sh                        # despliegue completo
#   ./desplegar.sh --purgar               # rebuild limpio (recomendado tras git pull)
#   ./desplegar.sh --desbloquear admin    # además desbloquea cuenta tras axes
#   ./desplegar.sh --no-sincronizar       # omite sync de activos
#   ./desplegar.sh --postgres              # usa docker-compose.postgres.yml
#   ./desplegar.sh --migrate-fake-initial  # tras pgloader (lo usa postgresql.sh)
#   ./desplegar.sh --reset-passwords       # restablece contraseñas demo
#
# Migración PostgreSQL completa (un solo comando):
#   ./postgresql.sh
#
# Catálogo MITRE: coloque enterprise-attack-v19_1.xlsx en inventario/data/
# (ver inventario/data/README.md). Si falta y el catálogo está vacío, avisa al final.
#
# Requiere: compose v2.17+ (--wait) desde la raíz de plataforma/.

set -euo pipefail

PURGAR=false
DESBLOQUEAR_USUARIO=""
SINCRONIZAR=true
SINCRONIZAR_MITRE=true
USAR_POSTGRES=false
MIGRATE_FAKE_INITIAL=false
RESET_PASSWORDS=false

mostrar_ayuda() {
    sed -n '2,20p' "$0" | sed 's/^# \?//'
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
        --postgres) USAR_POSTGRES=true; shift ;;
        --migrate-fake-initial) MIGRATE_FAKE_INITIAL=true; shift ;;
        --reset-passwords) RESET_PASSWORDS=true; shift ;;
        -h|--help) mostrar_ayuda; exit 0 ;;
        *) echo "Argumento desconocido: $1 (use --help)" >&2; exit 1 ;;
    esac
done

paso() { echo ""; echo "=== $1 ==="; }

cargar_env() {
    if [ -f .env ]; then
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    fi
}

compose() {
    if $USAR_POSTGRES || [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
        docker compose -f docker-compose.yml -f docker-compose.postgres.yml "$@"
    else
        docker compose "$@"
    fi
}

paso "1/10 · Verificando requisitos"
if ! command -v docker >/dev/null 2>&1; then
    echo "docker no está instalado o no está en el PATH." >&2
    exit 1
fi
if ! compose version >/dev/null 2>&1; then
    echo "El plugin 'docker compose' (v2) no está disponible." >&2
    exit 1
fi
if [ ! -f docker-compose.yml ]; then
    echo "Corra este script desde la raíz de plataforma/." >&2
    exit 1
fi

paso "2/10 · Verificando .env"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "No hay .env — copiando desde .env.example..."
        cp .env.example .env
    else
        echo ".env.example tampoco existe." >&2
        exit 1
    fi
fi

paso "3/10 · Generando secretos que falten"
python3 generar_secretos.py
python3 validar_secretos.py || exit 1
cargar_env

if $USAR_POSTGRES && [ "${DJANGO_DB_ENGINE:-}" != "postgresql" ]; then
    echo "Activando PostgreSQL en .env (--postgres)..."
    ./scripts/activar-postgresql.sh
    cargar_env
fi

if $PURGAR; then
    paso "4/10 · Deteniendo y purgando contenedores + imágenes"
    compose down --remove-orphans --rmi all
else
    paso "4/10 · Deteniendo contenedores (use --purgar tras actualizar código)"
    compose down --remove-orphans
fi

paso "5/10 · Reconstruyendo y esperando servicios sanos"
if $USAR_POSTGRES || [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
    echo "PostgreSQL: levantando postgres y verificando suiin_riesgos / suiin_rbac…"
    compose up -d postgres --wait --wait-timeout 120
    chmod +x scripts/asegurar-bases-postgresql.sh 2>/dev/null || true
    ./scripts/asegurar-bases-postgresql.sh
fi
if compose up -d --build --wait --wait-timeout 180; then
    echo "Todos los servicios con healthcheck quedaron 'healthy'."
else
    echo "⚠ Algún servicio no quedó sano." >&2
    compose ps >&2 || true
    for servicio in $(compose ps --format '{{.Service}}' --filter "health=unhealthy" 2>/dev/null || true); do
        echo "" >&2
        echo ">> $servicio:" >&2
        compose logs --tail=40 "$servicio" >&2 || true
    done
    exit 1
fi

paso "5b/10 · Migraciones de base de datos"
MIGRATE_FLAGS=(--noinput)
if $MIGRATE_FAKE_INITIAL; then
    MIGRATE_FLAGS=(--fake-initial --noinput)
fi
if $USAR_POSTGRES || [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
    compose exec -T inventario python manage.py asegurar_bases_postgresql 2>/dev/null || true
fi
compose exec -T inventario python manage.py migrate "${MIGRATE_FLAGS[@]}"
compose exec -T inventario python manage.py migrate rbac --database=rbac "${MIGRATE_FLAGS[@]}"
compose exec -T inventario python manage.py inicializar_rbac
compose exec -T riesgos-backend python manage.py migrate "${MIGRATE_FLAGS[@]}"
if $USAR_POSTGRES || [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
    echo "PostgreSQL: verificando usuarios demo (admin/consultor/dinamizador)…"
    CREAR_ROLES_ARGS=()
    if $RESET_PASSWORDS; then
        CREAR_ROLES_ARGS=(--reset-passwords)
    fi
    compose exec -T inventario python manage.py crear_roles "${CREAR_ROLES_ARGS[@]}"
fi
echo "Inventario:"
compose exec -T inventario python manage.py showmigrations inventario | tail -8
if ! compose exec -T inventario python manage.py showmigrations inventario 2>/dev/null | grep -E '0014_backfill|0015_alter' | grep -q '\[X\]'; then
    echo "ERROR: faltan migraciones 0014/0015 (modulos_acceso por proyecto)." >&2
    exit 1
fi
echo "Riesgos:"
compose exec -T riesgos-backend python manage.py showmigrations riesgos | tail -5

importar_mitre_si_falta() {
    local count
    count=$(compose exec -T inventario python manage.py shell -c \
        "from inventario.models import AmenazaMITRE; print(AmenazaMITRE.objects.count())" \
        2>/dev/null | grep -Eo '[0-9]+$' | tail -1 || true)
    count=${count:-0}
    if [ "$count" -ge 100 ] 2>/dev/null; then
        echo "Catálogo MITRE en Inventario: ${count} entradas (OK)."
        return 0
    fi

    local xlsx=""
    for candidato in inventario/data/enterprise-attack*.xlsx inventario/data/*.xlsx; do
        if [ -f "$candidato" ]; then
            xlsx="$candidato"
            break
        fi
    done

    if [ -z "$xlsx" ]; then
        echo "AVISO: catálogo MITRE casi vacío (${count:-0} entradas) y no hay .xlsx en inventario/data/."
        echo "      Descargue enterprise-attack-v19_1.xlsx de attack.mitre.org, colóquelo ahí y vuelva a ejecutar ./desplegar.sh"
        return 0
    fi

    local base
    base=$(basename "$xlsx")
    echo "Importando MITRE desde inventario/data/${base}..."
    compose exec -T inventario python manage.py importar_mitre --file "/app/data/${base}"
}

sync_mitre_plataforma() {
    if [ -z "${JWT_SHARED_SECRET:-}" ]; then
        echo "ERROR: JWT_SHARED_SECRET no definido en .env." >&2
        exit 1
    fi
    if [[ "${JWT_SHARED_SECRET}" == defina-* ]]; then
        echo "ERROR: JWT_SHARED_SECRET sigue siendo placeholder — ejecute python3 generar_secretos.py" >&2
        exit 1
    fi

    echo "→ Verificando endpoint interno MITRE..."
    compose exec -T \
        -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
        riesgos-backend python3 -c "
import os, urllib.request
req = urllib.request.Request(
    'http://inventario:8000/api/interno/catalogo-mitre/?page_size=1',
    headers={'X-Plataforma-Secret': os.environ['JWT_SHARED_SECRET']},
)
with urllib.request.urlopen(req, timeout=15) as r:
    assert r.status == 200
"

    echo "→ Riesgos: espejo TecnicaMitre"
    compose exec -T \
        -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
        riesgos-backend python manage.py sincronizar_tecnicas_mitre

    echo "→ RBAC Django: attack_tecnica desde Inventario"
    compose exec -T \
        -e INVENTARIO_URL="${INVENTARIO_URL:-http://inventario:8000}" \
        -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET}" \
        inventario python manage.py sincronizar_catalogo_attack
}

verificar_login() {
    local codigo
    codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1/api/auth/login/ 2>/dev/null || echo "000")
    case "$codigo" in
        200) echo "Login API responde OK (GET /api/auth/login/ → 200)." ;;
        502|503|504)
            echo "ERROR: login devuelve $codigo — inventario no alcanzable desde nginx." >&2
            echo "       Revise: compose logs inventario --tail 30" >&2
            return 1
            ;;
        *) echo "GET /api/auth/login/ → $codigo (revise nginx/inventario si no puede entrar)." ;;
    esac
}

verificar_sesion_anonima() {
    local cuerpo codigo
    codigo=$(curl -s -o /tmp/suiin-sesion-anon.json -w '%{http_code}' --connect-timeout 5 http://127.0.0.1/api/sesion/ 2>/dev/null || echo "000")
    cuerpo=$(cat /tmp/suiin-sesion-anon.json 2>/dev/null || true)
    if [ "$codigo" = "200" ] && echo "$cuerpo" | grep -qE '"autenticado"[[:space:]]*:[[:space:]]*false'; then
        echo "GET /api/sesion/ → anónimo OK (autenticado: false, modulos: [])."
        return 0
    fi
    echo "ERROR: GET /api/sesion/ → $codigo (esperado autenticado:false)." >&2
    return 1
}

verificar_rbac_resumen() {
    if compose exec -T inventario python manage.py shell -c "
from django.db import connections
c = connections['rbac']
c.ensure_connection()
cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM rol')
roles = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM sistema')
sistemas = cur.fetchone()[0]
print(f'RBAC Django: {roles} roles, {sistemas} sistemas')
" 2>/dev/null; then
        :
    else
        echo "ERROR: base RBAC Django inaccesible (alias rbac)." >&2
        echo "       Ejecute: compose exec inventario python manage.py migrate rbac --database=rbac" >&2
        return 1
    fi
    local roles
    roles=$(compose exec -T inventario python manage.py shell -c \
        "from rbac.models import Rol; print(Rol.objects.using('rbac').count())" 2>/dev/null | tail -1 || echo 0)
    if [ "${roles:-0}" -eq 0 ] 2>/dev/null; then
        echo "ERROR: base RBAC vacía (0 roles)." >&2
        echo "       Ejecute: compose exec inventario python manage.py inicializar_rbac" >&2
        echo "       o: ./scripts/migrar-rbac-postgresql.sh --forzar" >&2
        return 1
    fi
    local codigo
    codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1/rbac/api/resumen 2>/dev/null || echo "000")
    case "$codigo" in
        200|401) echo "GET /rbac/api/resumen → $codigo (401 sin sesión es esperado)." ;;
        500)
            echo "ERROR: GET /rbac/api/resumen → 500 (revise logs de inventario)." >&2
            return 1
            ;;
        502|503|504)
            echo "ERROR: GET /rbac/api/resumen → $codigo (nginx/inventario caído)." >&2
            return 1
            ;;
        *) echo "GET /rbac/api/resumen → $codigo (revise si no puede usar RBAC)." ;;
    esac
}

if $SINCRONIZAR_MITRE; then
    paso "6/10 · Importar catálogo MITRE en Inventario (si falta)"
    importar_mitre_si_falta

    paso "7/10 · Propagar MITRE Inventario → Riesgos + RBAC"
    sync_mitre_plataforma
else
    paso "6/10 · (MITRE omitido — omita --no-sincronizar-mitre para habilitarlo)"
    paso "7/10 · (omitido)"
fi

if [ -n "$DESBLOQUEAR_USUARIO" ]; then
    paso "8/10 · Desbloqueando cuenta '$DESBLOQUEAR_USUARIO'"
    compose exec -T inventario python manage.py desbloquear_login "$DESBLOQUEAR_USUARIO" || true
    compose exec -T riesgos-backend python manage.py desbloquear_login "$DESBLOQUEAR_USUARIO" || true
else
    paso "8/10 · (sin --desbloquear — omita si axes bloqueó su usuario)"
fi

if $SINCRONIZAR; then
    paso "9/10 · Sincronizando activos Inventario → Riesgos (todos los espacios)"
    compose exec -T \
        -e JWT_SHARED_SECRET="${JWT_SHARED_SECRET:-}" \
        riesgos-backend python manage.py sincronizar_activos_inventario --todos-espacios
else
    paso "9/10 · (sync activos omitido)"
fi

paso "10/10 · Verificación final"
verificar_rbac_resumen || exit 1
verificar_login || exit 1
verificar_sesion_anonima || exit 1

paso "Listo"
cat << 'EOF'
Plataforma desplegada. Acceda en el host de DJANGO_ALLOWED_HOSTS:
  http://<host>/login/          — inicio de sesión unificado
  http://<host>/inventario/     — inventario de activos
  http://<host>/gestion-riesgos/ — riesgos
  http://<host>/rbac/           — matriz RBAC

Un solo comando para todo (recomendado tras actualizar código):
  ./desplegar.sh --purgar --desbloquear admin

PostgreSQL — migración + despliegue en un solo paso:
  ./postgresql.sh

Despliegues posteriores con PostgreSQL ya activo:
  ./desplegar.sh --postgres --purgar --desbloquear admin

Si algo falla: ./diagnostico_login.sh
EOF

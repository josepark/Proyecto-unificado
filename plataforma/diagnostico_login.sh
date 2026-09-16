#!/bin/bash
# Diagnóstico rápido cuando /login muestra 502 en /api/auth/login/
# Uso: ./diagnostico_login.sh   (desde la raíz de plataforma/)

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/ (donde está docker-compose.yml)."
    exit 1
fi

if [ -f .env ]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi

compose_cmd() {
    if [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
        docker compose -f docker-compose.yml -f docker-compose.postgres.yml "$@"
    else
        docker compose "$@"
    fi
}

echo "=== 1/7 · Contenedores ==="
compose_cmd ps -a || { rojo "docker compose no disponible"; exit 1; }

echo ""
echo "=== 2/7 · Secretos en .env (placeholders impiden arrancar con DEBUG=False) ==="
if [ -f .env ]; then
    problemas=0
    for var in DJANGO_SECRET_KEY JWT_SHARED_SECRET RIESGOS_SECRET_KEY SUIIN_RBAC_SECRET; do
        val=$(grep -E "^${var}=" .env 2>/dev/null | head -1 | cut -d= -f2- || true)
        if [ -z "$val" ]; then
            amarillo "? $var no definida"
            problemas=1
        elif [[ "$val" == defina-* ]] || [[ "$val" == django-insecure-* ]]; then
            rojo "✗ $var sigue siendo placeholder: ${val:0:40}..."
            problemas=1
        else
            verde "✓ $var tiene valor propio"
        fi
    done
    if [ "$problemas" -eq 1 ]; then
        echo ""
        amarillo "Corrija con: python3 generar_secretos.py && docker compose up -d --build"
    fi
else
    rojo "No existe .env — copie .env.example a .env y ejecute python3 generar_secretos.py"
fi

echo ""
echo "=== 3/7 · Gateway nginx (localhost) ==="
if codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1/healthz 2>/dev/null); then
    if [ "$codigo" = "200" ]; then
        verde "GET /healthz → $codigo"
    else
        amarillo "GET /healthz → $codigo (esperado 200)"
    fi
else
    rojo "No responde http://127.0.0.1/healthz — ¿nginx levantado? (docker compose up -d nginx)"
fi

if codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1/api/auth/login/ 2>/dev/null); then
    case "$codigo" in
        200) verde "GET /api/auth/login/ vía nginx → $codigo (login debería funcionar)" ;;
        401|403|429) amarillo "GET /api/auth/login/ → $codigo (inventario responde; revise credenciales o bloqueo axes)" ;;
        502|503|504) rojo "GET /api/auth/login/ → $codigo (nginx NO alcanza inventario — siga al paso 4)" ;;
        *) amarillo "GET /api/auth/login/ → $codigo" ;;
    esac
else
    rojo "GET /api/auth/login/ sin respuesta"
fi

echo ""
echo "=== 3b/7 · Sesión anónima (proyectos / SPA) ==="
if cuerpo=$(curl -s --connect-timeout 3 http://127.0.0.1/api/sesion/ 2>/dev/null); then
    if echo "$cuerpo" | grep -qE '"autenticado"[[:space:]]*:[[:space:]]*false'; then
        verde "GET /api/sesion/ → autenticado: false (OK para logout / login)"
    else
        amarillo "GET /api/sesion/ no reporta autenticado:false — revise cookies o inventario"
    fi
else
    rojo "GET /api/sesion/ sin respuesta"
fi

echo ""
echo "=== 4/7 · Inventario directo (red docker, sin pasar por el navegador) ==="
if compose_cmd ps inventario 2>/dev/null | grep -qE 'Up|running'; then
    if compose_cmd exec -T nginx curl -sf --connect-timeout 5 http://inventario:8000/api/sesion/ >/dev/null 2>&1; then
        verde "inventario:8000/api/sesion/ responde OK"
    else
        rojo "inventario está 'Up' pero NO responde en :8000 — revise logs abajo"
    fi
    codigo=$(compose_cmd exec -T nginx curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
        http://inventario:8000/api/auth/login/ 2>/dev/null || echo "000")
    case "$codigo" in
        200) verde "inventario:8000/api/auth/login/ → $codigo" ;;
        502|000) rojo "inventario:8000/api/auth/login/ → $codigo (gunicorn caído o migrando)" ;;
        *) amarillo "inventario:8000/api/auth/login/ → $codigo" ;;
    esac
else
    rojo "Contenedor inventario NO está en ejecución — causa típica del 502 en login"
    echo ""
    echo "Últimas líneas del log de inventario:"
    compose_cmd logs inventario --tail 25 2>/dev/null || true
fi

echo ""
echo "=== 5/7 · RBAC (integridad /api/resumen) ==="
if compose_cmd ps rbac 2>/dev/null | grep -qE 'Up|running'; then
    if compose_cmd exec -T rbac python3 -c "from recuperar_rbac_db import integridad_ok; import sys; sys.exit(0 if integridad_ok('rbac.db') else 2)" 2>/dev/null; then
        verde "rbac.db: tablas, espacio_codigo y vistas OK"
    else
        rojo "rbac.db incompleta — /rbac/api/resumen puede devolver 500"
        amarillo "  docker compose exec rbac python3 recuperar_rbac_db.py"
        amarillo "  docker compose exec rbac python3 migrar_espacio_datos.py"
    fi
else
    amarillo "Contenedor rbac no está en ejecución — omitiendo chequeo de integridad"
fi

echo ""
echo "=== 6/7 · Migraciones modulos_acceso (Inventario) ==="
if compose_cmd ps inventario 2>/dev/null | grep -qE 'Up|running'; then
    if compose_cmd exec -T inventario python manage.py showmigrations inventario 2>/dev/null \
        | grep -E '0014_backfill|0015_alter' | grep -q '\[X\]'; then
        verde "Migraciones 0014/0015 aplicadas (proyectos por usuario)"
    else
        rojo "Faltan migraciones 0014/0015 — modulos_acceso puede estar mal"
        amarillo "  compose exec inventario python manage.py migrate inventario"
    fi
else
    amarillo "Inventario no está Up — omitiendo chequeo de migraciones"
fi

if [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ] && compose_cmd ps inventario 2>/dev/null | grep -qE 'Up|running'; then
    echo ""
    echo "=== 6b/7 · Usuario admin en PostgreSQL ==="
    if compose_cmd exec -T inventario python manage.py shell -c \
        "from django.contrib.auth.models import User; print(User.objects.filter(username='admin').exists())" 2>/dev/null \
        | grep -q True; then
        verde "Usuario 'admin' existe en PostgreSQL"
    else
        rojo "Usuario 'admin' NO existe — causa típica del 401 tras migrar PostgreSQL"
        amarillo "  ./scripts/asegurar-usuarios-postgresql.sh"
    fi
fi

echo ""
echo "=== 7/7 · Acciones recomendadas ==="
cat <<'EOF'
Si inventario está caído o el paso 3 devolvió 502:

  python3 generar_secretos.py          # solo si hay placeholders en .env
  docker compose up -d --build inventario
  docker compose logs inventario --tail 30
  docker compose up -d nginx

Recuperación completa (recomendada tras actualizar código):

  ./desplegar.sh --purgar --desbloquear admin

Verificación prioridad 1 (sesión + proyectos + RBAC):

  ./scripts/verificar-prioridad-1.sh

Verificación prioridad 2 (secretos, respaldos, cron, TLS):

  ./scripts/verificar-prioridad-2.sh
  sudo ./scripts/instalar-cron.sh

Verificación prioridad 3 (PostgreSQL, MFA TOTP, refresh JWT):

  ./scripts/verificar-prioridad-3.sh

Si el backend responde 401 (no 502) pero no acepta la clave:

  ./postgresql.sh                         # migración + despliegue completo
  ./scripts/asegurar-usuarios-postgresql.sh     # solo login 401 (sin re-migrar)
  docker compose exec inventario python manage.py changepassword admin
  docker compose exec inventario python manage.py desbloquear_login admin
  # Credenciales demo por defecto: admin / SUIIN2026#
EOF

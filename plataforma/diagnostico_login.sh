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

echo "=== 1/5 · Contenedores ==="
docker compose ps -a || { rojo "docker compose no disponible"; exit 1; }

echo ""
echo "=== 2/5 · Secretos en .env (placeholders impiden arrancar con DEBUG=False) ==="
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
echo "=== 3/5 · Gateway nginx (localhost) ==="
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
echo "=== 4/5 · Inventario directo (red docker, sin pasar por el navegador) ==="
if docker compose ps inventario 2>/dev/null | grep -qE 'Up|running'; then
    if docker compose exec -T nginx curl -sf --connect-timeout 5 http://inventario:8000/api/sesion/ >/dev/null 2>&1; then
        verde "inventario:8000/api/sesion/ responde OK"
    else
        rojo "inventario está 'Up' pero NO responde en :8000 — revise logs abajo"
    fi
    codigo=$(docker compose exec -T nginx curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
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
    docker compose logs inventario --tail 25 2>/dev/null || true
fi

echo ""
echo "=== 5/5 · Acciones recomendadas ==="
cat <<'EOF'
Si inventario está caído o el paso 3 devolvió 502:

  python3 generar_secretos.py          # solo si hay placeholders en .env
  docker compose up -d --build inventario
  docker compose logs inventario --tail 30
  docker compose up -d nginx

Recuperación completa (recomendada tras actualizar código):

  ./desplegar.sh --desbloquear admin

Si el backend responde 401 (no 502) pero no acepta la clave:

  docker compose exec inventario python manage.py changepassword admin
  docker compose exec inventario python manage.py desbloquear_login admin
EOF

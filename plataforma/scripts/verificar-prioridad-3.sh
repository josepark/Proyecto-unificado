#!/bin/bash
# Verificación prioridad 3 — PostgreSQL, MFA TOTP y refresh JWT.
# Uso: ./scripts/verificar-prioridad-3.sh   (desde plataforma/)

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

FALLOS=0
avisos=0

echo "=== Prioridad 3 · Refresh JWT ==="
if grep -q 'token-jwt/refresh' inventario/inventario/urls.py 2>/dev/null; then
    verde "Endpoint /api/token-jwt/refresh/ registrado"
else
    rojo "Falta endpoint refresh JWT"
    FALLOS=$((FALLOS + 1))
fi

codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 \
    -X POST http://127.0.0.1/api/token-jwt/refresh/ \
    -H 'Content-Type: application/json' \
    -d '{"refresh_token":"invalido"}' 2>/dev/null || echo "000")
case "$codigo" in
    401) verde "POST /api/token-jwt/refresh/ → 401 con token inválido (esperado)" ;;
    502|503|504|000) amarillo "Refresh endpoint no accesible ($codigo) — ¿contenedores arriba?" ;;
    *) amarillo "POST /api/token-jwt/refresh/ → $codigo" ;;
esac

echo ""
echo "=== Prioridad 3 · MFA TOTP (API) ==="
for ruta in mfa/estado mfa/configurar mfa/activar mfa/desactivar; do
    if grep -q "api/${ruta}/" inventario/inventario/urls.py 2>/dev/null; then
        verde "Ruta /api/${ruta}/ presente"
    else
        rojo "Falta /api/${ruta}/"
        FALLOS=$((FALLOS + 1))
    fi
done

echo ""
echo "=== Prioridad 3 · PostgreSQL (opcional) ==="
if [ -f .env ]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi
if [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
    verde "DJANGO_DB_ENGINE=postgresql en .env"
    if [ -f docker-compose.postgres.yml ]; then
        verde "docker-compose.postgres.yml presente"
    else
        rojo "Falta docker-compose.postgres.yml"
        FALLOS=$((FALLOS + 1))
    fi
    if command -v docker >/dev/null 2>&1; then
        if ./scripts/verificar-postgresql.sh 2>/dev/null; then
            : # verificar-postgresql ya imprime OK
        else
            amarillo "PostgreSQL configurado pero verificación falló — ¿stack arriba? ./desplegar.sh --postgres"
            avisos=$((avisos + 1))
        fi
    else
        amarillo "Docker no disponible — omitiendo verificación de conexión PostgreSQL"
        avisos=$((avisos + 1))
    fi
else
    amarillo "SQLite activo (OK en desarrollo) — use ./scripts/activar-postgresql.sh en producción concurrente"
    avisos=$((avisos + 1))
fi

if python3 -c "import importlib.util; exit(0 if importlib.util.find_spec('psycopg2') else 1)" 2>/dev/null; then
    verde "psycopg2 disponible en el host"
else
    amarillo "psycopg2 no instalado en el host (normal si solo corre en Docker)"
fi

echo ""
echo "=== Prioridad 3 · Checklist manual ==="
cat <<'EOF'
1. Refresh JWT: tras login, comprobar localStorage suiin_refresh_token
2. MFA: entrar → /seguridad-mfa → escanear QR → activar con código TOTP
3. Login con MFA: cerrar sesión → login pide código de 6 dígitos
4. PostgreSQL (staging): ./scripts/activar-postgresql.sh + compose override + migrate
EOF

echo ""
if [ "$FALLOS" -eq 0 ]; then
    verde "Verificación automática prioridad 3: OK ($avisos aviso(s))"
    exit 0
fi

rojo "Verificación automática prioridad 3: $FALLOS chequeo(s) fallido(s)"
exit 1

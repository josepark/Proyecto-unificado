#!/bin/bash
# Verificación prioridad 2 — HTTPS, secretos, respaldos y cron.
# Uso: ./scripts/verificar-prioridad-2.sh   (desde plataforma/)

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

echo "=== Prioridad 2 · Secretos (.env) ==="
if python3 validar_secretos.py; then
    verde "Las 4 claves tienen valores propios"
else
    rojo "Hay placeholders en .env"
    FALLOS=$((FALLOS + 1))
fi

echo ""
echo "=== Prioridad 2 · Respaldo unificado ==="
if [ -d respaldos ] && ls respaldos/suiin_plataforma_*.tar.gz >/dev/null 2>&1; then
    if python3 respaldar_plataforma.py --verificar; then
        verde "Último respaldo verificado"
    else
        rojo "El último respaldo no pasó la verificación"
        FALLOS=$((FALLOS + 1))
    fi
else
    amarillo "No hay respaldos aún — ejecute: python3 respaldar_plataforma.py"
    avisos=$((avisos + 1))
fi

echo ""
echo "=== Prioridad 2 · Scripts cron ==="
for script in scripts/cron-respaldar.sh scripts/cron-sync-activos.sh scripts/instalar-cron.sh; do
    if [ -x "$script" ] || [ -f "$script" ]; then
        verde "Presente: $script"
    else
        rojo "Falta: $script"
        FALLOS=$((FALLOS + 1))
    fi
done

echo ""
echo "=== Prioridad 2 · TLS (opcional) ==="
if [ -f .env ]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi
if [ -f nginx/nginx-tls.active.conf ] && [ -f nginx/tls/fullchain.pem ]; then
    verde "TLS activo (nginx-tls.active.conf + certificados)"
    if [ "${DJANGO_SSL_REDIRECT:-False}" != "True" ]; then
        amarillo "DJANGO_SSL_REDIRECT no es True — cookies Secure pueden no alinearse"
        avisos=$((avisos + 1))
    fi
    codigo=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 5 "https://127.0.0.1/healthz" 2>/dev/null || echo "000")
    case "$codigo" in
        200) verde "GET https://127.0.0.1/healthz → 200" ;;
        000) amarillo "Puerto 443 no responde (¿compose TLS override activo?)" ;;
        *) amarillo "HTTPS responde $codigo" ;;
    esac
else
    amarillo "TLS no activado (HTTP plano — OK en VLAN interna; use ./scripts/activar-tls.sh en producción expuesta)"
    avisos=$((avisos + 1))
fi

echo ""
echo "=== Prioridad 2 · Checklist operativo ==="
cat <<'EOF'
1. Secretos: python3 validar_secretos.py (sin placeholders)
2. Respaldo diario: sudo ./scripts/instalar-cron.sh
3. Prueba de restauración en staging:
     python3 restaurar_plataforma.py --ultimo --confirmar
4. Producción expuesta: ./scripts/activar-tls.sh <dominio> <email>
     docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build nginx
5. Copia remota (opcional): SUIIN_RESPALDO_RSYNC_DEST en .env + cron rsync
EOF

echo ""
if [ "$FALLOS" -eq 0 ]; then
    verde "Verificación automática prioridad 2: OK ($avisos aviso(s) informativo(s))"
    exit 0
fi

rojo "Verificación automática prioridad 2: $FALLOS chequeo(s) fallido(s)"
exit 1

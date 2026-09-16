#!/bin/bash
# Activa TLS en nginx con certificados Let's Encrypt (certbot) o certificados propios.
#
# Uso (desde plataforma/):
#   ./scripts/activar-tls.sh suiin.ejemplo.org admin@ejemplo.org   # certbot webroot
#   ./scripts/activar-tls.sh --solo-config suiin.ejemplo.org       # ya tiene certs en nginx/tls/
#
# Tras activar:
#   docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build nginx inventario riesgos-backend
#
# Ajusta .env: DJANGO_SSL_REDIRECT=True y DJANGO_CSRF_TRUSTED=https://<dominio>

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

SOLO_CONFIG=false
if [ "${1:-}" = "--solo-config" ]; then
    SOLO_CONFIG=true
    shift
fi

DOMINIO="${1:-}"
EMAIL="${2:-}"

if [ -z "$DOMINIO" ]; then
    rojo "Uso: $0 [--solo-config] <dominio> [email-certbot]"
    exit 1
fi

TLS_DIR="nginx/tls"
WEBROOT="nginx/certbot-webroot"
mkdir -p "$TLS_DIR" "$WEBROOT"

actualizar_env() {
    local url="https://${DOMINIO}"
    if [ ! -f .env ]; then
        amarillo "No hay .env — copie .env.example antes de continuar."
        return
    fi
    python3 - "$DOMINIO" "$url" <<'PY'
import re, sys
from pathlib import Path
dominio, url = sys.argv[1], sys.argv[2]
ruta = Path(".env")
lineas = ruta.read_text(encoding="utf-8").splitlines()
cambios = {
    "DJANGO_SSL_REDIRECT": "True",
    "DJANGO_CSRF_TRUSTED": url,
    "SUIIN_TLS_DOMAIN": dominio,
}
for clave, valor in cambios.items():
    patron = re.compile(rf"^{re.escape(clave)}=.*$")
    encontrada = False
    for i, linea in enumerate(lineas):
        if patron.match(linea):
            lineas[i] = f"{clave}={valor}"
            encontrada = True
            break
    if not encontrada:
        lineas.append(f"{clave}={valor}")
    print(f"  .env → {clave}={valor}")
ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
PY
}

renderizar_nginx_tls() {
    sed "s/__SUIIN_TLS_DOMAIN__/${DOMINIO}/g" nginx/nginx-tls.conf.template > nginx/nginx-tls.active.conf
    verde "Generado nginx/nginx-tls.active.conf"
}

obtener_certbot() {
    if [ -f "$TLS_DIR/fullchain.pem" ] && [ -f "$TLS_DIR/privkey.pem" ]; then
        verde "Certificados ya presentes en $TLS_DIR/"
        return 0
    fi
    if [ "$SOLO_CONFIG" = true ]; then
        rojo "Faltan $TLS_DIR/fullchain.pem y/o privkey.pem (use certbot o copie sus certs)."
        exit 1
    fi
    if [ -z "$EMAIL" ]; then
        rojo "Indique email para Let's Encrypt: $0 $DOMINIO admin@ejemplo.org"
        exit 1
    fi
    if ! command -v certbot >/dev/null 2>&1; then
        rojo "certbot no está instalado. Instálelo o use --solo-config con certs en nginx/tls/."
        exit 1
    fi

    amarillo "Asegúrese de que el puerto 80 apunte a este host y nginx esté arriba."
    amarillo "Certbot usará webroot en $WEBROOT (montado temporalmente en nginx)."

    docker compose up -d nginx || true

    certbot certonly --webroot -w "$(pwd)/$WEBROOT" \
        -d "$DOMINIO" --email "$EMAIL" --agree-tos --non-interactive \
        --keep-until-expiring

    LE="/etc/letsencrypt/live/${DOMINIO}"
    if [ ! -f "$LE/fullchain.pem" ]; then
        rojo "certbot no dejó certificados en $LE"
        exit 1
    fi
    cp "$LE/fullchain.pem" "$TLS_DIR/fullchain.pem"
    cp "$LE/privkey.pem" "$TLS_DIR/privkey.pem"
    chmod 644 "$TLS_DIR/fullchain.pem"
    chmod 600 "$TLS_DIR/privkey.pem"
    verde "Certificados copiados a $TLS_DIR/"
}

echo "=== Activar TLS · $DOMINIO ==="
obtener_certbot
renderizar_nginx_tls
actualizar_env

echo ""
verde "TLS configurado. Reinicie nginx con el override TLS:"
echo "  docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build nginx inventario riesgos-backend"
echo ""
echo "Renovación Let's Encrypt (cron del host, ejemplo mensual):"
echo "  0 4 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/${DOMINIO}/fullchain.pem $(pwd)/${TLS_DIR}/fullchain.pem && cp /etc/letsencrypt/live/${DOMINIO}/privkey.pem $(pwd)/${TLS_DIR}/privkey.pem && docker compose -f docker-compose.yml -f docker-compose.tls.yml exec nginx nginx -s reload"

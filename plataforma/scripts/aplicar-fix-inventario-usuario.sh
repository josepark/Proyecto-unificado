#!/usr/bin/env bash
# Aplica en Docker los fixes de inventario vacío por usuario (espacio personal + sesión + UI).
set -euo pipefail
cd "$(dirname "$0")/.."

echo ">> Reconstruyendo inventario y nginx (backend + SPA)..."
docker compose build inventario nginx

echo ">> Levantando servicios..."
docker compose up -d inventario nginx

echo ">> Migraciones inventario (0017 repara espacios demo indebidos)..."
docker compose exec inventario python manage.py migrate --noinput

echo ">> Listo. Cierre sesión en el navegador, Ctrl+Shift+R, vuelva a entrar."
echo ">> Verifique GET /api/sesion/ → espacio_codigo debe ser usuario-<su_usuario>, no organizacion."

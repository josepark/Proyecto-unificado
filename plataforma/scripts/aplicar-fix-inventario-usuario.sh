#!/usr/bin/env bash
# Aplica en Docker los fixes de inventario vacío por usuario (espacio personal + sesión + UI).
set -euo pipefail
cd "$(dirname "$0")/.."

echo ">> Reconstruyendo inventario, rbac y nginx (backend + SPA)..."
docker compose build inventario rbac nginx

echo ">> Levantando servicios..."
docker compose up -d inventario rbac nginx

echo ">> Migraciones inventario (0017 repara espacios demo indebidos)..."
docker compose exec inventario python manage.py migrate --noinput

echo ">> Migración espacio RBAC (columnas + vistas — evita 500 en /rbac/api/resumen)..."
docker compose exec rbac python3 recuperar_rbac_db.py
docker compose exec rbac python3 migrar_espacio_datos.py
docker compose exec rbac python3 migrar_v2_1.py

echo ">> Listo. Cierre sesión en el navegador, Ctrl+Shift+R, vuelva a entrar."
echo ">> Verifique GET /api/sesion/ → espacio_codigo debe ser usuario-<su_usuario>, no organizacion."

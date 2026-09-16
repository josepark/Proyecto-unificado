#!/bin/bash
# Activa PostgreSQL para Inventario y Riesgos (producción concurrente).
#
# Uso (desde plataforma/):
#   ./scripts/activar-postgresql.sh
#   ./scripts/migrar-sqlite-a-postgresql.sh          # primera vez con datos SQLite
#   ./desplegar.sh --postgres --purgar --desbloquear admin
#
# Inventario → suiin_inventario | Riesgos → suiin_riesgos | RBAC Django → suiin_rbac

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

if [ ! -f .env ]; then
    rojo "Copie .env.example a .env primero."
    exit 1
fi

python3 - <<'PY'
import re
import secrets
from pathlib import Path
ruta = Path(".env")
lineas = ruta.read_text(encoding="utf-8").splitlines()
cambios = {
    "DJANGO_DB_ENGINE": "postgresql",
    "DJANGO_DB_NAME": "suiin_inventario",
    "RIESGOS_DB_NAME": "suiin_riesgos",
    "RBAC_DB_NAME": "suiin_rbac",
    "DJANGO_DB_USER": "suiin",
    "DJANGO_DB_HOST": "postgres",
    "DJANGO_DB_PORT": "5432",
    "GUNICORN_WORKERS": "3",
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
if not any(l.startswith("DJANGO_DB_PASSWORD=") and len(l.split("=", 1)[1].strip()) > 0 for l in lineas):
    pwd = secrets.token_urlsafe(24)
    lineas.append(f"DJANGO_DB_PASSWORD={pwd}")
    print("  .env → DJANGO_DB_PASSWORD=<generada>")
ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
PY

chmod +x postgres/init/01-create-riesgos-db.sh 2>/dev/null || true
chmod +x postgres/init/02-create-rbac-db.sh 2>/dev/null || true
chmod +x scripts/asegurar-bases-postgresql.sh 2>/dev/null || true

verde "PostgreSQL configurado en .env."
echo ""
echo "Para migrar y desplegar todo en un solo paso:"
echo "  ./postgresql.sh"
echo ""
echo "Opciones:"
echo "  ./postgresql.sh --solo-vacio"
echo "  ./postgresql.sh --reset-passwords"

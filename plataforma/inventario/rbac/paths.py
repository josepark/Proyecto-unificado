"""Rutas a datos compartidos con el árbol legacy Flask (migración / sembrado)."""
import os
from pathlib import Path

INVENTARIO_DIR = Path(__file__).resolve().parent.parent
PLATAFORMA_DIR = INVENTARIO_DIR.parent
RBAC_FLASK_DIR = PLATAFORMA_DIR / 'rbac'

# En Docker montamos plataforma/rbac/ en /app/rbac_origen (ver docker-compose).
RBAC_ORIGEN_DIR = Path(os.environ.get('RBAC_ORIGEN_DIR', RBAC_FLASK_DIR))

RBAC_DATA_JSON = RBAC_ORIGEN_DIR / 'rbac_data.json'
ATTACK_TECNICAS_JSON = RBAC_ORIGEN_DIR / 'static' / 'attack_tecnicas.json'
RBAC_DB_FLASK = Path(os.environ.get('RBAC_SQLITE_ORIGEN', RBAC_ORIGEN_DIR / 'rbac.db'))

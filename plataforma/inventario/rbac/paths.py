"""Rutas a datos compartidos con el árbol legacy Flask (migración / sembrado)."""
import os
from pathlib import Path

INVENTARIO_DIR = Path(__file__).resolve().parent.parent
PLATAFORMA_DIR = INVENTARIO_DIR.parent
RBAC_FLASK_DIR = PLATAFORMA_DIR / 'rbac'

RBAC_DATA_JSON = RBAC_FLASK_DIR / 'rbac_data.json'
ATTACK_TECNICAS_JSON = RBAC_FLASK_DIR / 'static' / 'attack_tecnicas.json'
RBAC_DB_FLASK = Path(os.environ.get('RBAC_SQLITE_ORIGEN', RBAC_FLASK_DIR / 'rbac.db'))

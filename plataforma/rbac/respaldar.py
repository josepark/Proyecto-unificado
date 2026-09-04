#!/usr/bin/env python3
"""
SUIIN-RBAC — Respaldo de la base de datos.
Crea una copia consistente y fechada de rbac.db en ./respaldos/ y conserva
las últimas 30 copias. Prográmelo en cron, p. ej. diario a las 02:00:
    0 2 * * *  cd /ruta/suiin-rbac && python3 respaldar.py
"""
import os
import sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE, "respaldos")
os.makedirs(DIR, exist_ok=True)

destino = os.path.join(DIR, f"rbac_{datetime.now():%Y%m%d_%H%M%S}.db")
origen = sqlite3.connect(os.path.join(BASE, "rbac.db"))
copia = sqlite3.connect(destino)
origen.backup(copia)          # copia consistente aunque la app esté en uso (WAL)
copia.close()
origen.close()
print(f"Respaldo creado: {destino}")

copias = sorted(f for f in os.listdir(DIR) if f.startswith("rbac_"))
for viejo in copias[:-30]:
    os.remove(os.path.join(DIR, viejo))
    print(f"Retención: eliminado {viejo}")

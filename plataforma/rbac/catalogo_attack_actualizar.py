#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — Genera static/attack_tecnicas.json a partir de la matriz
oficial de MITRE ATT&CK Enterprise (hoja "techniques" del Excel que se
descarga desde https://attack.mitre.org/resources/attack-data-and-tools/,
o directamente https://github.com/mitre-attack/attack-stix-data).

Ejecútelo cuando MITRE publique una nueva versión de la matriz Enterprise:

    python3 catalogo_attack_actualizar.py ruta/enterprise-attack-vXX.xlsx

Después reinicie la aplicación (o ejecute migrar_v2_1.py sobre una base
existente): el catálogo en la tabla attack_tecnica se sincroniza solo con
el contenido de static/attack_tecnicas.json al arrancar.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, "static", "attack_tecnicas.json")


def generar(ruta_xlsx):
    import openpyxl  # pip install openpyxl --break-system-packages
    wb = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=True)
    ws = wb["techniques"]
    filas = list(ws.iter_rows(min_row=2, values_only=True))

    tecnicas = []
    for r in filas:
        (tid, _stix, nombre, _desc, _url, _creado, _mod, dominio, _ver,
         tacticas, _plataformas, es_sub, padre) = r[:13]
        if dominio != "enterprise-attack" or not tid:
            continue
        tecnicas.append({
            "id": tid,
            "nombre": nombre,
            "tactica": tacticas or "",
            "es_subtecnica": bool(es_sub),
            "padre": padre or None,
        })
    tecnicas.sort(key=lambda t: t["id"])

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(tecnicas, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Catálogo generado: {DESTINO} ({len(tecnicas)} técnicas, "
          f"{sum(1 for t in tecnicas if not t['es_subtecnica'])} principales, "
          f"{sum(1 for t in tecnicas if t['es_subtecnica'])} subtécnicas)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 catalogo_attack_actualizar.py ruta/enterprise-attack-vXX.xlsx")
        sys.exit(1)
    generar(sys.argv[1])

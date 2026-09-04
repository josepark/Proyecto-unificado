#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — Regenera static/attack_tecnicas.json desde el catálogo
MITRE ATT&CK del Inventario (SUIIN-SGSI-INV-001), en vez de requerir el
Excel oficial de MITRE.

Despliegue integrado: el Inventario ya mantiene su propio catálogo MITRE
(actualizado a v19.1 mediante `python manage.py importar_mitre`, ver su
README sección 12), que en general es más reciente que el que trae RBAC de
fábrica. En vez de mantener dos catálogos por separado y descargar el
Excel de MITIRE dos veces, este script toma el del Inventario como fuente
para el de RBAC.

Uso (con ambos servicios corriendo, o RBAC_INTERNAL_URL apuntando al
Inventario):

    python3 catalogo_attack_desde_inventario.py
    python3 migrar_v2_1.py     # recarga static/attack_tecnicas.json en rbac.db

Esto reemplaza únicamente el paso de generar el JSON; el resto del flujo
(catalogo_attack.sincronizar(), usado por seed.py y migrar_v2_1.py) no
cambia. `catalogo_attack_actualizar.py` (a partir del Excel de MITIRE)
sigue funcionando igual, por si en algún momento el Inventario no está
disponible o se prefiere esa fuente.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, "static", "attack_tecnicas.json")

# Por defecto asume que este script corre en el mismo host que el
# Inventario (uso manual desde fuera de docker-compose); dentro de la red
# de docker-compose, defina INVENTARIO_URL=http://inventario:8000.
INVENTARIO_URL = os.environ.get("INVENTARIO_URL", "http://127.0.0.1:8000")


def generar():
    import requests  # pip install requests --break-system-packages

    tecnicas = []
    url = f"{INVENTARIO_URL}/api/amenazas/?page_size=2000&ordering=codigo"
    while url:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        resultados = data.get("results", data) if isinstance(data, dict) else data
        for a in resultados:
            if a["tipo"] not in ("TE", "ST"):
                continue  # RBAC solo cataloga técnicas/subtécnicas, no tácticas (TA)
            tecnicas.append({
                "id": a["codigo"],
                "nombre": a["nombre"],
                "tactica": a.get("tacticas") or "",
                "es_subtecnica": a["tipo"] == "ST",
                "padre": a.get("codigo_padre") or None,
            })
        url = data.get("next") if isinstance(data, dict) else None

    if not tecnicas:
        print("El Inventario no devolvió técnicas — revise INVENTARIO_URL "
              f"({INVENTARIO_URL}) y que el servicio esté arriba.")
        sys.exit(1)

    tecnicas.sort(key=lambda t: t["id"])
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(tecnicas, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Catálogo generado desde el Inventario ({INVENTARIO_URL}): "
          f"{DESTINO} ({len(tecnicas)} técnicas, "
          f"{sum(1 for t in tecnicas if not t['es_subtecnica'])} principales, "
          f"{sum(1 for t in tecnicas if t['es_subtecnica'])} subtécnicas). "
          "Ejecute ahora: python3 migrar_v2_1.py")


if __name__ == "__main__":
    generar()

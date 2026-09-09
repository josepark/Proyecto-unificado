#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenera static/attack_tecnicas.json desde el Inventario (solo stdlib — sin requests)."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, "static", "attack_tecnicas.json")
INVENTARIO_URL = os.environ.get("INVENTARIO_URL", "http://127.0.0.1:8000").rstrip("/")
JWT_SHARED_SECRET = os.environ.get("JWT_SHARED_SECRET", "")


def _get_json(url):
    headers = {}
    if JWT_SHARED_SECRET:
        headers["X-Plataforma-Secret"] = JWT_SHARED_SECRET
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generar():
    if not JWT_SHARED_SECRET:
        print("AVISO: JWT_SHARED_SECRET vacío — /api/interno/catalogo-mitre/ responderá 403.", file=sys.stderr)

    tecnicas = []
    url = f"{INVENTARIO_URL}/api/interno/catalogo-mitre/?page_size=2000&ordering=codigo"
    while url:
        try:
            data = _get_json(url)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code} al consultar {url}: {cuerpo}", file=sys.stderr)
            if e.code == 403:
                print("Revise JWT_SHARED_SECRET en .env y reconstruya inventario "
                      "(docker compose build inventario && docker compose up -d inventario).", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"No se pudo conectar a {url}: {e}", file=sys.stderr)
            sys.exit(1)

        resultados = data.get("results", data) if isinstance(data, dict) else data
        for a in resultados:
            if a["tipo"] not in ("TE", "ST"):
                continue
            tecnicas.append({
                "id": a["codigo"],
                "nombre": a["nombre"],
                "tactica": a.get("tacticas") or "",
                "es_subtecnica": a["tipo"] == "ST",
                "padre": a.get("codigo_padre") or None,
            })
        url = data.get("next") if isinstance(data, dict) else None

    if not tecnicas:
        print("El Inventario no devolvió técnicas — ¿ejecutó importar_mitre?", file=sys.stderr)
        sys.exit(1)

    tecnicas.sort(key=lambda t: t["id"])
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(tecnicas, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Catálogo generado desde el Inventario ({INVENTARIO_URL}): "
          f"{DESTINO} ({len(tecnicas)} técnicas). "
          "Ejecute ahora: python3 migrar_v2_1.py")


if __name__ == "__main__":
    generar()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida que las cuatro claves de .env no sigan siendo placeholders.

Salida:
  0 — todas las variables tienen valores propios
  1 — hay placeholders o variables ausentes
  2 — error de uso (archivo .env inexistente)

Uso:
    python3 validar_secretos.py
    python3 validar_secretos.py ruta/.env
"""
import re
import sys
from pathlib import Path

VARIABLES = [
    "DJANGO_SECRET_KEY",
    "JWT_SHARED_SECRET",
    "RIESGOS_SECRET_KEY",
    "SUIIN_RBAC_SECRET",
]
MARCADORES = ("defina-", "django-insecure-", "cambie-esto-", "suiin-rbac-desarrollo-")


def es_placeholder(valor: str) -> bool:
    if not valor:
        return True
    return any(valor.startswith(m) for m in MARCADORES)


def validar(ruta: Path) -> list[str]:
    if not ruta.exists():
        print(f"No se encontró {ruta}.", file=sys.stderr)
        sys.exit(2)

    contenido = ruta.read_text(encoding="utf-8")
    problemas = []
    for var in VARIABLES:
        m = re.search(rf"^{re.escape(var)}=(.*)$", contenido, re.MULTILINE)
        if not m:
            problemas.append(f"{var} (ausente)")
        elif es_placeholder(m.group(1).strip()):
            problemas.append(var)
    return problemas


def main():
    ruta = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
    problemas = validar(ruta)
    if not problemas:
        print("OK — las 4 claves de plataforma tienen valores propios.")
        return
    print("ERROR — secretos sin configurar:", ", ".join(problemas), file=sys.stderr)
    print("Ejecute: python3 generar_secretos.py", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

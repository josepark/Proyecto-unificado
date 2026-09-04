#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plataforma SUIIN-SGSI — Generador de secretos reales para .env

Hallazgo real que motivó este script: un despliegue corrió con
DJANGO_DEBUG=False mientras DJANGO_SECRET_KEY, JWT_SHARED_SECRET,
RIESGOS_SECRET_KEY y SUIIN_RBAC_SECRET seguían siendo literalmente el texto
de ejemplo de .env.example — nunca se reemplazaron. Las tres aplicaciones ya
se niegan a arrancar si detectan esto (ver README-DESPLIEGUE.md sección
11.5ter), pero autogenerarlos de una vez evita el paso manual de copiar y
pegar cuatro valores distintos.

Detecta cuáles de las cuatro variables siguen con el valor de ejemplo (los
que empiezan con "defina-") y SOLO genera esas — nunca toca una variable que
ya tenga un valor propio, aunque el script se corra varias veces por error.

Uso:
    python3 generar_secretos.py            # opera sobre ./.env
    python3 generar_secretos.py otra/ruta.env
"""
import re
import secrets
import shutil
import sys
from datetime import datetime
from pathlib import Path

VARIABLES = ["DJANGO_SECRET_KEY", "JWT_SHARED_SECRET", "RIESGOS_SECRET_KEY", "SUIIN_RBAC_SECRET"]


def generar_valor() -> str:
    return secrets.token_urlsafe(50)


def main():
    ruta = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")

    if not ruta.exists():
        print(f"No se encontró {ruta}.", file=sys.stderr)
        ejemplo = ruta.parent / ".env.example"
        if ejemplo.exists():
            print(f"¿Copió {ejemplo.name} a {ruta.name} primero? "
                  f"cp {ejemplo} {ruta}", file=sys.stderr)
        sys.exit(1)

    lineas = ruta.read_text(encoding="utf-8").splitlines()
    respaldo = ruta.with_name(f"{ruta.name}.bak.{datetime.now():%Y%m%d%H%M%S}")
    shutil.copy(ruta, respaldo)

    cambiadas = []
    for var in VARIABLES:
        patron = re.compile(rf"^{re.escape(var)}=(.*)$")
        encontrada = False
        for i, linea in enumerate(lineas):
            m = patron.match(linea)
            if m:
                encontrada = True
                valor_actual = m.group(1).strip()
                if not valor_actual or valor_actual.startswith("defina-"):
                    lineas[i] = f"{var}={generar_valor()}"
                    cambiadas.append(var)
                    print(f"✓ {var} generado")
                else:
                    print(f"— {var} ya tiene un valor propio, no se toca")
                break
        if not encontrada:
            lineas.append(f"{var}={generar_valor()}")
            cambiadas.append(var)
            print(f"✓ {var} agregado (no existía en el archivo)")

    if cambiadas:
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"\n{len(cambiadas)} variable(s) generada(s): {', '.join(cambiadas)}")
        print(f"Respaldo del archivo anterior: {respaldo.name} (bórrelo cuando confirme que todo quedó bien)")
        print("\nReinicie los contenedores para que tomen los valores nuevos:")
        print("  docker compose down --rmi all && docker compose up -d --build")
    else:
        respaldo.unlink()  # no hubo cambios, no hace falta el respaldo
        print("\nNada que generar — las 4 variables ya tenían valores propios.")


if __name__ == "__main__":
    main()

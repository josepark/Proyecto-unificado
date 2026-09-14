#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unitarias — prioridad 2 (secretos y respaldo)."""
import os
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(BASE))

from validar_secretos import validar  # noqa: E402


class ValidarSecretosTest(unittest.TestCase):
    def test_rechaza_placeholders(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("DJANGO_SECRET_KEY=defina-una-clave\n")
            f.write("JWT_SHARED_SECRET=defina-jwt\n")
            f.write("RIESGOS_SECRET_KEY=defina-riesgos\n")
            f.write("SUIIN_RBAC_SECRET=defina-rbac\n")
            ruta = f.name
        try:
            problemas = validar(Path(ruta))
            self.assertEqual(len(problemas), 4)
        finally:
            os.unlink(ruta)

    def test_acepta_valores_reales(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("DJANGO_SECRET_KEY=" + "x" * 50 + "\n")
            f.write("JWT_SHARED_SECRET=" + "y" * 50 + "\n")
            f.write("RIESGOS_SECRET_KEY=" + "z" * 50 + "\n")
            f.write("SUIIN_RBAC_SECRET=" + "w" * 50 + "\n")
            ruta = f.name
        try:
            problemas = validar(Path(ruta))
            self.assertEqual(problemas, [])
        finally:
            os.unlink(ruta)


if __name__ == "__main__":
    unittest.main()

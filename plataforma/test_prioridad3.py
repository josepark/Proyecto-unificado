#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas unitarias — prioridad 3 (JWT refresh, sin base de datos)."""
import unittest
from unittest.mock import MagicMock, patch

import jwt

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "inventario"))

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
django.setup()

SETTINGS = {
    "JWT_SHARED_SECRET": "secreto-unit",
    "JWT_ALGORITHM": "HS256",
    "JWT_ISSUER": "suiin-inventario",
    "JWT_EXPIRACION_MINUTOS": 30,
    "JWT_REFRESH_EXPIRACION_DIAS": 7,
}


def _usuario_mock():
    user = MagicMock()
    user.pk = 42
    user.get_username.return_value = "usuario_test"
    return user


class JWTRefreshPureTest(unittest.TestCase):
    def test_renovar_desde_refresh(self):
        from inventario import jwt_plataforma as jp

        user = _usuario_mock()
        espacio = MagicMock(codigo="usuario-test")

        with patch.object(jp, "settings") as mock_settings:
            for clave, valor in SETTINGS.items():
                setattr(mock_settings, clave, valor)
            with patch.object(jp, "jwt_version_de", return_value=1), \
                 patch.object(jp, "modulos_de", return_value=["riesgos"]), \
                 patch.object(jp, "roles_de", return_value=["Dinamizador"]), \
                 patch.object(jp, "espacio_datos_de", return_value=espacio):
                _, _, refresh, _ = jp.emitir_par_jwt(user)

        with patch.object(jp, "settings") as mock_settings:
            for clave, valor in SETTINGS.items():
                setattr(mock_settings, clave, valor)
            with patch.object(jp.User, "objects") as manager, \
                 patch.object(jp, "jwt_version_de", return_value=1), \
                 patch.object(jp, "modulos_de", return_value=["riesgos"]), \
                 patch.object(jp, "roles_de", return_value=["Dinamizador"]), \
                 patch.object(jp, "espacio_datos_de", return_value=espacio):
                manager.get.return_value = user
                access, _, nuevo_refresh, _ = jp.renovar_desde_refresh(refresh)

        payload = jwt.decode(
            access,
            SETTINGS["JWT_SHARED_SECRET"],
            algorithms=[SETTINGS["JWT_ALGORITHM"]],
            issuer=SETTINGS["JWT_ISSUER"],
        )
        self.assertEqual(payload["typ"], "access")
        self.assertEqual(payload["username"], "usuario_test")
        self.assertTrue(nuevo_refresh)

    def test_refresh_invalido(self):
        from inventario.jwt_plataforma import renovar_desde_refresh, RefreshTokenInvalido

        with self.assertRaises(RefreshTokenInvalido):
            renovar_desde_refresh("")


if __name__ == "__main__":
    unittest.main()

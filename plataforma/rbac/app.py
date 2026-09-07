#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUIIN-RBAC v2.1 — API de gestión de la Matriz de Control de Acceso
Documento fuente: SUIIN-SGSI-MCA-001 v2.0 · ISO/IEC 27002:2022 (5.15–5.18, 8.15)

Backend JSON para la SPA unificada de React. Sin inicio de sesión propio:
nginx delega la autorización en la sesión del Inventario (auth_request).

Uso (desarrollo):   python3 seed.py && python3 app.py
Uso (producción):   ./run_produccion.sh
"""
import os
import warnings
from datetime import timedelta

from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import api_rest
from db import aplicar_vencimientos, cerrar_db


def crear_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get(
        "SUIIN_RBAC_SECRET", "suiin-rbac-desarrollo-cambiar-en-produccion")

    _es_placeholder = app.secret_key.startswith(("defina-", "suiin-rbac-desarrollo-"))
    _debug = os.environ.get("DJANGO_DEBUG", "False") == "True"
    if _es_placeholder and not _debug:
        raise RuntimeError(
            "No se puede arrancar con DJANGO_DEBUG=False mientras SUIIN_RBAC_SECRET siga con "
            "el valor de ejemplo de .env.example. Genere un valor real y aleatorio y actualice "
            "su archivo .env — ver README-DESPLIEGUE.md."
        )
    if _es_placeholder and _debug:
        warnings.warn(
            "Usando el valor de ejemplo/desarrollo para SUIIN_RBAC_SECRET. "
            "No debe llegar a producción.",
        )

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    api_rest.registrar(app)
    app.before_request(auth.proteger_peticion)
    app.before_request(aplicar_vencimientos)
    app.after_request(auth.encabezados_seguridad)
    app.teardown_appcontext(cerrar_db)

    @app.errorhandler(404)
    def _error_404(_e):
        return jsonify({"detail": "Recurso no encontrado."}), 404

    @app.errorhandler(403)
    def _error_403(_e):
        return jsonify({"detail": "Acceso rechazado."}), 403

    @app.errorhandler(413)
    def _error_413(_e):
        return jsonify({"detail": "Archivo demasiado grande (máximo 1 MB)."}), 413

    @app.errorhandler(500)
    def _error_500(_e):
        return jsonify({"detail": "Error interno del servidor."}), 500

    return app


app = crear_app()

if __name__ == "__main__":
    from db import DB
    if not os.path.exists(DB):
        print("No existe rbac.db — ejecute primero: python3 seed.py")
        raise SystemExit(1)
    app.run(debug=False, host="127.0.0.1", port=5000)

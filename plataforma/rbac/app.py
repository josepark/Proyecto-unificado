#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUIIN-RBAC v2.1 — Aplicación web de gestión de la Matriz de Control de Acceso
Documento fuente: SUIIN-SGSI-MCA-001 v2.0 · ISO/IEC 27002:2022 (5.15–5.18, 8.15)

Sin inicio de sesión (uso local / monousuario). Conserva: CSRF, encabezados
de seguridad, bitácora encadenada por hash y vencimientos automáticos.

Uso (desarrollo):   python3 seed.py && python3 app.py
Uso (producción):   ./run_produccion.sh
"""
import os
from datetime import timedelta

from flask import Flask, g, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import api_rest
import rutas
from db import aplicar_vencimientos, cerrar_db


def crear_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get(
        "SUIIN_RBAC_SECRET", "suiin-rbac-desarrollo-cambiar-en-produccion")

    # Guardia contra secretos sin configurar — mismo mecanismo que en
    # inventario/config/settings.py y riesgos/.../settings.py (hallazgo real
    # de un despliegue que corrió con el valor de ejemplo de .env.example sin
    # reemplazar). DJANGO_DEBUG es el mismo interruptor que ya usan las otras
    # dos apps del mismo .env compartido — no se introduce uno nuevo solo
    # para RBAC.
    _es_placeholder = app.secret_key.startswith(("defina-", "suiin-rbac-desarrollo-"))
    _debug = os.environ.get("DJANGO_DEBUG", "False") == "True"
    if _es_placeholder and not _debug:
        raise RuntimeError(
            "No se puede arrancar con DJANGO_DEBUG=False mientras SUIIN_RBAC_SECRET siga con "
            "el valor de ejemplo de .env.example. Genere un valor real y aleatorio (ej. "
            "`python3 -c \"import secrets; print(secrets.token_urlsafe(50))\"`) y actualice su "
            "archivo .env — ver README-DESPLIEGUE.md."
        )
    if _es_placeholder and _debug:
        import warnings
        warnings.warn(
            "⚠ Usando el valor de ejemplo/desarrollo para SUIIN_RBAC_SECRET. Aceptable con "
            "DJANGO_DEBUG=True, pero NO debe llegar a producción.",
        )

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    # Despliegue integrado: la app se sirve bajo el prefijo /rbac/ detrás del
    # gateway nginx de la plataforma SUIIN. ProxyFix ajusta SCRIPT_NAME a
    # partir de X-Forwarded-Prefix para que url_for() genere enlaces y
    # recursos estáticos correctos bajo ese prefijo, y respeta también
    # X-Forwarded-Proto/Host/For para que la app "vea" la petición real del
    # cliente en vez de la del proxy interno.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    rutas.registrar(app)
    api_rest.registrar(app)
    app.before_request(auth.proteger_peticion)
    app.before_request(aplicar_vencimientos)
    app.after_request(auth.encabezados_seguridad)
    app.teardown_appcontext(cerrar_db)

    # Despliegue integrado: cuando el módulo se carga incrustado dentro del
    # Inventario (iframe con ?embed=1), estos dos hooks hacen que TODO enlace
    # y redirect generado con url_for() dentro de la app conserve ese
    # parámetro automáticamente, sin tener que tocar cada plantilla o cada
    # redirect(url_for(...)) de rutas.py uno por uno.
    @app.url_value_preprocessor
    def _leer_embed(_endpoint, _values):
        g.embed = request.args.get("embed")

    @app.url_defaults
    def _propagar_embed(endpoint, values):
        if endpoint != "static" and getattr(g, "embed", None) and "embed" not in values:
            values["embed"] = g.embed

    @app.context_processor
    def _contexto():
        return {"csrf_campo": auth.csrf_campo, "static_v": _static_v}

    def _static_v(filename):
        """URL de un estático con parámetro de versión según su fecha de
        modificación en disco, para que el navegador nunca sirva una copia
        en caché desactualizada tras una actualización del código — el
        incidente que motivó esto: app.js se corrigió en el servidor pero
        el navegador siguió usando la versión vieja porque la URL no había
        cambiado. Si el archivo no cambia, la URL tampoco cambia, así que
        el cacheo normal sigue funcionando igual de bien entre despliegues."""
        ruta = os.path.join(app.static_folder, filename)
        try:
            v = int(os.path.getmtime(ruta))
        except OSError:
            v = 0
        return f"{url_for('static', filename=filename)}?v={v}"

    def _pagina_error(codigo, titulo, mensaje):
        return render_template("error.html", codigo=codigo, titulo=titulo,
                               mensaje=mensaje), codigo

    @app.errorhandler(404)
    def _error_404(_e):
        return _pagina_error(404, "Página no encontrada",
                             "El enlace al que intentó acceder no existe, o el "
                             "registro correspondiente fue eliminado o desactivado.")

    @app.errorhandler(403)
    def _error_403(_e):
        return _pagina_error(403, "Acceso rechazado",
                             "La solicitud fue rechazada por seguridad. Vuelva "
                             "a la página anterior y reintente la acción.")

    @app.errorhandler(413)
    def _error_413(_e):
        return _pagina_error(413, "Archivo demasiado grande",
                             "El archivo enviado supera el tamaño máximo "
                             "permitido (1 MB).")

    @app.errorhandler(500)
    def _error_500(_e):
        return _pagina_error(500, "Error interno",
                             "Ocurrió un error inesperado al procesar la "
                             "solicitud. Si persiste, contacte al "
                             "administrador del SGSI.")

    return app


app = crear_app()

if __name__ == "__main__":
    from db import DB
    if not os.path.exists(DB):
        print("No existe rbac.db — ejecute primero: python3 seed.py")
        raise SystemExit(1)
    app.run(debug=False, host="127.0.0.1", port=5000)

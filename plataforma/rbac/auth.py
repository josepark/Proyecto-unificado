#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — protecciones de la aplicación sin inicio de sesión:
tokens CSRF por sesión anónima y encabezados de seguridad HTTP."""
import secrets

from flask import abort, request, session
from markupsafe import Markup


def _csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


def csrf_campo():
    return Markup(f'<input type="hidden" name="_csrf" value="{_csrf_token()}">')


def csrf_token_actual():
    """Para la API JSON: el front-end (React) lo pide una vez y lo reenvía
    como encabezado X-CSRF-Token en cada POST/PUT/DELETE, igual que Django
    hace con X-CSRFToken — mismo token de sesión que ya usan los
    formularios HTML, ninguna protección nueva ni distinta."""
    return _csrf_token()


def proteger_peticion():
    """Valida el token CSRF de toda escritura: formularios propios
    (campo _csrf) o la API JSON (encabezado X-CSRF-Token) — mismo token,
    dos formas de enviarlo."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        token = session.get("csrf")
        enviado = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not token or enviado != token:
            abort(403)
    return None


def encabezados_seguridad(resp):
    # SAMEORIGIN (no DENY): el módulo ahora se incrusta en un <iframe> del
    # Inventario, servido bajo el mismo origen a través del gateway nginx de
    # la plataforma. Un origen externo sigue sin poder enmarcar la app.
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; frame-ancestors 'self'; "
        # script-src sin 'unsafe-inline': todo el JS vive en static/app.js
        # (event listeners delegados; los formularios usan data-confirm /
        # data-auto-submit en vez de atributos onclick/onchange inline).
        # style-src y font-src incluyen Google Fonts (Space Grotesk/Inter/IBM
        # Plex Mono) — se agregaron en el rediseño visual sin revisar esta
        # política, así que quedaban bloqueadas por CSP (confirmado con el
        # error real de consola: "violates ... style-src 'self'
        # 'unsafe-inline'"); RBAC caía a la fuente del sistema en silencio.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'")
    return resp

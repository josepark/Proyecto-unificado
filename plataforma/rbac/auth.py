#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — protecciones HTTP: CSRF por sesión anónima y encabezados."""
import secrets

from flask import abort, request, session


def _csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


def csrf_token_actual():
    return _csrf_token()


def proteger_peticion():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        token = session.get("csrf")
        enviado = request.headers.get("X-CSRF-Token")
        if not token or enviado != token:
            abort(403)
    return None


def encabezados_seguridad(resp):
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'self'"
    return resp

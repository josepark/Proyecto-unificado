"""CSRF por sesión Django — mismo contrato que rbac/auth.py (Flask)."""
import secrets

from django.http import HttpRequest

SESSION_KEY = 'rbac_csrf'


def token_actual(request: HttpRequest) -> str:
    if SESSION_KEY not in request.session:
        request.session[SESSION_KEY] = secrets.token_hex(32)
    return request.session[SESSION_KEY]


def validar_csrf(request: HttpRequest) -> bool:
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return True
    enviado = request.headers.get('X-CSRF-Token', '')
    esperado = request.session.get(SESSION_KEY)
    return bool(esperado and enviado == esperado)

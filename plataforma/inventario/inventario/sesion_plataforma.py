"""Sesión Django unificada — mismo criterio que GET /api/sesion/ para todo el API."""
import time

from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.db.utils import OperationalError
from rest_framework.authentication import SessionAuthentication


def http_request(request):
    """DRF envuelve HttpRequest; la sesión y cookies viven en el objeto interno."""
    return getattr(request, "_request", request)


def _uid_desde_sesion(sesion):
    return sesion.get("_auth_user_id")


def _cargar_sesion_por_cookie(clave):
    """Carga sesión desde cookie con reintento breve (SQLite bajo ráfaga concurrente)."""
    for intento in range(3):
        sesion = SessionStore(session_key=clave)
        try:
            sesion.load()
            return _uid_desde_sesion(sesion)
        except OperationalError:
            if intento == 2:
                return None
            time.sleep(0.05 * (intento + 1))
        except Exception:
            return None
    return None


def _usuario_por_id(uid):
    for intento in range(3):
        try:
            return get_user_model().objects.get(pk=uid)
        except OperationalError:
            if intento == 2:
                raise
            time.sleep(0.05 * (intento + 1))
        except get_user_model().DoesNotExist:
            return None
    return None


def usuario_desde_sesion(request):
    """Usuario de la sesión Django — respaldo si DRF no re-hidrato request.user."""
    req = http_request(request)
    user = get_user(req)
    if getattr(user, "is_authenticated", False):
        return user

    uid = None
    if req.session.session_key:
        uid = _uid_desde_sesion(req.session)

    if not uid:
        clave = req.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if clave:
            uid = _cargar_sesion_por_cookie(clave)

    if not uid:
        return None
    return _usuario_por_id(uid)


class SesionPlataformaAuthentication(SessionAuthentication):
    """SessionAuthentication + respaldo por cookie (igual que /api/sesion/)."""

    def authenticate(self, request):
        req = http_request(request)
        if not getattr(req.user, "is_authenticated", False):
            user = usuario_desde_sesion(req)
            if user is not None:
                req.user = user
        user = req.user
        if not getattr(user, "is_authenticated", False):
            return None
        self.enforce_csrf(request)
        return (user, None)

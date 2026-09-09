# -*- coding: utf-8 -*-
"""Consulta la versión vigente del JWT en el Inventario (revocación por cambio de rol)."""
import requests
from django.conf import settings


def jwt_version_vigente(username):
    if not settings.JWT_SHARED_SECRET or not username:
        return None
    base = settings.INVENTARIO_API_URL.rstrip("/")
    try:
        r = requests.get(
            f"{base}/auth/jwt-version/{username}/",
            headers={"X-Plataforma-Secret": settings.JWT_SHARED_SECRET},
            timeout=2,
        )
        if r.status_code == 200:
            return r.json().get("ver")
    except requests.RequestException:
        pass
    return None

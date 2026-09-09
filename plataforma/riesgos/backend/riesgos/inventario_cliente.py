"""Peticiones servidor-a-servidor al Inventario (misma red docker-compose)."""
import requests
from django.conf import settings

# Endpoint dedicado — no depende de permisos del ViewSet /api/amenazas/
CATALOGO_MITRE_INTERNO = "/interno/catalogo-mitre/"


def headers_inventario():
    """Cabecera compartida con jwt_version_usuario — ver inventario.permisos."""
    if not settings.JWT_SHARED_SECRET:
        return {}
    return {"X-Plataforma-Secret": settings.JWT_SHARED_SECRET}


def url_catalogo_mitre(base_url):
    return f"{base_url.rstrip('/')}{CATALOGO_MITRE_INTERNO}"


def get(url, **kwargs):
    cabeceras = dict(kwargs.pop("headers", {}))
    cabeceras.update(headers_inventario())
    return requests.get(url, headers=cabeceras, **kwargs)

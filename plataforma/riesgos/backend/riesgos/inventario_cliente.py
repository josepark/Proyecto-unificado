"""Peticiones servidor-a-servidor al Inventario (misma red docker-compose)."""
import requests
from django.conf import settings

# Endpoint dedicado — no depende de permisos del ViewSet /api/amenazas/
CATALOGO_MITRE_INTERNO = "/interno/catalogo-mitre/"


def headers_inventario(espacio_codigo=None):
    """Cabecera compartida con jwt_version_usuario — ver inventario.permisos."""
    headers = {}
    if settings.JWT_SHARED_SECRET:
        headers["X-Plataforma-Secret"] = settings.JWT_SHARED_SECRET
    if espacio_codigo:
        headers["X-Espacio-Datos"] = espacio_codigo
    return headers


def url_catalogo_mitre(base_url):
    return f"{base_url.rstrip('/')}{CATALOGO_MITRE_INTERNO}"


def get(url, espacio_codigo=None, **kwargs):
    cabeceras = dict(kwargs.pop("headers", {}))
    cabeceras.update(headers_inventario(espacio_codigo=espacio_codigo))
    return requests.get(url, headers=cabeceras, **kwargs)

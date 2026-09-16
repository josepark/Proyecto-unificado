"""Espacio de datos activo — nginx reenvía X-Espacio-Datos desde Inventario."""
from django.http import HttpRequest

ESPACIO_ORGANIZACION = 'organizacion'


def espacio_codigo_actual(request: HttpRequest) -> str:
    codigo = (request.headers.get('X-Espacio-Datos') or '').strip()
    return codigo or ESPACIO_ORGANIZACION

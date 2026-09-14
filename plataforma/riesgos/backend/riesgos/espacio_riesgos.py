# -*- coding: utf-8 -*-
"""Espacios de datos por usuario — aísla activos y datos operativos de Riesgos."""
from django.conf import settings

ESPACIO_ORGANIZACION = "organizacion"


def es_peticion_servicio_interno(request):
    secreto = request.headers.get("X-Plataforma-Secret", "")
    return bool(settings.JWT_SHARED_SECRET and secreto == settings.JWT_SHARED_SECRET)


def espacio_codigo_de_request(request):
    """Espacio activo: JWT de plataforma, cabecera interna o demo organizacional."""
    auth = getattr(request, "auth", None)
    if isinstance(auth, dict):
        codigo = (auth.get("espacio_codigo") or "").strip()
        if codigo:
            return codigo
    if es_peticion_servicio_interno(request):
        codigo = (request.headers.get("X-Espacio-Datos") or "").strip()
        return codigo or ESPACIO_ORGANIZACION
    return ESPACIO_ORGANIZACION


class FiltrarEspacioMixin:
    """Filtra queryset por espacio_codigo del request."""

    campo_espacio = "espacio_codigo"

    def queryset_por_espacio(self, qs):
        return qs.filter(**{self.campo_espacio: espacio_codigo_de_request(self.request)})

    def get_queryset(self):
        qs = super().get_queryset()
        return self.queryset_por_espacio(qs)

    def perform_create(self, serializer):
        serializer.save(**{self.campo_espacio: espacio_codigo_de_request(self.request)})


class FiltrarEspacioPorActivoMixin:
    """Filtra registros hijos vía activo__espacio_codigo."""

    def get_queryset(self):
        qs = super().get_queryset()
        codigo = espacio_codigo_de_request(self.request)
        return qs.filter(activo__espacio_codigo=codigo)

# -*- coding: utf-8 -*-
"""
sembrar_catalogos — Puebla CatalogoValor extrayendo los valores DISTINTOS que
ya están en uso en los datos reales, para que el catálogo arranque con el
vocabulario institucional real de CRIC/SUIIN en vez de una lista vacía o
genérica. Idempotente (get_or_create) — correrlo de nuevo más adelante solo
agrega valores nuevos que hayan aparecido, no duplica ni borra nada.

Uso:
    python manage.py sembrar_catalogos
"""
from django.core.management.base import BaseCommand

from riesgos.models import Activo, RiesgoActivo, AccionTratamiento, Vulnerabilidad, CatalogoValor

CAMPOS_A_SEMBRAR = [
    (Activo, "tipo", "TIPO_ACTIVO"),
    (RiesgoActivo, "responsable_sugerido", "RESPONSABLE_RIESGO"),
    (AccionTratamiento, "responsable", "RESPONSABLE_ACCION"),
    (AccionTratamiento, "fuente", "FUENTE_HALLAZGO"),
    (AccionTratamiento, "plazo", "PLAZO_ACCION"),
    (Vulnerabilidad, "solucion_recomendada", "SOLUCION_VULN"),
]


class Command(BaseCommand):
    help = "Puebla el catálogo de valores a partir de lo ya usado en los datos reales."

    def handle(self, *args, **options):
        total_creados = 0
        for modelo, campo, categoria in CAMPOS_A_SEMBRAR:
            valores = (
                modelo.objects.exclude(**{campo: ""})
                .values_list(campo, flat=True).distinct().order_by(campo)
            )
            creados_aqui = 0
            for i, valor in enumerate(valores):
                valor = valor.strip()
                if not valor:
                    continue
                _, creado = CatalogoValor.objects.get_or_create(
                    categoria=categoria, valor=valor, defaults={"orden": i})
                if creado:
                    creados_aqui += 1
            total_creados += creados_aqui
            self.stdout.write(
                f"  · {categoria}: {creados_aqui} valor(es) nuevo(s) "
                f"(de {modelo.__name__}.{campo})")

        self.stdout.write(self.style.SUCCESS(
            f"Catálogo sembrado: {total_creados} valor(es) nuevo(s) en total."))

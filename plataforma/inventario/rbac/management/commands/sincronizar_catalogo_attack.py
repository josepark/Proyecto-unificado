"""Propaga el catálogo MITRE ATT&CK Inventario → base RBAC Django."""
import urllib.error

from django.core.management.base import BaseCommand, CommandError

from rbac import catalogo_attack


class Command(BaseCommand):
    help = (
        'Descarga /api/interno/catalogo-mitre/ del Inventario y repuebla '
        'attack_tecnica en la base alias rbac (sustituye Flask catalogo_attack_desde_inventario.py).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--inventario-url',
            default=None,
            help='Base URL del Inventario (default: INVENTARIO_URL o http://inventario:8000)',
        )

    def handle(self, *args, **options):
        try:
            n = catalogo_attack.sincronizar_desde_inventario(
                inventario_url=options.get('inventario_url'),
            )
        except urllib.error.HTTPError as exc:
            raise CommandError(f'HTTP {exc.code} al consultar catálogo MITRE del Inventario') from exc
        except (urllib.error.URLError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f'attack_tecnica actualizado: {n} técnicas'))

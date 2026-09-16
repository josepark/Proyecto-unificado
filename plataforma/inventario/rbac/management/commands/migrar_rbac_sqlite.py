"""Copia rbac/rbac.db (Flask) a la base Django alias rbac (Fase 1.4)."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rbac.paths import RBAC_DB_FLASK
from rbac.migracion_sqlite import MigracionError, migrar


class Command(BaseCommand):
    help = (
        'Migra datos desde rbac/rbac.db (SQLite Flask) hacia la base RBAC Django '
        '(PostgreSQL suiin_rbac o SQLite rbac_django.sqlite3).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--origen',
            type=str,
            default=str(RBAC_DB_FLASK),
            help='Ruta al rbac.db de Flask (por defecto plataforma/rbac/rbac.db)',
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Vacía la base destino antes de copiar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra conteos del origen sin escribir',
        )

    def handle(self, *args, **options):
        origen = Path(options['origen'])
        try:
            resultado = migrar(
                origen=origen,
                forzar=options['forzar'],
                dry_run=options['dry_run'],
            )
        except MigracionError as exc:
            raise CommandError(str(exc)) from exc

        if resultado.get('dry_run'):
            self.stdout.write('Conteos en origen (dry-run):')
            for tabla, n in resultado['origen'].items():
                self.stdout.write(f'  {tabla}: {n}')
            return

        self.stdout.write(self.style.SUCCESS(
            f'Migración RBAC completada desde {resultado["origen_path"]}'
        ))
        for tabla in resultado['destino']:
            self.stdout.write(
                f'  {tabla}: {resultado["destino"][tabla]} filas'
            )

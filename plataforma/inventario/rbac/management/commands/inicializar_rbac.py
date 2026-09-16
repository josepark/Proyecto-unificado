"""Puebla la base RBAC Django si está vacía (Docker / PostgreSQL post-migración)."""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from rbac.migracion_sqlite import MigracionError, origen_sqlite_usable
from rbac.models import Rol
from rbac.paths import RBAC_DATA_JSON, RBAC_DB_FLASK


class Command(BaseCommand):
    help = (
        'Si la base alias rbac no tiene roles, migra desde rbac.db (Flask) o '
        'siembra desde rbac_data.json. Idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar-migracion',
            action='store_true',
            help='Pasa --forzar a migrar_rbac_sqlite cuando el origen es rbac.db',
        )

    def handle(self, *args, **options):
        using = 'rbac'
        roles = Rol.objects.using(using).count()
        if roles > 0:
            self.stdout.write(f'RBAC ya tiene {roles} roles — omitiendo inicialización.')
            return

        if origen_sqlite_usable(RBAC_DB_FLASK):
            self.stdout.write(f'Migrando RBAC desde {RBAC_DB_FLASK}…')
            migrar_args = []
            if options['forzar_migracion']:
                migrar_args.append('--forzar')
            try:
                call_command('migrar_rbac_sqlite', *migrar_args)
            except CommandError as exc:
                self.stdout.write(self.style.WARNING(
                    f'migrar_rbac_sqlite falló ({exc}) — intentando sembrar_rbac…'
                ))
            else:
                roles = Rol.objects.using(using).count()
                if roles > 0:
                    self.stdout.write(self.style.SUCCESS(f'RBAC inicializado: {roles} roles.'))
                    return

        if RBAC_DATA_JSON.is_file():
            self.stdout.write(f'Sembrando RBAC desde {RBAC_DATA_JSON}…')
            call_command('sembrar_rbac', forzar=True)
            return

        raise CommandError(
            'La base RBAC está vacía y no hay rbac.db legible ni rbac_data.json. '
            'Monte ./rbac en el contenedor (RBAC_ORIGEN_DIR=/app/rbac_origen) o ejecute '
            './scripts/migrar-rbac-postgresql.sh --forzar'
        )

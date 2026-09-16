"""Crea suiin_riesgos y suiin_rbac si faltan (volúmenes PG anteriores a Fase 1.1)."""
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Crea bases PostgreSQL auxiliares (suiin_riesgos, suiin_rbac) si no existen.'

    def handle(self, *args, **options):
        if os.environ.get('DJANGO_DB_ENGINE') != 'postgresql':
            self.stdout.write('DJANGO_DB_ENGINE no es postgresql — omitiendo.')
            return
        if connection.vendor != 'postgresql':
            self.stdout.write('Conexión default no es PostgreSQL — omitiendo.')
            return

        db_user = os.environ.get('DJANGO_DB_USER', 'suiin')
        rbac_name = settings.DATABASES['rbac']['NAME']
        riesgos_name = os.environ.get('RIESGOS_DB_NAME', 'suiin_riesgos')

        for nombre in (riesgos_name, rbac_name):
            self._crear_si_falta(nombre, db_user)

    def _crear_si_falta(self, nombre, owner):
        connection.ensure_connection()
        autocommit_prev = connection.get_autocommit()
        connection.set_autocommit(True)
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', [nombre])
                if cur.fetchone():
                    self.stdout.write(f'Base {nombre}: OK')
                    return
                cur.execute(f'CREATE DATABASE "{nombre}" OWNER "{owner}"')
            self.stdout.write(self.style.SUCCESS(f'Base {nombre} creada.'))
        finally:
            connection.set_autocommit(autocommit_prev)

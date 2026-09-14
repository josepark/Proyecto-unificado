# -*- coding: utf-8 -*-
"""
desbloquear_login — Diagnostica y limpia por completo cualquier bloqueo de
login (django-axes) para un usuario, mostrando el ANTES y el DESPUÉS con datos
reales de la base de datos, en vez de confiar en un mensaje genérico de éxito
como el de `axes_reset_username` (que en un despliegue real reportó haber
funcionado sin que el bloqueo realmente desapareciera — causa no confirmada
del todo, ver README-DESPLIEGUE.md sección 11.5bis). Este comando:

  1. Muestra qué hay en AccessAttempt/AccessFailureLog/AccessLog ANTES.
  2. Corre el reset oficial de axes (la vía normal).
  3. Además borra DIRECTO por ORM, sin pasar por esa capa intermedia, por si
     el problema estuviera ahí.
  4. Busca también filas con el username guardado con mayúsculas o espacios
     distintos (que un filtro exacto no atraparía).
  5. Muestra el DESPUÉS, para confirmar con evidencia — no con un mensaje.

Uso:
    python manage.py desbloquear_login admin
    python manage.py desbloquear_login admin --todos   # limpia TODO axes, no solo ese usuario
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnostica y desbloquea por completo el login de un usuario (django-axes)."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "--todos", action="store_true",
            help="Además, limpia TODAS las filas de axes (de cualquier usuario/IP) — "
                 "úselo si sigue bloqueado después del reset normal por ese usuario.")

    def handle(self, *args, **options):
        from axes.models import AccessAttempt, AccessFailureLog, AccessLog
        from axes.utils import reset

        username = options["username"]

        self.stdout.write(self.style.WARNING(f"=== Estado ANTES para {username!r} ==="))
        self._mostrar_estado(username, AccessAttempt)

        n = reset(username=username)
        self.stdout.write(f"1) axes.utils.reset(): {n} fila(s) de AccessAttempt eliminada(s).")

        borrados_attempt, _ = AccessAttempt.objects.filter(username__iexact=username).delete()
        borrados_fail, _ = AccessFailureLog.objects.filter(username__iexact=username).delete()
        borrados_log, _ = AccessLog.objects.filter(username__iexact=username).delete()
        self.stdout.write(
            f"2) Borrado directo (case-insensitive): {borrados_attempt} AccessAttempt, "
            f"{borrados_fail} AccessFailureLog, {borrados_log} AccessLog.")

        extra = 0
        objetivo = username.strip().casefold()
        for modelo in (AccessAttempt, AccessFailureLog, AccessLog):
            for fila in list(modelo.objects.all()):
                if fila.username and fila.username.strip().casefold() == objetivo:
                    fila.delete()
                    extra += 1
        if extra:
            self.stdout.write(self.style.WARNING(
                f"3) {extra} fila(s) adicionales con el username guardado distinto "
                "(mayúsculas/espacios) — también se borraron."))
        else:
            self.stdout.write("3) Sin filas adicionales por diferencias de mayúsculas/espacios.")

        if options["todos"]:
            t_a, _ = AccessAttempt.objects.all().delete()
            t_f, _ = AccessFailureLog.objects.all().delete()
            t_l, _ = AccessLog.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"4) --todos: se limpiaron TODAS las filas de axes en la base — "
                f"{t_a} AccessAttempt, {t_f} AccessFailureLog, {t_l} AccessLog "
                "(de cualquier usuario o IP, no solo el indicado)."))

        self.stdout.write(self.style.SUCCESS(f"=== Estado DESPUÉS para {username!r} ==="))
        self._mostrar_estado(username, AccessAttempt)

        restantes = AccessAttempt.objects.filter(username__iexact=username).count()
        if restantes == 0:
            self.stdout.write(self.style.SUCCESS(
                "Sin filas restantes en AccessAttempt para este usuario. Si el login SIGUE "
                "bloqueado después de esto, el bloqueo no está en la base de datos de axes — "
                "revise el límite de nginx (docker compose restart nginx) o pruebe en una "
                "ventana de incógnito (por si el navegador está mostrando una respuesta en caché)."))
        else:
            self.stdout.write(self.style.ERROR(
                f"Quedan {restantes} fila(s) sin poder borrar — esto no debería pasar; "
                "copie esta salida completa para diagnosticarlo."))

    def _mostrar_estado(self, username, AccessAttempt):
        attempts = AccessAttempt.objects.filter(username__iexact=username)
        if attempts.exists():
            for a in attempts:
                self.stdout.write(
                    f"  AccessAttempt: usuario={a.username!r} ip={a.ip_address!r} "
                    f"fallos={a.failures_since_start} hora={a.attempt_time}")
        else:
            self.stdout.write("  Sin filas en AccessAttempt para este usuario.")
        total = AccessAttempt.objects.count()
        if total:
            self.stdout.write(f"  (Hay {total} fila(s) en AccessAttempt en total, de cualquier usuario.)")

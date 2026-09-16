# -*- coding: utf-8 -*-
"""Restablece cuentas demo, desactiva MFA heredado y desbloquea axes.

Tras migrar a PostgreSQL (pgloader) el usuario admin puede existir con otra
contraseña o MFA activo — este comando deja el login en estado conocido.

Uso:
    python manage.py reparar_acceso_demo
    python manage.py reparar_acceso_demo --probar-http
"""
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.test import RequestFactory

DEMO = (
    ("admin", "SUIIN2026#", "Administrador", True, True),
    ("dinamizador", "Dinamizador2026#", "Dinamizador", False, False),
    ("consultor", "Consultor2026#", "Consultor", False, False),
)


class Command(BaseCommand):
    help = "Restablece admin/consultor/dinamizador, MFA off y desbloqueo axes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--probar-http",
            action="store_true",
            help="Tras reparar, prueba POST /api/auth/login/ como la SPA",
        )

    def handle(self, *args, **options):
        from inventario.espacio_datos import espacio_datos_de
        from inventario.models import PerfilPlataforma

        grupos = {}
        for nombre in ("Consultor", "Dinamizador", "Administrador"):
            grupos[nombre], _ = Group.objects.get_or_create(name=nombre)

        motor = self._motor_db()
        self.stdout.write(f"Base de datos activa: {motor}")

        for username, password, grupo, staff, superuser in DEMO:
            defaults = {
                "is_staff": staff or superuser,
                "is_superuser": superuser,
                "is_active": True,
            }
            user, creado = User.objects.get_or_create(username=username, defaults=defaults)
            user.is_staff = staff or superuser
            user.is_superuser = superuser
            user.is_active = True
            user.set_password(password)
            user.save()
            user.groups.set([grupos[grupo]])
            espacio_datos_de(user)
            perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
            if perfil.mfa_habilitado or perfil.mfa_totp_secreto:
                perfil.mfa_habilitado = False
                perfil.mfa_totp_secreto = ""
                perfil.save(update_fields=["mfa_habilitado", "mfa_totp_secreto"])
            accion = "creado" if creado else "restablecido"
            self.stdout.write(
                self.style.SUCCESS(f"  {username} ({grupo}) {accion} — pass: {password}")
            )

        from django.core.management import call_command

        call_command("desbloquear_login", "admin")

        request = RequestFactory().post("/api/auth/login/", REMOTE_ADDR="127.0.0.1")
        user = authenticate(request, username="admin", password="SUIIN2026#")
        if user is None:
            self.stdout.write(self.style.ERROR(
                "ERROR: authenticate('admin', 'SUIIN2026#') falló tras reparar — "
                "revise DJANGO_DB_ENGINE y que inventario use PostgreSQL."
            ))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("authenticate('admin', 'SUIIN2026#'): OK"))

        if options["probar_http"]:
            self._probar_http()

    def _motor_db(self):
        from django.conf import settings

        engine = settings.DATABASES["default"]["ENGINE"]
        if "postgresql" not in engine:
            self.stdout.write(self.style.ERROR(
                f"Inventario NO usa PostgreSQL ({engine}). "
                "Revise DJANGO_DB_ENGINE=postgresql en .env y reinicie: "
                "./desplegar.sh --postgres --purgar"
            ))
            raise SystemExit(2)
        return engine

    def _probar_http(self):
        from django.test import Client

        client = Client()
        client.get("/api/auth/login/")
        resp = client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "SUIIN2026#"},
            content_type="application/json",
        )
        if resp.status_code != 200:
            self.stdout.write(self.style.ERROR(
                f"POST /api/auth/login/ → {resp.status_code}: {resp.content.decode()[:200]}"
            ))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("POST /api/auth/login/ → 200 (como la SPA)"))

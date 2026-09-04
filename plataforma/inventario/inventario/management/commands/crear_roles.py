"""Crea los grupos de rol del SGSI y usuarios de ejemplo."""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea grupos Consultor/Dinamizador/Administrador y usuarios de ejemplo"

    def handle(self, *args, **o):
        grupos = {}
        for g in ["Consultor", "Dinamizador", "Administrador"]:
            grupos[g], _ = Group.objects.get_or_create(name=g)
        self.stdout.write(self.style.SUCCESS("Grupos creados: Consultor, Dinamizador, Administrador"))

        # Usuarios de ejemplo (cambiar contrasenas en produccion)
        ejemplo = [
            ("consultor", "Consultor2026#", "Consultor", False),
            ("dinamizador", "Dinamizador2026#", "Dinamizador", False),
        ]
        for username, pwd, grupo, staff in ejemplo:
            u, creado = User.objects.get_or_create(username=username, defaults={"is_staff": staff})
            u.set_password(pwd)
            u.is_staff = staff
            u.save()
            u.groups.set([grupos[grupo]])
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"  Usuario '{username}' ({grupo}) {estado} - pass: {pwd}")

        # El superusuario admin queda como Administrador
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            admin.groups.add(grupos["Administrador"])
            self.stdout.write(f"  Superusuario '{admin.username}' agregado a Administrador")

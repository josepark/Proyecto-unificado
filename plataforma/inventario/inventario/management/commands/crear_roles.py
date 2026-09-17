"""Crea los grupos de rol del SGSI y usuarios de ejemplo."""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea grupos Consultor/Dinamizador/Administrador y usuarios de ejemplo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Restablece contraseñas demo aunque el usuario ya exista",
        )

    def handle(self, *args, **options):
        reset = options["reset_passwords"]
        grupos = {}
        for g in ["Consultor", "Dinamizador", "Administrador"]:
            grupos[g], _ = Group.objects.get_or_create(name=g)
        self.stdout.write(self.style.SUCCESS("Grupos creados: Consultor, Dinamizador, Administrador"))

        # Superusuario admin — necesario tras migrar a PostgreSQL con SQLite vacío
        admin, admin_creado = User.objects.get_or_create(
            username="admin",
            defaults={"is_superuser": True, "is_staff": True, "is_active": True},
        )
        if admin_creado or reset:
            admin.set_password("SUIIN2026#")
        elif not admin.check_password("SUIIN2026#"):
            admin.set_password("SUIIN2026#")
            self.stdout.write(self.style.WARNING(
                "  admin existía con otra contraseña — restablecida a SUIIN2026#"
            ))
        admin.is_superuser = True
        admin.is_staff = True
        admin.is_active = True
        admin.save()
        admin.groups.add(grupos["Administrador"])
        from inventario.espacio_datos import espacio_datos_de
        from inventario.modulos_plataforma import modulos_demo_para
        from inventario.models import PerfilPlataforma

        espacio_datos_de(admin)
        perfil, _ = PerfilPlataforma.objects.get_or_create(user=admin)
        perfil.modulos_acceso = modulos_demo_para("admin", "Administrador")
        campos_perfil = ["modulos_acceso"]
        if perfil.mfa_habilitado or perfil.mfa_totp_secreto:
            perfil.mfa_habilitado = False
            perfil.mfa_totp_secreto = ""
            campos_perfil.extend(["mfa_habilitado", "mfa_totp_secreto"])
            self.stdout.write("  MFA desactivado en admin (heredado de SQLite)")
        perfil.save(update_fields=campos_perfil)
        estado_admin = "creado" if admin_creado else ("contraseña restablecida" if reset else "verificado")
        self.stdout.write(
            f"  Usuario 'admin' (Administrador) {estado_admin}"
            + (" — pass: SUIIN2026#" if admin_creado or reset else "")
        )

        # Usuarios de ejemplo (cambiar contrasenas en produccion)
        ejemplo = [
            ("consultor", "Consultor2026#", "Consultor", False),
            ("dinamizador", "Dinamizador2026#", "Dinamizador", False),
        ]
        for username, pwd, grupo, staff in ejemplo:
            u, creado = User.objects.get_or_create(username=username, defaults={"is_staff": staff})
            if creado or reset:
                u.set_password(pwd)
            u.is_staff = staff
            u.is_active = True
            u.save()
            u.groups.set([grupos[grupo]])
            espacio_datos_de(u)
            perfil, _ = PerfilPlataforma.objects.get_or_create(user=u)
            perfil.modulos_acceso = modulos_demo_para(username, grupo)
            perfil.save(update_fields=["modulos_acceso"])
            if creado:
                estado = "creado"
            elif reset:
                estado = "contraseña restablecida"
            else:
                estado = "verificado"
            self.stdout.write(
                f"  Usuario '{username}' ({grupo}) {estado}"
                + (f" — pass: {pwd}" if creado or reset else "")
            )

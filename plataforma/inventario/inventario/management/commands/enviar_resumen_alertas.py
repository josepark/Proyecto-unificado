"""
Envia por correo un resumen de las alertas pendientes del SGSI —
Inventario (fin de soporte, garantias, mantenimiento, hallazgos,
completitud, riesgo cruzado con RBAC) y RBAC (vencimientos proximos,
incumplimientos de MFA, roles con certificacion vencida) — reusando
exactamente los mismos calculos que ya usan las pantallas de Alertas
e Inicio, en vez de definir de nuevo que cuenta como "pendiente".

Antes de este comando, las alertas eran enteramente "pull": solo se
veian si alguien entraba a mirar la pestaña de Alertas o el tablero de
Inicio. Pensado para correr por cron (semanal), igual que ya se hace
con respaldar_plataforma.py:

    0 7 * * 1  cd /ruta/suiin-plataforma && \\
      docker compose exec -T inventario python manage.py enviar_resumen_alertas \\
      >> respaldos/alertas.log 2>&1

Uso:
    python manage.py enviar_resumen_alertas
    python manage.py enviar_resumen_alertas --solo-si-hay-criticas
    python manage.py enviar_resumen_alertas --destinatarios correo1@x.com,correo2@x.com
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from inventario.integracion_rbac import inicio_rbac
from inventario.views import calcular_alertas

MAX_ITEMS_POR_GRUPO = 8


class Command(BaseCommand):
    help = "Envia por correo el resumen semanal de alertas del SGSI (Inventario + RBAC)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--destinatarios",
            help="Correos separados por coma. Si no se indica, usa DJANGO_ALERTAS_EMAIL del .env.",
        )
        parser.add_argument(
            "--solo-si-hay-criticas", action="store_true",
            help="No envía nada si no hay alertas crít/alto ni vencimientos próximos en RBAC "
                 "(por defecto SÍ envía siempre, como confirmación de que el resumen sigue vivo).",
        )

    def handle(self, *args, **opts):
        destinatarios = (
            [d.strip() for d in opts["destinatarios"].split(",") if d.strip()]
            if opts.get("destinatarios") else settings.ALERTAS_EMAIL_DESTINATARIOS
        )
        if not destinatarios:
            self.stdout.write(self.style.WARNING(
                "No hay destinatarios configurados (DJANGO_ALERTAS_EMAIL en .env, o --destinatarios). "
                "No se envía nada."))
            return

        alertas = calcular_alertas()
        rbac = inicio_rbac()  # None si RBAC no responde — no debe romper el envío del lado Inventario

        for g in alertas["grupos"]:
            g["items_mostrados"] = g["items"][:MAX_ITEMS_POR_GRUPO]
            g["items_restantes"] = len(g["items"]) - len(g["items_mostrados"])

        rbac_pendientes = 0
        if rbac:
            rbac_pendientes = len(rbac["proximos_vencimientos"]) + len(rbac["alertas_mfa"])

        if opts["solo_si_hay_criticas"] and alertas["alertas_criticas"] == 0 and rbac_pendientes == 0:
            self.stdout.write("Sin alertas críticas ni vencimientos en RBAC — no se envía correo (--solo-si-hay-criticas).")
            return

        contexto = {
            "fecha": timezone.now().strftime("%Y-%m-%d"),
            "alertas": alertas,
            "rbac": rbac,
            "rbac_pendientes": rbac_pendientes,
        }
        asunto = (
            f"[SUIIN-SGSI] Resumen semanal — {alertas['alertas_criticas']} alerta(s) crítica(s)/alta(s)"
            + (f", {rbac_pendientes} pendiente(s) en RBAC" if rbac_pendientes else "")
        )
        texto = render_to_string("correo/resumen_alertas.txt", contexto)
        html = render_to_string("correo/resumen_alertas.html", contexto)

        correo = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, destinatarios)
        correo.attach_alternative(html, "text/html")
        enviados = correo.send()

        if enviados:
            self.stdout.write(self.style.SUCCESS(
                f"Resumen enviado a {', '.join(destinatarios)} "
                f"({alertas['total_alertas']} alerta(s) de Inventario, {rbac_pendientes} de RBAC)."))
        else:
            self.stdout.write(self.style.ERROR("El backend de correo no confirmó el envío."))

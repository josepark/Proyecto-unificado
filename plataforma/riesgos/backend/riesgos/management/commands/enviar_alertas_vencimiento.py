# -*- coding: utf-8 -*-
"""
enviar_alertas_vencimiento — Envía un resumen por correo de acciones de tratamiento
y riesgos por activo vencidos o próximos a vencer.

Uso:
    python manage.py enviar_alertas_vencimiento
    python manage.py enviar_alertas_vencimiento --destinatarios jose@cric.org.co,otro@cric.org.co

Pensado para correr periódicamente (cron, Celery beat, systemd timer) — no envía
nada si no hay vencimientos que reportar, para no generar ruido diario.

Ejemplo de crontab (todos los días laborales a las 8:00 a.m.):
    0 8 * * 1-5 cd /ruta/backend && venv/bin/python manage.py enviar_alertas_vencimiento
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

from riesgos.models import AccionTratamiento, RiesgoActivo, RiesgoContextual


class Command(BaseCommand):
    help = "Envía un resumen por correo de vencimientos (acciones de tratamiento y riesgos por activo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destinatarios", type=str, default=None,
            help="Lista separada por comas. Si se omite, usa ALERTAS_EMAIL_DESTINATARIOS del .env.")
        parser.add_argument(
            "--forzar", action="store_true",
            help="Envía el correo aunque no haya vencimientos (útil para probar la configuración de correo).")

    def handle(self, *args, **options):
        destinatarios = (
            [d.strip() for d in options["destinatarios"].split(",") if d.strip()]
            if options["destinatarios"] else settings.ALERTAS_EMAIL_DESTINATARIOS
        )
        if not destinatarios:
            self.stderr.write(self.style.ERROR(
                "No hay destinatarios configurados. Use --destinatarios o defina "
                "ALERTAS_EMAIL_DESTINATARIOS en el .env."))
            return

        acciones = AccionTratamiento.objects.exclude(fecha_limite=None).exclude(
            estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"]).select_related("plan")
        riesgos = RiesgoActivo.objects.exclude(fecha_objetivo=None).exclude(
            estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"]).select_related("activo")
        riesgos_ctx = RiesgoContextual.objects.exclude(fecha_limite=None).exclude(
            estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"])

        acciones_vencidas = [a for a in acciones if a.esta_vencida]
        acciones_por_vencer = [a for a in acciones if a.por_vencer]
        riesgos_vencidos = [r for r in riesgos if r.esta_vencido]
        riesgos_por_vencer = [r for r in riesgos if r.por_vencer]
        ctx_vencidos = [r for r in riesgos_ctx if r.esta_vencido]
        ctx_por_vencer = [r for r in riesgos_ctx if r.por_vencer]

        total = (len(acciones_vencidas) + len(acciones_por_vencer) + len(riesgos_vencidos)
                 + len(riesgos_por_vencer) + len(ctx_vencidos) + len(ctx_por_vencer))
        if total == 0 and not options["forzar"]:
            self.stdout.write("Sin vencimientos pendientes — no se envía correo.")
            return

        asunto = f"SUIIN-SGSI · {len(acciones_vencidas) + len(riesgos_vencidos) + len(ctx_vencidos)} vencido(s), " \
                 f"{len(acciones_por_vencer) + len(riesgos_por_vencer) + len(ctx_por_vencer)} por vencer"
        cuerpo = self._construir_cuerpo(
            acciones_vencidas, acciones_por_vencer, riesgos_vencidos, riesgos_por_vencer,
            ctx_vencidos, ctx_por_vencer)

        send_mail(
            subject=asunto, message=cuerpo, from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios, fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Correo enviado a {', '.join(destinatarios)} ({total} ítem(s))."))

    def _construir_cuerpo(self, acciones_vencidas, acciones_por_vencer, riesgos_vencidos, riesgos_por_vencer,
                           ctx_vencidos, ctx_por_vencer):
        lineas = ["Resumen de vencimientos — SUIIN-SGSI-RIESGOS", ""]

        if acciones_vencidas:
            lineas.append(f"ACCIONES DE TRATAMIENTO VENCIDAS ({len(acciones_vencidas)}):")
            for a in acciones_vencidas:
                lineas.append(f"  · {a.id_riesgo} ({a.plan.referencia}) — venció hace "
                               f"{abs(a.dias_para_vencer)} día(s) — {a.descripcion_riesgo[:80]}")
            lineas.append("")

        if riesgos_vencidos:
            lineas.append(f"RIESGOS POR ACTIVO VENCIDOS ({len(riesgos_vencidos)}):")
            for r in riesgos_vencidos:
                lineas.append(f"  · {r.id_riesgo} ({r.activo.id_activo}) — venció hace "
                               f"{abs(r.dias_para_vencer)} día(s)")
            lineas.append("")

        if ctx_vencidos:
            lineas.append(f"RIESGOS CONTEXTUALES VENCIDOS ({len(ctx_vencidos)}):")
            for r in ctx_vencidos:
                lineas.append(f"  · {r.id_riesgo_contextual} — venció hace "
                               f"{abs(r.dias_para_vencer)} día(s) — {r.escenario_amenaza[:80]}")
            lineas.append("")

        if acciones_por_vencer:
            lineas.append(f"ACCIONES DE TRATAMIENTO POR VENCER EN 7 DÍAS ({len(acciones_por_vencer)}):")
            for a in acciones_por_vencer:
                lineas.append(f"  · {a.id_riesgo} ({a.plan.referencia}) — vence en "
                               f"{a.dias_para_vencer} día(s) — {a.descripcion_riesgo[:80]}")
            lineas.append("")

        if riesgos_por_vencer:
            lineas.append(f"RIESGOS POR ACTIVO POR VENCER EN 7 DÍAS ({len(riesgos_por_vencer)}):")
            for r in riesgos_por_vencer:
                lineas.append(f"  · {r.id_riesgo} ({r.activo.id_activo}) — vence en {r.dias_para_vencer} día(s)")
            lineas.append("")

        if ctx_por_vencer:
            lineas.append(f"RIESGOS CONTEXTUALES POR VENCER EN 7 DÍAS ({len(ctx_por_vencer)}):")
            for r in ctx_por_vencer:
                lineas.append(f"  · {r.id_riesgo_contextual} — vence en "
                               f"{r.dias_para_vencer} día(s) — {r.escenario_amenaza[:80]}")
            lineas.append("")

        if not any([acciones_vencidas, acciones_por_vencer, riesgos_vencidos, riesgos_por_vencer,
                    ctx_vencidos, ctx_por_vencer]):
            lineas.append("Sin vencimientos pendientes en este momento.")

        return "\n".join(lineas)

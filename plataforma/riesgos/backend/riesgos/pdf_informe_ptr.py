# -*- coding: utf-8 -*-
"""Informe PDF completo de un Plan de Tratamiento de Riesgos (PTR)."""
import io

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .pdf_hoja_riesgo import VERDE, GRIS, _tabla_encabezado, _tabla_lista

_styles = getSampleStyleSheet()


def _estilos():
    return {
        "h": ParagraphStyle("h", parent=_styles["Title"], textColor=VERDE, fontSize=16),
        "sub": ParagraphStyle("sub", parent=_styles["Normal"], textColor=GRIS, fontSize=9),
        "normal": ParagraphStyle("normal9", parent=_styles["Normal"], fontSize=8.5, leading=11),
    }


def generar_informe_ptr_pdf(plan):
    buf = io.BytesIO()
    st = _estilos()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    story.append(Paragraph("Plan de Tratamiento de Riesgos", st["h"]))
    story.append(Paragraph(plan.titulo, st["sub"]))
    story.append(Spacer(1, 0.4 * cm))

    meta = [
        ["Referencia", plan.referencia, "Estado", plan.get_estado_plan_display()],
        ["Campaña Red Team", plan.campana_red_team.nombre, "Host", plan.campana_red_team.host_ip],
        ["Fecha emisión", str(plan.fecha_emision), "Clasificación", plan.clasificacion_documento],
        ["Herramientas", plan.herramientas or "—", "Avance global", f"{plan.porcentaje_avance_global}%"],
    ]
    story.append(_tabla_encabezado(meta, [3.2 * cm, 5.5 * cm, 3.2 * cm, 5.5 * cm]))
    story.append(Spacer(1, 0.5 * cm))

    acciones = list(
        plan.acciones.select_related("plan").prefetch_related("controles_iso_vinculados").order_by("fase", "id_riesgo")
    )
    filas = [["ID", "Fase", "Nivel", "Estado", "Avance", "Responsable", "Descripción"]]
    for a in acciones:
        filas.append([
            a.id_riesgo,
            a.get_fase_display(),
            a.get_nivel_riesgo_display(),
            a.get_estado_display(),
            f"{a.porcentaje_avance}%",
            a.responsable or "—",
            Paragraph((a.descripcion_riesgo or "")[:280], st["normal"]),
        ])
    story.append(Paragraph(
        "Acciones de tratamiento",
        ParagraphStyle("h2", parent=st["normal"], textColor=VERDE, fontSize=12),
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_tabla_lista(
        filas,
        [1.4 * cm, 2.4 * cm, 1.6 * cm, 2.2 * cm, 1.4 * cm, 2.4 * cm, 6.6 * cm],
        "Sin acciones registradas en este plan.",
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"Generado {timezone.localtime().strftime('%Y-%m-%d %H:%M')} · SUIIN-SGSI / CRIC",
        st["sub"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf

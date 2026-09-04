# -*- coding: utf-8 -*-
"""
Hoja de riesgo en PDF por activo — equivalente en riesgos a la hojavida.pdf que
ya tiene el Inventario, con el mismo lenguaje visual (misma paleta institucional)
para que ambos documentos se sientan de la misma familia dentro de la Plataforma
SUIIN, aunque vengan de servicios distintos.

A diferencia de hojavida.pdf (bitácora de eventos del activo en sí), esta hoja
está centrada en el RIESGO: vulnerabilidades, riesgos evaluados, acciones de
tratamiento vinculadas, evidencia recolectada y qué controles ISO 27001 quedan
cubiertos — es el documento que un auditor pediría ver junto al activo.
"""
import io

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import AccionTratamiento, Evidencia

VERDE = colors.HexColor("#0d2b23")
GRIS = colors.HexColor("#5a6b64")
FONDO_CLARO = colors.HexColor("#eef4f1")
GRID = colors.HexColor("#d9e2dd")
FILA_ALTERNA = colors.HexColor("#f4f6f5")

_styles = getSampleStyleSheet()


def _estilos():
    return {
        "h": ParagraphStyle("h", parent=_styles["Title"], textColor=VERDE, fontSize=16),
        "h2": ParagraphStyle("h2", parent=_styles["Heading2"], textColor=VERDE, fontSize=12,
                              spaceBefore=6, spaceAfter=4),
        "sub": ParagraphStyle("sub", parent=_styles["Normal"], textColor=GRIS, fontSize=9),
        "normal": ParagraphStyle("normal9", parent=_styles["Normal"], fontSize=8.5, leading=11),
        "vacio": ParagraphStyle("vacio", parent=_styles["Normal"], fontSize=8.5,
                                 textColor=GRIS, leading=11),
    }


def _tabla_encabezado(datos, col_widths):
    st = _estilos()
    datos_envueltos = [[Paragraph(str(celda), st["normal"]) for celda in fila] for fila in datos]
    t = Table(datos_envueltos, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("BACKGROUND", (0, 0), (0, -1), FONDO_CLARO),
        ("BACKGROUND", (2, 0), (2, -1), FONDO_CLARO),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _tabla_lista(filas_con_encabezado, col_widths, sin_datos_texto):
    st = _estilos()
    if len(filas_con_encabezado) == 1:
        return Paragraph(sin_datos_texto, st["vacio"])
    encabezado_blanco = ParagraphStyle("enc", parent=st["normal"], textColor=colors.white)
    filas_envueltas = [
        [Paragraph(str(c), encabezado_blanco) for c in filas_con_encabezado[0]]
    ] + [
        [c if isinstance(c, Paragraph) else Paragraph(str(c), st["normal"]) for c in fila]
        for fila in filas_con_encabezado[1:]
    ]
    t = Table(filas_envueltas, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FILA_ALTERNA]),
    ]))
    return t


def _evidencia_del_activo(activo):
    """Evidencia adjunta directamente al activo, más la de sus vulnerabilidades y
    riesgos por activo — para que la hoja de riesgo muestre toda la evidencia
    recolectada en el recorrido de este activo, no solo la colgada del registro
    del activo en sí."""
    ct_activo = ContentType.objects.get_for_model(activo.__class__)
    ct_vuln = ContentType.objects.get(app_label="riesgos", model="vulnerabilidad")
    ct_riesgo = ContentType.objects.get(app_label="riesgos", model="riesgoactivo")

    ids_vuln = list(activo.vulnerabilidades.values_list("id", flat=True))
    ids_riesgo = list(activo.riesgos_agregados.values_list("id", flat=True))

    qs = Evidencia.objects.filter(
        Q(content_type=ct_activo, object_id=activo.id)
        | Q(content_type=ct_vuln, object_id__in=ids_vuln)
        | Q(content_type=ct_riesgo, object_id__in=ids_riesgo)
    ).select_related("content_type", "subido_por").order_by("-creado_en")
    return list(qs)


def generar_hoja_riesgo_pdf(activo):
    """Devuelve un BytesIO con el PDF ya construido para el activo dado."""
    st = _estilos()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Hoja de riesgo {activo.id_activo}",
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    el = [
        Paragraph("Hoja de Riesgo del Activo", st["h"]),
        Paragraph("SUIIN-SGSI-RIESGOS · SUIIN — CRIC · ISO/IEC 27001:2022", st["sub"]),
        Spacer(1, 0.4 * cm),
    ]

    # --- Identidad del activo ---
    datos = [
        ["ID", activo.id_activo, "Nombre", activo.nombre],
        ["Tipo", activo.tipo or "—", "IP principal", activo.ip_principal or "—"],
        ["Clasificación", activo.get_clasificacion_si_display(), "Valor (C+I+D)", str(activo.valor)],
        ["Riesgo actual", activo.get_riesgo_matriz_display(), "Cobertura de escaneo", activo.get_cobertura_display()],
    ]
    if activo.inventario_id:
        datos.append(["Vínculo", f"Inventario #{activo.inventario_id}", "Afectado Red Team",
                       "Sí" if activo.afectado_red_team else "No"])
    el.append(_tabla_encabezado(datos, [3 * cm, 5.5 * cm, 3.3 * cm, 5.2 * cm]))
    el.append(Spacer(1, 0.5 * cm))

    # --- Vulnerabilidades ---
    vulns = activo.vulnerabilidades.all().order_by("-probabilidad", "-impacto")
    el.append(Paragraph(f"Vulnerabilidades ({vulns.count()})", st["h2"]))
    filas = [["Hallazgo", "Severidad OV", "P×I=Score", "Nivel", "Estado"]]
    for v in vulns:
        filas.append([
            Paragraph(v.nombre_vulnerabilidad[:90], st["normal"]),
            v.severidad_ov or "—",
            f"{v.probabilidad or '—'}×{v.impacto or '—'}={v.score or '—'}",
            v.get_nivel_riesgo_display(),
            v.get_estado_display(),
        ])
    el.append(_tabla_lista(filas, [7.5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm, 2.5 * cm],
                            "Sin vulnerabilidades registradas para este activo."))
    el.append(Spacer(1, 0.4 * cm))

    # --- Riesgos por activo ---
    riesgos = activo.riesgos_agregados.all().order_by("-probabilidad", "-impacto")
    el.append(Paragraph(f"Riesgos evaluados ({riesgos.count()})", st["h2"]))
    filas = [["ID", "Clasificación", "P×I=Score", "Nivel", "Estado", "Responsable"]]
    for r in riesgos:
        filas.append([
            r.id_riesgo, r.get_clasificacion_display(),
            f"{r.probabilidad}×{r.impacto}={r.score}", r.get_nivel_riesgo_display(),
            r.get_estado_display(), r.responsable_sugerido or "—",
        ])
    el.append(_tabla_lista(filas, [2.3 * cm, 2.8 * cm, 2.5 * cm, 2 * cm, 2.6 * cm, 4.8 * cm],
                            "Sin riesgos evaluados para este activo."))
    el.append(Spacer(1, 0.4 * cm))

    # --- Acciones de tratamiento vinculadas ---
    # Tres caminos de vínculo, todos válidos: (a) origen fino a una
    # vulnerabilidad o riesgo por activo, cuando la acción se generó desde el
    # botón "Generar acción" sobre un hallazgo específico de este activo;
    # (b) por campaña de Red Team, cuando la acción viene de un PTR importado
    # directo del Excel (sin ese vínculo campo a campo, pero sí asociado al
    # mismo host mediante el plan); (c) origen en un riesgo contextual que
    # tenga este activo entre sus activos_relacionados — antes esta tercera
    # vía no existía en absoluto (RiesgoContextual no tenía forma de generar
    # una acción trazada), así que ningún activo mostraba nunca estas
    # acciones aquí, aunque el riesgo contextual sí lo mencionara.
    filtro_acciones = (
        Q(origen_vulnerabilidad__activo=activo)
        | Q(origen_riesgo_activo__activo=activo)
        | Q(origen_riesgo_contextual__activos_relacionados=activo)
    )
    if activo.campana_red_team_id:
        filtro_acciones |= Q(plan__campana_red_team=activo.campana_red_team)
    acciones = AccionTratamiento.objects.filter(filtro_acciones).select_related(
        "plan").prefetch_related("controles_iso_vinculados").distinct().order_by(
        "-probabilidad", "-impacto")
    el.append(Paragraph(f"Acciones de tratamiento vinculadas ({acciones.count()})", st["h2"]))
    filas = [["ID", "Plan", "Descripción", "Estado", "Avance", "Controles ISO vinculados"]]
    for a in acciones:
        controles = ", ".join(c.codigo for c in a.controles_iso_vinculados.all()) or "—"
        filas.append([
            a.id_riesgo, a.plan.referencia,
            Paragraph(a.descripcion_riesgo[:80], st["normal"]),
            a.get_estado_display(), f"{a.porcentaje_avance}%", controles,
        ])
    el.append(_tabla_lista(filas, [1.8 * cm, 2.8 * cm, 5.5 * cm, 2.2 * cm, 1.7 * cm, 2.6 * cm],
                            "Sin acciones de tratamiento generadas todavía a partir de los "
                            "hallazgos de este activo."))
    el.append(Spacer(1, 0.4 * cm))

    # --- Evidencia adjunta (del activo y de sus vulnerabilidades/riesgos) ---
    evidencias = _evidencia_del_activo(activo)
    el.append(Paragraph(f"Evidencia adjunta ({len(evidencias)})", st["h2"]))
    filas = [["Archivo", "Tipo", "Vinculada a", "Descripción", "Subido por", "Fecha"]]
    for e in evidencias:
        filas.append([
            Paragraph(e.nombre_original, st["normal"]), e.get_tipo_archivo_display() or "—",
            e.content_type.model, Paragraph(e.descripcion or "—", st["normal"]),
            e.subido_por.username if e.subido_por else "—",
            e.creado_en.strftime("%Y-%m-%d"),
        ])
    el.append(_tabla_lista(filas, [3.5 * cm, 1.8 * cm, 2.2 * cm, 4 * cm, 2.5 * cm, 2 * cm],
                            "Sin evidencia adjunta a este activo ni a sus hallazgos."))

    el.append(Spacer(1, 0.6 * cm))
    el.append(Paragraph(
        f"Generado el {timezone.now().strftime('%Y-%m-%d %H:%M')} desde SUIIN-SGSI-RIESGOS.",
        st["sub"]))

    doc.build(el)
    buf.seek(0)
    return buf

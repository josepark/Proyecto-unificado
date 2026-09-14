"""
Reporte consolidado para auditoría — antes, preparar evidencia para una
auditoría externa o para la Junta significaba combinar a mano varias
exportaciones parciales (Excel del inventario, CSV de la matriz de RBAC,
capturas de pantalla del panel ejecutivo). Este módulo junta en un solo
PDF los datos que ya calcula cada pantalla por separado — no inventa
ningún cálculo nuevo, solo los presenta juntos: Declaración de
Aplicabilidad dinámica (cobertura de controles), matriz de riesgo,
alertas críticas del Inventario, y cumplimiento MFA / roles críticos /
vencimientos próximos de RBAC.
"""
import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from .integracion_rbac import inicio_rbac

VERDE = colors.HexColor("#0d2b23")
DORADO = colors.HexColor("#9a7d1f")
GRIS = colors.HexColor("#5a6b64")
BORDE = colors.HexColor("#d9e2dd")
FILA_ALT = colors.HexColor("#f2f2f2")
NIVEL_COLOR = {
    "CRIT": colors.HexColor("#b3261e"), "ALTO": colors.HexColor("#c9622a"),
    "MED": colors.HexColor("#c9a94e"), "BAJO": colors.HexColor("#5f6a64"),
    "SIN": colors.HexColor("#9aa39c"),
}
NIVEL_NOMBRE = {"CRIT": "Crítico", "ALTO": "Alto", "MED": "Medio",
               "BAJO": "Bajo", "SIN": "Sin valorar"}

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_styles["Title"], textColor=VERDE, fontSize=20, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_styles["Heading1"], textColor=VERDE, fontSize=14,
                    spaceBefore=16, spaceAfter=8, borderColor=BORDE, borderWidth=0,
                    borderPadding=0)
SUB = ParagraphStyle("Sub", parent=_styles["Normal"], textColor=GRIS, fontSize=9)
NORMAL = ParagraphStyle("N", parent=_styles["Normal"], fontSize=9, leading=12)
NOTA = ParagraphStyle("Nota", parent=_styles["Normal"], fontSize=8, textColor=GRIS,
                      spaceBefore=6)


def _tabla(cabeceras, filas, anchos, resaltar_col=None):
    data = [cabeceras] + filas
    t = Table(data, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), FILA_ALT))
    t.setStyle(TableStyle(estilo))
    return t


def _kpi_tabla(pares):
    """Tabla de dos columnas valor/etiqueta, para bloques de KPIs.
    `pares` es una lista de (valor, etiqueta)."""
    filas = [[Paragraph(f"<b>{v}</b>", NORMAL), Paragraph(str(k), SUB)] for v, k in pares]
    t = Table(filas, colWidths=[2.4 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def generar_pdf():
    from .views import calcular_alertas, calcular_cobertura, calcular_panel_ejecutivo, calcular_riesgos

    panel = calcular_panel_ejecutivo()
    cobertura = calcular_cobertura()
    riesgos = calcular_riesgos()
    alertas = calcular_alertas()
    rbac = inicio_rbac()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Reporte consolidado SUIIN-SGSI",
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            # Sin comprimir: el reporte es pequeño y bajo demanda
                            # (no se almacena ni se envía masivamente), y así su
                            # contenido queda verificable en texto plano — tanto
                            # para las pruebas automatizadas como para cualquier
                            # revisión manual del PDF sin herramientas adicionales.
                            pageCompression=0)
    el = []

    # --- Portada ---
    el.append(Spacer(1, 4 * cm))
    el.append(Paragraph("Reporte Consolidado del SGSI", H1))
    el.append(Paragraph("SUIIN · Consejo Regional Indígena del Cauca (CRIC)", SUB))
    el.append(Spacer(1, 0.3 * cm))
    el.append(Paragraph(
        "Declaración de Aplicabilidad, riesgos, alertas operativas y cumplimiento de "
        "control de acceso — ISO/IEC 27001:2022", SUB))
    el.append(Spacer(1, 1 * cm))
    ahora = timezone.localtime(timezone.now())
    el.append(Paragraph(f"Generado: {ahora:%Y-%m-%d %H:%M}", NORMAL))
    el.append(PageBreak())

    # --- Resumen ejecutivo ---
    el.append(Paragraph("1. Resumen ejecutivo", H2))
    comp = panel["completitud"]
    el.append(_kpi_tabla([
        (panel["total_activos"], "Activos registrados en el Inventario"),
        (f"{comp['valoracion_cid']}%", "Con valoración C-I-D completa"),
        (f"{comp['propietario']}%", "Con propietario asignado"),
        (f"{comp['con_control']}%", "Con al menos un control ISO aplicado"),
        (f"{panel['cobertura_controles']['pct']}%",
         f"Cobertura de controles ISO 27002 ({panel['cobertura_controles']['usados']}/{panel['cobertura_controles']['total']})"),
        (panel["datos_personales"], "Activos que procesan datos personales (Ley 1581/2012)"),
        (panel["cambios_30dias"], "Cambios registrados en los últimos 30 días"),
    ]))
    if rbac:
        el.append(Spacer(1, 6))
        el.append(_kpi_tabla([
            (rbac["stats"]["roles"], "Roles definidos en la Matriz RBAC"),
            (rbac["stats"]["sistemas"], "Sistemas / recursos cubiertos"),
            (rbac["stats"]["accesos"], "Accesos definidos en la matriz"),
            (f"{rbac['mfa_pct']}%", f"Cumplimiento MFA ({rbac['mfa_ok']}/{rbac['mfa_total']})"),
        ]))
    else:
        el.append(Paragraph("No se pudo consultar RBAC al generar este reporte.", NOTA))

    vinc = panel.get("vinculacion") or {}
    if vinc.get("disponible"):
        el.append(Spacer(1, 6))
        pct = round(vinc["vinculados"] / vinc["total_inventario"] * 100, 1) if vinc["total_inventario"] else 100
        el.append(_kpi_tabla([
            (f"{vinc['vinculados']}/{vinc['total_inventario']} ({pct}%)",
             "Activos vinculados Inventario ↔ Gestión de Riesgos"),
            (vinc["sin_espejo_riesgos"], "Activos del Inventario sin espejo en Riesgos"),
            (vinc["huerfanos_riesgos"], "Activos huérfanos solo en Riesgos"),
        ]))
        if vinc["sin_espejo_riesgos"] or vinc["huerfanos_riesgos"]:
            el.append(Paragraph(
                "Ejecute sincronizar_activos_inventario o ./desplegar.sh --sincronizar para "
                "alinear ambos módulos.", NOTA))
    else:
        el.append(Spacer(1, 6))
        el.append(Paragraph("No se pudo consultar el estado de sincronización con Riesgos.", NOTA))

    # --- Declaración de Aplicabilidad ---
    el.append(Paragraph("2. Declaración de Aplicabilidad (controles ISO/IEC 27002:2022)", H2))
    el.append(Paragraph(
        f"{cobertura['controles_usados']} de {cobertura['total_controles']} controles del catálogo están "
        f"aplicados a al menos un activo. {cobertura['activos_con_control']} de {cobertura['total_activos']} "
        f"activos ({cobertura['cobertura_activos_pct']}%) tienen al menos un control asociado.", NORMAL))
    el.append(Spacer(1, 6))
    filas_ctrl = [[c["codigo"], Paragraph(c["descripcion"][:90], NORMAL), str(c["num_activos"])]
                 for c in cobertura["detalle"][:30]]
    el.append(_tabla(["Control", "Descripción", "Activos"], filas_ctrl,
                     [2.3 * cm, 10.5 * cm, 1.6 * cm]))
    if len(cobertura["detalle"]) > 30:
        el.append(Paragraph(
            f"... y {len(cobertura['detalle']) - 30} control(es) más — ver la pestaña Riesgos "
            "para el listado completo.", NOTA))
    el.append(PageBreak())

    # --- Riesgos ---
    el.append(Paragraph("3. Matriz de riesgo", H2))
    el.append(Paragraph(
        f"{len(riesgos['activos']) - riesgos['sin_valorar']} de {len(riesgos['activos'])} activos tienen "
        "riesgo calculado (probabilidad × impacto, ISO/IEC 27005).", NORMAL))
    el.append(Spacer(1, 6))
    filas_nivel = [[NIVEL_NOMBRE.get(n, n), str(c)]
                  for n, c in sorted(riesgos["por_nivel"].items(),
                                     key=lambda x: -{"CRIT": 5, "ALTO": 4, "MED": 3, "BAJO": 2, "SIN": 1}.get(x[0], 0))]
    el.append(_tabla(["Nivel", "Activos"], filas_nivel, [6 * cm, 3 * cm]))
    el.append(Spacer(1, 10))
    el.append(Paragraph("Activos de mayor riesgo (top 15)", ParagraphStyle(
        "H3", parent=NORMAL, fontSize=10, textColor=DORADO, fontName="Helvetica-Bold",
        spaceBefore=6, spaceAfter=4)))
    top = [a for a in riesgos["activos"] if a["score"]][:15]
    filas_top = [[a["id_activo"], Paragraph(a["nombre"][:55], NORMAL),
                 str(a["score"]), NIVEL_NOMBRE.get(a["nivel"], a["nivel"])] for a in top]
    el.append(_tabla(["ID", "Activo", "Score", "Nivel"], filas_top,
                     [2 * cm, 8.5 * cm, 1.8 * cm, 2.1 * cm]))
    el.append(PageBreak())

    # --- Alertas críticas ---
    el.append(Paragraph("4. Alertas operativas del Inventario", H2))
    el.append(Paragraph(
        f"{alertas['total_alertas']} alerta(s) pendientes ({alertas['alertas_criticas']} "
        "crítica(s)/alta(s)) al momento de generar este reporte.", NORMAL))
    el.append(Spacer(1, 6))
    if not alertas["grupos"]:
        el.append(Paragraph("Sin alertas pendientes.", NORMAL))
    for g in alertas["grupos"]:
        bloque = [Paragraph(f"{g['titulo']} ({len(g['items'])})", ParagraphStyle(
            "H3b", parent=NORMAL, fontSize=10, textColor=DORADO, fontName="Helvetica-Bold",
            spaceBefore=8, spaceAfter=3))]
        filas_g = [[i["id_activo"], Paragraph(f"{i['nombre']}: {i['detalle']}"[:110], NORMAL),
                   i["severidad"].upper()] for i in g["items"][:10]]
        bloque.append(_tabla(["ID", "Detalle", "Sev."], filas_g, [2 * cm, 10.5 * cm, 1.7 * cm]))
        if len(g["items"]) > 10:
            bloque.append(Paragraph(f"... y {len(g['items']) - 10} más.", NOTA))
        el.append(KeepTogether(bloque))
    el.append(PageBreak())

    # --- RBAC ---
    el.append(Paragraph("5. Matriz de Control de Acceso (RBAC)", H2))
    if not rbac:
        el.append(Paragraph("No se pudo consultar RBAC al generar este reporte — "
                            "verificar que el servicio esté disponible.", NORMAL))
    else:
        el.append(Paragraph("Roles críticos (con accesos de nivel Administrador)", ParagraphStyle(
            "H3c", parent=NORMAL, fontSize=10, textColor=DORADO, fontName="Helvetica-Bold",
            spaceBefore=4, spaceAfter=4)))
        filas_crit = [[r["abreviatura"], Paragraph(r["denominacion"], NORMAL), str(r["n_admin"])]
                     for r in rbac["criticos"]]
        el.append(_tabla(["Rol", "Denominación", "Sistemas nivel A"], filas_crit,
                         [2.3 * cm, 9.5 * cm, 2.4 * cm]))

        el.append(Paragraph("Usuarios con MFA exigido pero no activo", ParagraphStyle(
            "H3d", parent=NORMAL, fontSize=10, textColor=DORADO, fontName="Helvetica-Bold",
            spaceBefore=12, spaceAfter=4)))
        if rbac["alertas_mfa"]:
            filas_mfa = [[a["nombre"], a["rol"]] for a in rbac["alertas_mfa"]]
            el.append(_tabla(["Usuario", "Rol"], filas_mfa, [8 * cm, 6.2 * cm]))
        else:
            el.append(Paragraph("Ninguno — cumplimiento del 100% entre los usuarios que lo requieren.", NORMAL))

        el.append(Paragraph(f"Vencimientos en los próximos {rbac['dias_alerta']} días", ParagraphStyle(
            "H3e", parent=NORMAL, fontSize=10, textColor=DORADO, fontName="Helvetica-Bold",
            spaceBefore=12, spaceAfter=4)))
        if rbac["proximos_vencimientos"]:
            filas_v = [[v["tipo"], v["nombre"], v["contexto"], v["fecha_fin"], str(v["dias"])]
                      for v in rbac["proximos_vencimientos"]]
            el.append(_tabla(["Tipo", "Persona", "Contexto", "Vence", "Días"], filas_v,
                             [3 * cm, 4 * cm, 3.2 * cm, 2.5 * cm, 1.5 * cm]))
        else:
            el.append(Paragraph("Sin vencimientos próximos.", NORMAL))

    el.append(Spacer(1, 20))
    el.append(Paragraph(
        "Documento generado automáticamente por la Plataforma Soluciones SUIIN a partir de "
        "los datos vigentes del Inventario de Activos SGSI y la Matriz RBAC al momento de "
        "su generación. No sustituye los documentos formales del SGSI (SoA, PTR, políticas).",
        NOTA))

    doc.build(el)
    buf.seek(0)
    return buf.read()

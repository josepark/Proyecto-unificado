#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — validaciones y constantes compartidas por la API REST."""
import csv
import io
from datetime import datetime

ESTADOS_USUARIO = ("Activo", "Temporal", "Suspendido", "Revocado")
RIESGOS_ATTACK = ("Alto", "Medio", "Bajo")
CLASIFICACIONES = ("Altamente Confidencial", "Confidencial", "Interna", "Pública")
DIAS_ALERTA_VENCIMIENTO = 7

DIAS_REVISION = {"Mensual": 30, "Trimestral": 90, "Semestral": 180, "Anual": 365}
_CASE_DIAS_REVISION = " ".join(
    f"WHEN '{k}' THEN {v}" for k, v in DIAS_REVISION.items())
SQL_REVISION_VENCIDA = f"""CASE
    WHEN r.ultima_revision IS NULL THEN 1
    WHEN date(r.ultima_revision, '+' ||
         (CASE r.revision_periodica {_CASE_DIAS_REVISION} ELSE 90 END) ||
         ' days') < date('now') THEN 1
    ELSE 0 END"""


def _fecha_valida(txt):
    if not txt:
        return True
    try:
        datetime.strptime(txt, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validar_datos_rol(f, c):
    codigo = f.get("codigo", "").strip()
    abreviatura = f.get("abreviatura", "").strip().upper()
    denominacion = f.get("denominacion", "").strip()
    if not codigo or not abreviatura or not denominacion:
        return None, "El código, la abreviatura y la denominación son obligatorios."
    try:
        grupo_id = int(f.get("grupo_id"))
    except (TypeError, ValueError):
        return None, "Seleccione un grupo de rol válido."
    if not c.execute("SELECT 1 FROM grupo_rol WHERE id=?", (grupo_id,)).fetchone():
        return None, "Seleccione un grupo de rol válido."
    riesgo = f.get("riesgo_attack", "")
    if riesgo not in RIESGOS_ATTACK:
        return None, "Seleccione un nivel de riesgo ATT&CK válido (Alto/Medio/Bajo)."
    mfa = f.get("mfa_requerido", "").strip()
    revision = f.get("revision_periodica", "").strip()
    if not mfa or not revision:
        return None, "El requisito de MFA y la periodicidad de revisión son obligatorios."
    return {
        "codigo": codigo, "abreviatura": abreviatura, "denominacion": denominacion,
        "grupo_id": grupo_id, "cosecha": f.get("cosecha", "").strip(),
        "en_det7": 1 if f.get("en_det7") == "1" else 0,
        "funcion": f.get("funcion", "").strip(), "mfa_requerido": mfa,
        "riesgo_attack": riesgo, "revision_periodica": revision,
        "observaciones": f.get("observaciones", "").strip(),
    }, None


def _validar_datos_sistema(f, c):
    nombre = f.get("nombre", "").strip()
    if not nombre:
        return None, "El nombre del sistema o recurso es obligatorio."
    clasificacion = f.get("clasificacion", "")
    if clasificacion not in CLASIFICACIONES:
        return None, "Seleccione una clasificación válida."
    cat_nueva = f.get("categoria_nueva", "").strip()
    if cat_nueva:
        fila = c.execute("SELECT id FROM categoria_sistema WHERE nombre=?",
                         (cat_nueva,)).fetchone()
        cat_id = fila["id"] if fila else c.execute(
            "INSERT INTO categoria_sistema (nombre) VALUES (?)",
            (cat_nueva,)).lastrowid
    else:
        try:
            cat_id = int(f.get("categoria_id"))
        except (TypeError, ValueError):
            return None, "Seleccione una categoría válida o indique una nueva."
        if not c.execute("SELECT 1 FROM categoria_sistema WHERE id=?",
                         (cat_id,)).fetchone():
            return None, "Seleccione una categoría válida o indique una nueva."

    tecnicas_raw = f.get("tecnicas_attack", "").strip()
    codigos = [t.strip().upper() for t in tecnicas_raw.split("/") if t.strip()]
    if codigos:
        reconocidos = {r["id"] for r in c.execute(
            "SELECT id FROM attack_tecnica WHERE id IN (%s)"
            % ",".join("?" * len(codigos)), codigos)}
        desconocidos = [cod for cod in codigos if cod not in reconocidos]
        if desconocidos:
            return None, (f"Técnica(s) ATT&CK no reconocida(s) del catálogo: "
                          f"{', '.join(desconocidos)}.")
    tecnicas_attack = "/".join(codigos)

    return {
        "nombre": nombre, "categoria_id": cat_id, "clasificacion": clasificacion,
        "tecnicas_attack": tecnicas_attack,
    }, None


def _celda_segura(valor):
    """Antepone un apóstrofo si la celda podría interpretarse como fórmula
    al abrirse en Excel/Sheets (mitigación de CSV/Formula Injection)."""
    txt = "" if valor is None else str(valor)
    if txt and txt[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + txt
    return txt


def csv_response(nombre, encabezados, filas):
    """Genera CSV con BOM UTF-8 y delimitador ; (mismo formato que la UI HTML)."""
    from flask import Response

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([_celda_segura(h) for h in encabezados])
    w.writerows([[_celda_segura(v) for v in fila] for fila in filas])
    return Response(
        "\ufeff" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nombre}"})


def analizar_importacion_matriz(c, texto):
    """Analiza un CSV de matriz sin escribir en la base — mismo algoritmo que
    la antigua vista matriz_importar."""
    filas_csv = list(csv.reader(io.StringIO(texto), delimiter=";"))
    if not filas_csv:
        return None, "El archivo está vacío."

    encabezado, datos = filas_csv[0], filas_csv[1:]
    roles_por_abrev = {r["abreviatura"]: r["id"] for r in
                       c.execute("SELECT id, abreviatura FROM rol WHERE activo=1")}
    sistemas_por_nombre = {s["nombre"]: s["id"] for s in
                           c.execute("SELECT id, nombre FROM sistema WHERE activo=1")}
    niveles_validos = {n["codigo"] for n in c.execute("SELECT codigo FROM nivel_acceso")}
    actuales = {(m["rol_id"], m["sistema_id"]): m["nivel_codigo"]
                for m in c.execute("SELECT * FROM matriz_acceso")}

    columnas, errores = [], []
    for i, abrev in enumerate(encabezado[1:], start=1):
        abrev = abrev.strip()
        if abrev in roles_por_abrev:
            columnas.append((i, roles_por_abrev[abrev], abrev))
        else:
            errores.append(f"Columna «{abrev}»: no coincide con ningún rol "
                           "activo; se ignoró toda la columna.")

    cambios = []
    for fila in datos:
        if not fila or not fila[0].strip():
            continue
        nombre_sis = fila[0].strip()
        sid = sistemas_por_nombre.get(nombre_sis)
        if sid is None:
            errores.append(f"Sistema «{nombre_sis}»: no coincide con ningún "
                           "sistema activo; se ignoró la fila.")
            continue
        for i, rid, abrev in columnas:
            if i >= len(fila):
                continue
            nivel = fila[i].strip()
            if not nivel:
                continue
            if nivel not in niveles_validos:
                errores.append(f"«{nombre_sis}» × {abrev}: valor «{nivel}» "
                               "no es un nivel válido; se ignoró esa celda.")
                continue
            actual = actuales.get((rid, sid), "—")
            if nivel != actual:
                cambios.append({
                    "rol_id": rid, "rol": abrev, "sistema_id": sid,
                    "sistema": nombre_sis, "actual": actual, "nuevo": nivel,
                })

    if len(errores) > 50:
        errores = errores[:50] + [f"… y {len(errores) - 50} advertencia(s) más."]
    return cambios, errores


def aplicar_importacion_matriz(c, cambios, audit_fn):
    """Aplica la lista de cambios confirmados y registra en bitácora."""
    aplicados, detalle_partes = 0, []
    for item in cambios:
        try:
            rid = int(item["rol_id"])
            sid = int(item["sistema_id"])
        except (TypeError, ValueError, KeyError):
            continue
        nivel = item.get("nuevo", "")
        if not c.execute("SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone():
            continue
        rol = c.execute("SELECT abreviatura FROM rol WHERE id=?", (rid,)).fetchone()
        sis = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
        if not rol or not sis:
            continue
        c.execute(
            "UPDATE matriz_acceso SET nivel_codigo=? WHERE rol_id=? AND sistema_id=?",
            (nivel, rid, sid))
        aplicados += 1
        if len(detalle_partes) < 30:
            detalle_partes.append(f"{rol['abreviatura']}×{sis['nombre']}→{nivel}")
    c.commit()
    if aplicados:
        detalle = f"Importación CSV: {aplicados} cambio(s) aplicado(s): " + \
            "; ".join(detalle_partes)
        if aplicados > len(detalle_partes):
            detalle += f"; … y {aplicados - len(detalle_partes)} más."
        audit_fn("matriz_acceso", "IMPORTACION", detalle)
    return aplicados

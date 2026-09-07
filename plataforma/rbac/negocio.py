#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — validaciones y constantes compartidas por la API REST."""
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

"""Despliegue integrado — llamadas servidor-a-servidor a SUIIN-SGSI-RIESGOS.

Mismo patrón que integracion_rbac.py: red interna docker-compose, timeout
corto, None si el módulo no responde (el Inventario no debe caer por ello).
"""
import os

import requests
from django.conf import settings

RIESGOS_INTERNAL_URL = os.environ.get("RIESGOS_INTERNAL_URL", "http://riesgos-backend:8000")
_TIMEOUT = 2


def _headers_internos(espacio_codigo=None):
    headers = {}
    if settings.JWT_SHARED_SECRET:
        headers["X-Plataforma-Secret"] = settings.JWT_SHARED_SECRET
    if espacio_codigo:
        headers["X-Espacio-Datos"] = espacio_codigo
    return headers


def resumen_activo_por_inventario(inventario_id, espacio_codigo="organizacion"):
    """KPIs del activo espejo en Riesgos (vulns, riesgo matriz). None si no hay vínculo."""
    try:
        r = requests.get(
            f"{RIESGOS_INTERNAL_URL}/api/activos/",
            params={"inventario_id": inventario_id, "page_size": 1},
            headers=_headers_internos(espacio_codigo),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if not results:
            return None
        a = results[0]
        return {
            "id": a.get("id"),
            "id_activo": a.get("id_activo"),
            "riesgo_matriz": a.get("riesgo_matriz"),
            "total_vulnerabilidades": a.get("total_vulnerabilidades", 0),
            "vulnerabilidades_criticas": a.get("vulnerabilidades_criticas", 0),
            "cobertura": a.get("cobertura"),
            "cobertura_display": a.get("cobertura_display"),
            "afectado_red_team": a.get("afectado_red_team", False),
        }
    except requests.RequestException:
        return None


def alertas_riesgos_resumen(espacio_codigo="organizacion"):
    """Conteos operativos de vencimientos en el módulo Riesgos."""
    try:
        r = requests.get(
            f"{RIESGOS_INTERNAL_URL}/api/alertas/resumen/",
            headers=_headers_internos(espacio_codigo),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "total_vencidas": data.get("total_vencidas", 0),
            "total_por_vencer": data.get("total_por_vencer", 0),
            "disponible": True,
        }
    except requests.RequestException:
        return {"total_vencidas": 0, "total_por_vencer": 0, "disponible": False}


def kpis_riesgos_dashboard(espacio_codigo="organizacion"):
    """KPIs agregados del panel de Riesgos (para centro de alertas unificado)."""
    try:
        r = requests.get(
            f"{RIESGOS_INTERNAL_URL}/api/dashboard/resumen/",
            headers=_headers_internos(espacio_codigo),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        kpis = data.get("kpis") or {}
        return {
            "disponible": True,
            "activos_sin_cobertura": kpis.get("activos_sin_cobertura", 0),
            "vulnerabilidades_criticas": kpis.get("vulnerabilidades_criticas", 0),
            "activos_comprometidos": kpis.get("activos_comprometidos", 0),
        }
    except requests.RequestException:
        return {"disponible": False}


def mapa_activos_por_inventario(espacio_codigo="organizacion"):
    """Mapa inventario_id → metadatos del activo espejo en Riesgos."""
    try:
        mapa = {}
        page = 1
        while page <= 50:
            r = requests.get(
                f"{RIESGOS_INTERNAL_URL}/api/activos/",
                params={"page": page, "page_size": 200},
                headers=_headers_internos(espacio_codigo),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            for a in data.get("results", []):
                inv_id = a.get("inventario_id")
                if inv_id:
                    mapa[int(inv_id)] = {
                        "id": a.get("id"),
                        "id_activo": a.get("id_activo"),
                        "total_vulnerabilidades": a.get("total_vulnerabilidades", 0),
                        "vulnerabilidades_criticas": a.get("vulnerabilidades_criticas", 0),
                        "riesgo_matriz": a.get("riesgo_matriz"),
                    }
            if not data.get("next"):
                break
            page += 1
        return mapa
    except requests.RequestException:
        return None


def _contar_huerfanos_riesgos(espacio_codigo="organizacion"):
    try:
        r = requests.get(
            f"{RIESGOS_INTERNAL_URL}/api/activos/",
            params={"sin_vinculo_inventario": "true", "page_size": 1},
            headers=_headers_internos(espacio_codigo),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("count", 0)
    except requests.RequestException:
        return 0


def listar_huerfanos_riesgos(espacio_codigo="organizacion"):
    """Activos en Riesgos sin inventario_id (solo lectura vía API interna)."""
    try:
        filas = []
        page = 1
        while page <= 50:
            r = requests.get(
                f"{RIESGOS_INTERNAL_URL}/api/activos/",
                params={"sin_vinculo_inventario": "true", "page": page, "page_size": 200},
                headers=_headers_internos(espacio_codigo),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            for a in data.get("results", []):
                filas.append({
                    "riesgos_id": a.get("id"),
                    "id_activo": a.get("id_activo"),
                    "nombre": a.get("nombre"),
                    "ip_principal": a.get("ip_principal"),
                    "riesgo_matriz": a.get("riesgo_matriz"),
                })
            if not data.get("next"):
                break
            page += 1
        return filas
    except requests.RequestException:
        return None


def resumen_vinculacion(total_inventario, espacio_codigo="organizacion"):
    """Conteos de sincronización Inventario ↔ Riesgos."""
    mapa = mapa_activos_por_inventario(espacio_codigo=espacio_codigo)
    if mapa is None:
        return {"disponible": False}
    vinculados = len(mapa)
    return {
        "disponible": True,
        "total_inventario": total_inventario,
        "vinculados": vinculados,
        "sin_espejo_riesgos": max(0, total_inventario - vinculados),
        "huerfanos_riesgos": _contar_huerfanos_riesgos(espacio_codigo=espacio_codigo),
    }


def detalle_vinculacion(activos_qs, espacio_codigo="organizacion"):
    """Estado de sincronización con listados para panel operativo (Ola 6)."""
    from .models import Activo

    total = activos_qs.count() if hasattr(activos_qs, "count") else Activo.objects.count()
    resumen = resumen_vinculacion(total, espacio_codigo=espacio_codigo)
    if not resumen.get("disponible"):
        return {"disponible": False, "resumen": resumen}

    mapa = mapa_activos_por_inventario(espacio_codigo=espacio_codigo) or {}
    sin_espejo = []
    for a in activos_qs.only("id", "id_activo", "nombre", "clase", "nivel_riesgo"):
        if a.pk not in mapa:
            sin_espejo.append({
                "inventario_id": a.pk,
                "id_activo": a.id_activo,
                "nombre": a.nombre,
                "clase": a.clase,
                "nivel_riesgo": a.nivel_riesgo,
            })
    huerfanos = listar_huerfanos_riesgos(espacio_codigo=espacio_codigo)
    if huerfanos is None:
        return {"disponible": False, "resumen": resumen}

    pct = round(resumen["vinculados"] / total * 100, 1) if total else 100.0
    return {
        "disponible": True,
        "resumen": resumen,
        "sin_espejo": sin_espejo,
        "huerfanos_riesgos": huerfanos,
        "sincronizacion_ok": not sin_espejo and not huerfanos,
        "porcentaje_vinculados": pct,
    }


def generar_csv_vinculacion(detalle, tipo="todos"):
    """CSV operativo: activos sin espejo y/o huérfanos en Riesgos."""
    import csv
    from io import StringIO

    buf = StringIO()
    w = csv.writer(buf)
    w.writerow([
        "tipo", "inventario_id", "riesgos_id", "id_activo", "nombre",
        "clase", "nivel_riesgo", "ip_principal", "riesgo_matriz",
    ])
    if tipo in ("todos", "sin_espejo"):
        for row in detalle.get("sin_espejo", []):
            w.writerow([
                "sin_espejo",
                row.get("inventario_id"),
                "",
                row.get("id_activo"),
                row.get("nombre"),
                row.get("clase"),
                row.get("nivel_riesgo"),
                "",
                "",
            ])
    if tipo in ("todos", "huerfanos"):
        for row in detalle.get("huerfanos_riesgos", []):
            w.writerow([
                "huerfano_riesgos",
                "",
                row.get("riesgos_id"),
                row.get("id_activo"),
                row.get("nombre"),
                "",
                "",
                row.get("ip_principal"),
                row.get("riesgo_matriz"),
            ])
    return buf.getvalue()


def resumen_riesgos_panel(espacio_codigo="organizacion"):
    """KPIs de Riesgos para panel ejecutivo y badges del Shell."""
    alertas = alertas_riesgos_resumen(espacio_codigo=espacio_codigo)
    kpis = kpis_riesgos_dashboard(espacio_codigo=espacio_codigo)
    if not alertas.get("disponible") and not kpis.get("disponible"):
        return None
    pendientes = 0
    if alertas.get("disponible"):
        pendientes += alertas.get("total_vencidas", 0)
        pendientes += alertas.get("total_por_vencer", 0)
    if kpis.get("disponible"):
        pendientes += kpis.get("activos_sin_cobertura", 0)
        pendientes += kpis.get("vulnerabilidades_criticas", 0)
        pendientes += kpis.get("activos_comprometidos", 0)
    return {
        "disponible": True,
        "pendientes_total": pendientes,
        **alertas,
        **kpis,
    }

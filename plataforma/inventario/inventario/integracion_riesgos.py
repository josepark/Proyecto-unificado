"""Despliegue integrado — llamadas servidor-a-servidor a SUIIN-SGSI-RIESGOS.

Mismo patrón que integracion_rbac.py: red interna docker-compose, timeout
corto, None si el módulo no responde (el Inventario no debe caer por ello).
"""
import os

import requests

RIESGOS_INTERNAL_URL = os.environ.get("RIESGOS_INTERNAL_URL", "http://riesgos-backend:8000")
_TIMEOUT = 2


def resumen_activo_por_inventario(inventario_id):
    """KPIs del activo espejo en Riesgos (vulns, riesgo matriz). None si no hay vínculo."""
    try:
        r = requests.get(
            f"{RIESGOS_INTERNAL_URL}/api/activos/",
            params={"inventario_id": inventario_id, "page_size": 1},
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


def alertas_riesgos_resumen():
    """Conteos operativos de vencimientos en el módulo Riesgos."""
    try:
        r = requests.get(f"{RIESGOS_INTERNAL_URL}/api/alertas/resumen/", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return {
            "total_vencidas": data.get("total_vencidas", 0),
            "total_por_vencer": data.get("total_por_vencer", 0),
            "disponible": True,
        }
    except requests.RequestException:
        return {"total_vencidas": 0, "total_por_vencer": 0, "disponible": False}


def kpis_riesgos_dashboard():
    """KPIs agregados del panel de Riesgos (para centro de alertas unificado)."""
    try:
        r = requests.get(f"{RIESGOS_INTERNAL_URL}/api/dashboard/resumen/", timeout=_TIMEOUT)
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


def resumen_riesgos_panel():
    """KPIs de Riesgos para panel ejecutivo y badges del Shell."""
    alertas = alertas_riesgos_resumen()
    kpis = kpis_riesgos_dashboard()
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

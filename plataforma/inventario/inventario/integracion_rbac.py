"""Despliegue integrado — llamadas servidor-a-servidor a SUIIN-RBAC.

Estas llamadas van directo a la red interna de docker-compose
(http://rbac:5000), NO a través de nginx: la puerta de autorización de
nginx (auth_request) protege el acceso desde el navegador, no las llamadas
de un backend que ya corre dentro de la misma red de confianza.

Todas las funciones devuelven None si RBAC no responde, para que el
Inventario nunca se caiga por una falla o mantenimiento de RBAC.
"""
import os

import requests

RBAC_INTERNAL_URL = os.environ.get("RBAC_INTERNAL_URL", "http://rbac:5000")

_TIMEOUT = 2  # segundos — corto a propósito: esto no debe demorar una petición del navegador


def resumen_rbac():
    """KPIs consolidados (roles, sistemas, MFA, vencimientos, excepciones,
    certificación de roles). Usado por el badge de la pestaña "Matriz RBAC"
    y por el Panel ejecutivo."""
    try:
        r = requests.get(f"{RBAC_INTERNAL_URL}/api/resumen", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def inicio_rbac():
    """Detalle del tablero de Inicio de RBAC (no solo conteos, como
    resumen_rbac): quién exactamente tiene el MFA pendiente, qué vence
    pronto, roles críticos. Usado por el resumen semanal por correo
    (management/commands/enviar_resumen_alertas.py) — un conteo solo
    ("3 vencimientos") no le dice al Dinamizador qué hacer; el detalle
    con nombres sí."""
    try:
        r = requests.get(f"{RBAC_INTERNAL_URL}/api/inicio", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def catalogo_sistemas_rbac():
    """Catálogo completo de sistemas de la matriz MCA con sus accesos por
    rol. None si RBAC no responde."""
    try:
        r = requests.get(f"{RBAC_INTERNAL_URL}/api/sistemas", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def auditoria_rbac(limite=80):
    """Últimas filas de log_auditoria de RBAC — para el panel unificado."""
    try:
        r = requests.get(
            f"{RBAC_INTERNAL_URL}/api/auditoria",
            params={"limite": limite},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("registros") or data.get("filas") or []
    except requests.RequestException:
        return None


def accesos_rbac_por_sistema(nombre_sistema=None, sistema_rbac_id=None):
    """Busca accesos en el catálogo canónico de RBAC por ID (prioritario) o
    por nombre normalizado de `sistema_mca_equivalente`."""
    if not sistema_rbac_id and not nombre_sistema:
        return None
    catalogo = catalogo_sistemas_rbac()
    if catalogo is None:
        return None
    if sistema_rbac_id:
        for s in catalogo:
            if s.get("id") == sistema_rbac_id:
                return s.get("accesos") or []
    if nombre_sistema:
        objetivo = nombre_sistema.strip().lower()
        for s in catalogo:
            nom = (s.get("nombre") or "").strip().lower()
            if nom and nom == objetivo:
                return s.get("accesos") or []
    return None


def sistema_rbac_resumen(nombre_sistema=None, sistema_rbac_id=None):
    """Metadatos del sistema RBAC vinculado (excepciones, nombre canónico)."""
    if not sistema_rbac_id and not nombre_sistema:
        return None
    catalogo = catalogo_sistemas_rbac()
    if catalogo is None:
        return None
    if sistema_rbac_id:
        for s in catalogo:
            if s.get("id") == sistema_rbac_id:
                return s
    if nombre_sistema:
        objetivo = nombre_sistema.strip().lower()
        for s in catalogo:
            nom = (s.get("nombre") or "").strip().lower()
            if nom and nom == objetivo:
                return s
    return None

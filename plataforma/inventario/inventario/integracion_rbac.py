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


def accesos_rbac_por_sistema(nombre_sistema):
    """Busca en el catálogo canónico de RBAC los accesos reales del sistema
    cuyo nombre coincide (sin distinguir mayúsculas ni espacios sobrantes)
    con el `sistema_mca_equivalente` capturado en el Inventario.

    Devuelve:
      - la lista de accesos (puede estar vacía) si RBAC respondió y hubo coincidencia,
      - None si RBAC no respondió, si no se indicó nombre, o si no hubo
        coincidencia (para poder distinguir "no hay accesos" de "no se
        pudo verificar / no está vinculado" en la interfaz).
    """
    if not nombre_sistema:
        return None
    catalogo = catalogo_sistemas_rbac()
    if catalogo is None:
        return None
    objetivo = nombre_sistema.strip().lower()
    for s in catalogo:
        if s["nombre"].strip().lower() == objetivo:
            return s["accesos"]
    return None

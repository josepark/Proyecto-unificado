#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Espacios de datos por usuario — aísla sistemas, usuarios y excepciones RBAC."""
from flask import request

ESPACIO_ORGANIZACION = "organizacion"


def espacio_codigo_actual():
    """Código del espacio activo (nginx reenvía X-Espacio-Datos desde Inventario)."""
    codigo = (request.headers.get("X-Espacio-Datos") or "").strip()
    return codigo or ESPACIO_ORGANIZACION


def sql_filtro_espacio(alias=""):
    """Fragmento SQL: «AND alias.espacio_codigo = ?»."""
    pref = f"{alias}." if alias else ""
    return f" AND {pref}espacio_codigo = ?"


def verificar_sistema_espacio(c, sid, esp=None):
    esp = esp or espacio_codigo_actual()
    return c.execute(
        "SELECT 1 FROM sistema WHERE id=? AND espacio_codigo=?",
        (sid, esp),
    ).fetchone()


def verificar_usuario_espacio(c, uid, esp=None):
    esp = esp or espacio_codigo_actual()
    return c.execute(
        "SELECT 1 FROM usuario WHERE id=? AND espacio_codigo=?",
        (uid, esp),
    ).fetchone()

"""Fragmentos SQL compatibles con SQLite (dev) y PostgreSQL (producción)."""
from django.db import connections

DIAS_REVISION = {'Mensual': 30, 'Trimestral': 90, 'Semestral': 180, 'Anual': 365}


def vendor(using='rbac'):
    return connections[using].vendor


def hoy_sql(using='rbac'):
    if vendor(using) == 'postgresql':
        return 'CURRENT_DATE'
    return "date('now','localtime')"


def date_col(column, using='rbac'):
    if vendor(using) == 'postgresql':
        return f"NULLIF(TRIM({column}), '')::date"
    return f'date({column})'


def hoy_mas_dias(dias, using='rbac'):
    if vendor(using) == 'postgresql':
        return f'(CURRENT_DATE + {int(dias)})'
    return f"date('now','localtime','+{int(dias)} days')"


def dias_hasta(column, using='rbac'):
    if vendor(using) == 'postgresql':
        return f'({date_col(column, using)} - {hoy_sql(using)})'
    return (
        f"CAST(julianday({column}) - julianday('now','localtime') AS INTEGER)"
    )


def sql_activo(column, using='rbac'):
    """activo=1 en SQLite; IS TRUE en PostgreSQL (BooleanField)."""
    if vendor(using) == 'postgresql':
        return f'{column} IS TRUE'
    return f'{column}=1'


def sql_revision_vencida(alias='r', using='rbac'):
    case_dias = ' '.join(
        f"WHEN '{k}' THEN {v}" for k, v in DIAS_REVISION.items()
    )
    if vendor(using) == 'postgresql':
        rev = f"NULLIF(TRIM({alias}.ultima_revision), '')"
        return f"""CASE
            WHEN {rev} IS NULL THEN 1
            WHEN ({rev}::date +
                  (CASE {alias}.revision_periodica {case_dias} ELSE 90 END)
                  * INTERVAL '1 day') < CURRENT_DATE THEN 1
            ELSE 0 END"""
    return f"""CASE
        WHEN {alias}.ultima_revision IS NULL THEN 1
        WHEN date({alias}.ultima_revision, '+' ||
             (CASE {alias}.revision_periodica {case_dias} ELSE 90 END) ||
             ' days') < date('now') THEN 1
        ELSE 0 END"""

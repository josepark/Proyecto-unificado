"""Acceso a la base RBAC vía cursor SQL."""
from django.db import connections


def rbac_cursor(using='rbac'):
    return connections[using].cursor()


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dictfetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def fetchall(sql, params=None, using='rbac'):
    with rbac_cursor(using) as cursor:
        cursor.execute(sql, params or [])
        return dictfetchall(cursor)


def fetchone(sql, params=None, using='rbac'):
    with rbac_cursor(using) as cursor:
        cursor.execute(sql, params or [])
        return dictfetchone(cursor)


def scalar(sql, params=None, using='rbac'):
    row = fetchone(sql, params, using=using)
    if not row:
        return None
    return next(iter(row.values()))

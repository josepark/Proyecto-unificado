"""Verificación y registro de la bitácora encadenada (ISO 27002 — 8.15)."""
import hashlib

from django.utils import timezone

from rbac.db_util import fetchall, fetchone, rbac_cursor, scalar


def _hash_registro(prev, fecha, entidad, accion, detalle, responsable):
    base = f'{prev}|{fecha}|{entidad}|{accion}|{detalle}|{responsable}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()


def registrar(entidad, accion, detalle, responsable='operador local', using='rbac'):
    fecha = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    prev = fetchone(
        'SELECT hash FROM log_auditoria ORDER BY id DESC LIMIT 1', using=using,
    )
    prev_hash = prev['hash'] if prev else 'GENESIS'
    hash_cadena = _hash_registro(prev_hash, fecha, entidad, accion, detalle, responsable)
    with rbac_cursor(using) as cursor:
        cursor.execute(
            'INSERT INTO log_auditoria (fecha, entidad, accion, detalle, responsable, hash) '
            'VALUES (%s, %s, %s, %s, %s, %s)',
            [fecha, entidad, accion, detalle, responsable, hash_cadena],
        )


def verificar_cadena(using='rbac'):
    prev = 'GENESIS'
    total = 0
    for registro in fetchall(
        'SELECT id, fecha, entidad, accion, detalle, responsable, hash '
        'FROM log_auditoria ORDER BY id',
        using=using,
    ):
        esperado = _hash_registro(
            prev,
            registro['fecha'],
            registro['entidad'],
            registro['accion'],
            registro['detalle'],
            registro['responsable'],
        )
        if registro['hash'] != esperado:
            return False, registro['id']
        prev = registro['hash']
        total += 1
    return True, total

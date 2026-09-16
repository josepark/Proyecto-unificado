"""Verificación de la bitácora encadenada (ISO 27002 — 8.15)."""
import hashlib

from rbac.db_util import fetchall


def _hash_registro(prev, fecha, entidad, accion, detalle, responsable):
    base = f'{prev}|{fecha}|{entidad}|{accion}|{detalle}|{responsable}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()


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

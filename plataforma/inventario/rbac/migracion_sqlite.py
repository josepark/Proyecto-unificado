"""Migración ETL: rbac/rbac.db (Flask SQLite) → base Django alias ``rbac``."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from django.db import connections, transaction
from django.utils import timezone

from rbac.paths import RBAC_DB_FLASK

TABLAS_ORDEN = (
    'grupo_rol',
    'nivel_acceso',
    'categoria_sistema',
    'attack_tecnica',
    'rol',
    'sistema',
    'matriz_acceso',
    'usuario',
    'acceso_excepcion',
    'log_auditoria',
)

TABLAS_SERIAL = (
    'grupo_rol',
    'categoria_sistema',
    'rol',
    'sistema',
    'usuario',
    'log_auditoria',
)

BOOL_COLUMNS = {
    'rol': ('en_det7', 'activo'),
    'sistema': ('activo',),
    'attack_tecnica': ('es_subtecnica',),
}

DATETIME_COLUMNS = {
    'usuario': ('creado', 'actualizado'),
    'acceso_excepcion': ('creado',),
}


class MigracionError(Exception):
    pass


def _conectar_origen_sqlite(origen: Path) -> sqlite3.Connection:
    """Abre rbac.db origen en solo lectura (volúmenes Docker montados :ro)."""
    ruta = origen.resolve().as_posix()
    return sqlite3.connect(f'file:{ruta}?mode=ro', uri=True)


def origen_sqlite_usable(origen: Path | None = None) -> bool:
    """True si rbac.db existe y SQLite puede leerlo (p. ej. montaje :ro)."""
    path = Path(origen or RBAC_DB_FLASK)
    if not path.is_file():
        return False
    try:
        verificar_origen(path)
        return True
    except (MigracionError, sqlite3.OperationalError, OSError):
        return False


def _parse_datetime(val):
    if val is None or val == '':
        return timezone.now()
    if isinstance(val, datetime):
        if timezone.is_naive(val):
            return timezone.make_aware(val, timezone.get_current_timezone())
        return val
    texto = str(val).strip()[:19]
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(texto, fmt)
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except ValueError:
            continue
    return timezone.now()


def _transform_row(tabla, row_dict):
    for col in BOOL_COLUMNS.get(tabla, ()):
        if col in row_dict:
            row_dict[col] = bool(row_dict[col])
    for col in DATETIME_COLUMNS.get(tabla, ()):
        if col in row_dict:
            row_dict[col] = _parse_datetime(row_dict[col])
    return row_dict


def verificar_origen(origen: Path) -> None:
    if not origen.is_file():
        raise MigracionError(f'No se encontró {origen}')
    con = _conectar_origen_sqlite(origen)
    con.row_factory = sqlite3.Row
    try:
        for tabla in ('sistema', 'rol', 'usuario', 'matriz_acceso'):
            ok = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tabla,),
            ).fetchone()
            if not ok:
                raise MigracionError(
                    f'{origen} incompleta: falta la tabla {tabla}. '
                    'Ejecute rbac/recuperar_rbac_db.py o rbac/seed.py.'
                )
    finally:
        con.close()


def vaciar_destino(using='rbac'):
    with transaction.atomic(using=using):
        cursor = connections[using].cursor()
        if connections[using].vendor == 'postgresql':
            cursor.execute(
                'TRUNCATE ' + ', '.join(TABLAS_ORDEN) + ' RESTART IDENTITY CASCADE'
            )
        else:
            for tabla in reversed(TABLAS_ORDEN):
                cursor.execute(f'DELETE FROM {tabla}')


def _columnas_destino(tabla, using='rbac'):
    cursor = connections[using].cursor()
    if connections[using].vendor == 'postgresql':
        cursor.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_name = %s AND table_schema = 'public'""",
            [tabla],
        )
    else:
        cursor.execute(f'PRAGMA table_info({tabla})')
        return [r[1] for r in cursor.fetchall()]
    return [r[0] for r in cursor.fetchall()]


def _copiar_tabla(src_con, tabla, using='rbac'):
    src_cols = [r[1] for r in src_con.execute(f'PRAGMA table_info({tabla})')]
    dst_cols = _columnas_destino(tabla, using=using)
    cols = [c for c in src_cols if c in dst_cols]
    if not cols:
        return 0

    placeholders = ', '.join(['%s'] * len(cols))
    col_list = ', '.join(cols)
    insert_sql = f'INSERT INTO {tabla} ({col_list}) VALUES ({placeholders})'

    filas = src_con.execute(f'SELECT {col_list} FROM {tabla}').fetchall()
    count = 0
    cursor = connections[using].cursor()
    for fila in filas:
        row = _transform_row(tabla, dict(zip(cols, fila)))
        cursor.execute(insert_sql, [row[c] for c in cols])
        count += 1
    return count


def _ajustar_secuencias(using='rbac'):
    if connections[using].vendor != 'postgresql':
        return
    cursor = connections[using].cursor()
    for tabla in TABLAS_SERIAL:
        cursor.execute(
            f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {tabla}), 1), true)"
        )


def contar_tablas(origen: Path | None = None, using='rbac', origen_sqlite=False):
    counts = {}
    if origen_sqlite and origen:
        con = _conectar_origen_sqlite(Path(origen))
        try:
            for tabla in TABLAS_ORDEN:
                try:
                    counts[tabla] = con.execute(
                        f'SELECT COUNT(*) FROM {tabla}'
                    ).fetchone()[0]
                except sqlite3.OperationalError:
                    counts[tabla] = 0
        finally:
            con.close()
    else:
        cursor = connections[using].cursor()
        for tabla in TABLAS_ORDEN:
            cursor.execute(f'SELECT COUNT(*) FROM {tabla}')
            counts[tabla] = cursor.fetchone()[0]
    return counts


def migrar(origen: Path | None = None, using='rbac', forzar=False, dry_run=False):
    origen = Path(origen or RBAC_DB_FLASK)
    verificar_origen(origen)

    origen_counts = contar_tablas(origen, using=using, origen_sqlite=True)
    if dry_run:
        return {'origen': origen_counts, 'destino': {}, 'dry_run': True}

    destino_counts = contar_tablas(using=using)
    if any(destino_counts.values()) and not forzar:
        raise MigracionError(
            'La base RBAC destino ya tiene datos. Use --forzar para repoblar desde rbac.db.'
        )

    stats = {}
    src = _conectar_origen_sqlite(origen)
    try:
        with transaction.atomic(using=using):
            if forzar or any(destino_counts.values()):
                vaciar_destino(using=using)
            for tabla in TABLAS_ORDEN:
                stats[tabla] = _copiar_tabla(src, tabla, using=using)
            _ajustar_secuencias(using=using)
    finally:
        src.close()

    destino_final = contar_tablas(using=using)
    for tabla in TABLAS_ORDEN:
        if origen_counts.get(tabla, 0) != destino_final.get(tabla, 0):
            raise MigracionError(
                f'Conteo distinto en {tabla}: origen={origen_counts.get(tabla)} '
                f'destino={destino_final.get(tabla)}'
            )

    return {
        'origen': origen_counts,
        'destino': destino_final,
        'copiadas': stats,
        'origen_path': str(origen),
    }

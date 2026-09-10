#!/usr/bin/env python3
"""Migración: columna espacio_codigo en sistema, usuario y acceso_excepcion.

Los datos demo existentes quedan en espacio «organizacion». Las cuentas nuevas
reciben su propio espacio vacío vía header X-Espacio-Datos.

Uso: python3 migrar_espacio_datos.py
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "rbac.db")
ESPACIO_DEFAULT = "organizacion"

_VISTAS_RBAC = (
    "v_accesos_usuario",
    "v_roles_criticos",
    "v_alertas_mfa",
)

_RECREAR_VISTAS_SQL = """
CREATE VIEW v_accesos_usuario AS
SELECT u.id AS usuario_id, u.nombre AS usuario, u.estado,
       r.abreviatura AS rol, r.denominacion,
       s.nombre AS sistema, c.nombre AS categoria, s.clasificacion,
       COALESCE(e.nivel_codigo, ma.nivel_codigo) AS nivel,
       n.nombre AS nivel_nombre,
       CASE WHEN e.usuario_id IS NOT NULL THEN 1 ELSE 0 END AS es_excepcion
FROM usuario u
JOIN rol r            ON r.id = u.rol_id
JOIN matriz_acceso ma ON ma.rol_id = r.id
JOIN sistema s        ON s.id = ma.sistema_id
JOIN categoria_sistema c ON c.id = s.categoria_id
LEFT JOIN acceso_excepcion e ON e.usuario_id = u.id AND e.sistema_id = s.id
       AND (e.fecha_fin IS NULL OR date(e.fecha_fin) >= date('now'))
JOIN nivel_acceso n   ON n.codigo = COALESCE(e.nivel_codigo, ma.nivel_codigo)
WHERE COALESCE(e.nivel_codigo, ma.nivel_codigo) <> '—'
  AND u.estado IN ('Activo','Temporal')
  AND r.activo = 1 AND s.activo = 1;

CREATE VIEW v_roles_criticos AS
SELECT r.codigo, r.abreviatura, r.denominacion, s.nombre AS sistema, s.clasificacion
FROM matriz_acceso ma
JOIN rol r     ON r.id = ma.rol_id
JOIN sistema s ON s.id = ma.sistema_id
WHERE ma.nivel_codigo = 'A' AND r.activo = 1 AND s.activo = 1;

CREATE VIEW v_alertas_mfa AS
SELECT u.id, u.nombre, r.abreviatura AS rol, r.mfa_requerido, u.mfa_activo
FROM usuario u JOIN rol r ON r.id = u.rol_id
WHERE u.estado IN ('Activo','Temporal')
  AND r.mfa_requerido LIKE 'Sí%'
  AND u.mfa_activo NOT LIKE 'Sí%'
  AND r.activo = 1;
"""


def _tabla_existe(con, nombre):
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (nombre,),
        ).fetchone()
        is not None
    )


def _columnas(con, tabla):
    if not _tabla_existe(con, tabla):
        return []
    return [r[1] for r in con.execute(f"PRAGMA table_info({tabla})")]


def _agregar_columna_espacio(con, tabla):
    if "espacio_codigo" in _columnas(con, tabla):
        return False
    con.execute(
        f"ALTER TABLE {tabla} ADD COLUMN espacio_codigo TEXT NOT NULL "
        f"DEFAULT '{ESPACIO_DEFAULT}'"
    )
    print(f"Columna espacio_codigo agregada a {tabla}.")
    return True


def _sistema_unicidad_por_espacio(con):
    row = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='sistema'"
    ).fetchone()
    if not row or not row[0]:
        return False
    ddl = row[0].replace(" ", "")
    return "UNIQUE(espacio_codigo,nombre)" in ddl


def _migracion_completa(con):
    for tabla in ("sistema", "usuario", "acceso_excepcion"):
        if "espacio_codigo" not in _columnas(con, tabla):
            return False
    return _sistema_unicidad_por_espacio(con)


def _eliminar_vistas(con):
    for vista in _VISTAS_RBAC:
        con.execute(f"DROP VIEW IF EXISTS {vista}")


def _completar_migracion_sistema_interrumpida(con):
    """Tras un DROP TABLE sistema abortado, sistema_new puede quedar sin renombrar."""
    if _tabla_existe(con, "sistema") or not _tabla_existe(con, "sistema_new"):
        return False
    _eliminar_vistas(con)
    con.execute("ALTER TABLE sistema_new RENAME TO sistema")
    con.executescript(_RECREAR_VISTAS_SQL)
    print("Migración interrumpida completada (sistema_new → sistema).")
    return True


def _recrear_sistema_unicidad_espacio(con):
    """Nombre único por espacio, no globalmente."""
    if _sistema_unicidad_por_espacio(con):
        return False

    if _completar_migracion_sistema_interrumpida(con):
        return True

    if not _tabla_existe(con, "sistema"):
        raise RuntimeError(
            "Tabla 'sistema' ausente. Ejecute python3 recuperar_rbac_db.py y reintente."
        )

    _eliminar_vistas(con)
    con.executescript("""
    CREATE TABLE sistema_new (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre           TEXT NOT NULL,
        categoria_id     INTEGER NOT NULL REFERENCES categoria_sistema(id),
        clasificacion    TEXT NOT NULL CHECK (clasificacion IN
                           ('Altamente Confidencial','Confidencial','Interna','Pública')),
        tecnicas_attack  TEXT,
        activo           INTEGER NOT NULL DEFAULT 1,
        espacio_codigo   TEXT NOT NULL DEFAULT 'organizacion',
        UNIQUE (espacio_codigo, nombre)
    );
    INSERT INTO sistema_new (id, nombre, categoria_id, clasificacion, tecnicas_attack,
                             activo, espacio_codigo)
    SELECT id, nombre, categoria_id, clasificacion, tecnicas_attack, activo,
           COALESCE(espacio_codigo, 'organizacion')
    FROM sistema;
    DROP TABLE sistema;
    ALTER TABLE sistema_new RENAME TO sistema;
    CREATE INDEX IF NOT EXISTS idx_sistema_espacio ON sistema(espacio_codigo);
    """)
    con.executescript(_RECREAR_VISTAS_SQL)
    print("Tabla sistema: unicidad (espacio_codigo, nombre) aplicada.")
    return True


def migrar(db_path=DB):
    if not os.path.exists(db_path):
        print(f"No existe {db_path} — omitiendo migración de espacio.")
        return

    from recuperar_rbac_db import recuperar_si_corrupta

    recuperar_si_corrupta(db_path)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        if _migracion_completa(con):
            print("Migración de espacio de datos RBAC ya aplicada.")
            return
        for tabla in ("sistema", "usuario", "acceso_excepcion"):
            _agregar_columna_espacio(con, tabla)
        _recrear_sistema_unicidad_espacio(con)
        con.execute("CREATE INDEX IF NOT EXISTS idx_usuario_espacio ON usuario(espacio_codigo)")
        con.commit()
        print("Migración de espacio de datos RBAC completa.")
    finally:
        con.close()


if __name__ == "__main__":
    migrar()

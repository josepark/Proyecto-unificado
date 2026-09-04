#!/usr/bin/env python3
"""Migración acumulativa a v2.1 sobre una rbac.db existente, sin perder datos:
columnas 'activo', tabla 'acceso_excepcion', bitácora encadenada (columna
'hash' con recomputación del histórico) y vista con exclusión de excepciones
vencidas. Si su base viene de la v2.0 (con login), la tabla 'cuenta' queda
sin uso y puede conservarse o eliminarse manualmente.
Uso: python3 migrar_v2_1.py"""
import hashlib
import sqlite3

import catalogo_attack

c = sqlite3.connect('rbac.db')
c.row_factory = sqlite3.Row

for tabla in ('rol', 'sistema'):
    if 'activo' not in [r[1] for r in c.execute(f"PRAGMA table_info({tabla})")]:
        c.execute(f"ALTER TABLE {tabla} ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")
        print(f"Columna 'activo' agregada a {tabla}.")

if 'ultima_revision' not in [r[1] for r in c.execute("PRAGMA table_info(rol)")]:
    c.execute("ALTER TABLE rol ADD COLUMN ultima_revision TEXT")
    print("Columna 'ultima_revision' agregada a rol (certificación periódica de accesos).")

if not c.execute("SELECT name FROM sqlite_master WHERE name='acceso_excepcion'").fetchone():
    c.executescript("""
    CREATE TABLE acceso_excepcion (
        usuario_id   INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
        sistema_id   INTEGER NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
        nivel_codigo TEXT NOT NULL REFERENCES nivel_acceso(codigo),
        motivo       TEXT NOT NULL,
        fecha_fin    TEXT,
        creado       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        PRIMARY KEY (usuario_id, sistema_id));""")
    print("Tabla acceso_excepcion creada.")

if 'hash' not in [r[1] for r in c.execute("PRAGMA table_info(log_auditoria)")]:
    c.execute("ALTER TABLE log_auditoria ADD COLUMN hash TEXT NOT NULL DEFAULT ''")
    c.execute("UPDATE log_auditoria SET responsable='sistema' WHERE responsable IS NULL")
    prev = 'GENESIS'
    for r in c.execute("SELECT * FROM log_auditoria ORDER BY id").fetchall():
        h = hashlib.sha256(
            f"{prev}|{r['fecha']}|{r['entidad']}|{r['accion']}|{r['detalle']}|{r['responsable']}"
            .encode()).hexdigest()
        c.execute("UPDATE log_auditoria SET hash=? WHERE id=?", (h, r['id']))
        prev = h
    print("Bitácora encadenada: hashes calculados para el histórico.")

c.executescript("""
DROP VIEW IF EXISTS v_accesos_usuario;
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
  AND u.estado IN ('Activo','Temporal') AND r.activo = 1 AND s.activo = 1;
""")
c.commit()
n_attack = catalogo_attack.sincronizar(c)
print(f"Catálogo MITRE ATT&CK sincronizado: {n_attack} técnicas.")
print("Migración a v2.1 completa.")

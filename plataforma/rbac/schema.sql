-- ============================================================================
-- SUIIN-RBAC — Esquema de Base de Datos
-- Sistematización de la Matriz de Control de Acceso Basado en Roles
-- Documento fuente: SUIIN-SGSI-MCA-001 v2.0
-- Base normativa: ISO/IEC 27002:2022 (5.15–5.18) · POL-SI-002 · MAN-POL-SI-002
--                 Determinación 7 CRIC-Nacional (Decisión No. 02 / 02-Ene-2025)
-- Motor: SQLite 3 (portable a PostgreSQL/MySQL con cambios mínimos)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Grupos de roles según Determinación 7 + grupos SGSI (TI Privilegiado, Externo)
CREATE TABLE grupo_rol (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo  TEXT NOT NULL UNIQUE,          -- GOB, ASE, LID, PRO, CON, TEC, COL, OPE, TI, EXT
    nombre  TEXT NOT NULL
);

-- Roles: 19 de Determinación 7 + 4 TI Privilegiado + 2 Externos
CREATE TABLE rol (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo              TEXT NOT NULL UNIQUE,   -- 001..603 (Det.7), TI1..TI4, EX1..EX2
    abreviatura         TEXT NOT NULL UNIQUE,   -- CM, DOS, DTG, CISO...
    denominacion        TEXT NOT NULL,          -- Denominación oficial Decisión No. 02
    grupo_id            INTEGER NOT NULL REFERENCES grupo_rol(id),
    cosecha             TEXT,                   -- 01..05 según Det.7; N/A para roles SGSI
    en_det7             INTEGER NOT NULL DEFAULT 1,  -- 1 = definido en Determinación 7
    funcion             TEXT,                   -- Función según Decisión No. 02
    mfa_requerido       TEXT NOT NULL,          -- 'Sí — obligatorio', 'Sí — sistemas críticos', 'No', 'N/A'
    riesgo_attack       TEXT NOT NULL CHECK (riesgo_attack IN ('Alto','Medio','Bajo')),
    revision_periodica  TEXT NOT NULL,          -- Trimestral, Semestral, Anual, Mensual
    ultima_revision     TEXT,                   -- fecha de la última certificación registrada
    observaciones       TEXT,
    activo              INTEGER NOT NULL DEFAULT 1   -- 0 = desactivado (baja lógica)
);

-- Categorías de sistemas/recursos
CREATE TABLE categoria_sistema (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE               -- INFRA CRÍTICA, SISTEMAS, DATOS, COMUNIC, EQUIPOS
);

-- Sistemas y recursos protegidos
CREATE TABLE sistema (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre           TEXT NOT NULL UNIQUE,
    categoria_id     INTEGER NOT NULL REFERENCES categoria_sistema(id),
    clasificacion    TEXT NOT NULL CHECK (clasificacion IN
                       ('Altamente Confidencial','Confidencial','Interna','Pública')),
    tecnicas_attack  TEXT,                     -- Técnicas MITRE ATT&CK asociadas (IDs separados por /)
    activo           INTEGER NOT NULL DEFAULT 1    -- 0 = desactivado (baja lógica)
);

-- Catálogo de técnicas MITRE ATT&CK (Enterprise) — sincronizado desde
-- static/attack_tecnicas.json por catalogo_attack.sincronizar(); ver
-- catalogo_attack_actualizar.py para regenerarlo desde el Excel de MITRE.
CREATE TABLE attack_tecnica (
    id             TEXT PRIMARY KEY,            -- p.ej. T1566 o T1566.001
    nombre         TEXT NOT NULL,
    tactica        TEXT,
    es_subtecnica  INTEGER NOT NULL DEFAULT 0,
    padre          TEXT                          -- ID de la técnica padre, si aplica
);

-- Catálogo de niveles de acceso (POL-SI-002)
CREATE TABLE nivel_acceso (
    codigo      TEXT PRIMARY KEY,              -- A, C, M, L, T, —
    nombre      TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    orden       INTEGER NOT NULL               -- para ordenar de mayor a menor privilegio
);

-- Matriz RBAC: nivel de acceso de cada rol sobre cada sistema
CREATE TABLE matriz_acceso (
    rol_id       INTEGER NOT NULL REFERENCES rol(id) ON DELETE CASCADE,
    sistema_id   INTEGER NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
    nivel_codigo TEXT NOT NULL REFERENCES nivel_acceso(codigo),
    PRIMARY KEY (rol_id, sistema_id)
);

-- Usuarios (personas) con rol asignado — accesos efectivos se derivan de la matriz
CREATE TABLE usuario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    rol_id        INTEGER NOT NULL REFERENCES rol(id),
    mfa_activo    TEXT NOT NULL DEFAULT 'No',
    nda           TEXT,                        -- NDA-001, NDA-002, NDA-004
    estado        TEXT NOT NULL DEFAULT 'Activo'
                    CHECK (estado IN ('Activo','Temporal','Suspendido','Revocado')),
    fecha_inicio  TEXT,                        -- ISO 8601; obligatoria para acceso Temporal
    fecha_fin     TEXT,                        -- obligatoria para acceso Temporal (nivel T)
    notas         TEXT,
    creado        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);


-- Excepciones de acceso por usuario: anulan el nivel que la matriz otorga al
-- rol para un sistema concreto (conceder o restringir). Deben estar
-- justificadas y, de preferencia, acotadas en el tiempo (ISO 27002 — 5.18).
CREATE TABLE acceso_excepcion (
    usuario_id   INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    sistema_id   INTEGER NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
    nivel_codigo TEXT NOT NULL REFERENCES nivel_acceso(codigo),
    motivo       TEXT NOT NULL,
    fecha_fin    TEXT,                       -- recomendada; obligatoria si amplía privilegios
    creado       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (usuario_id, sistema_id)
);

-- Bitácora de auditoría encadenada (ISO 27002:2022 — 8.15): cada registro
-- incluye el hash SHA-256 del anterior; alterar uno rompe toda la cadena.
CREATE TABLE log_auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT NOT NULL,
    entidad     TEXT NOT NULL,                 -- usuario | matriz_acceso | rol | sistema | cuenta | sesion
    accion      TEXT NOT NULL,                 -- ALTA | MODIFICACION | REVOCACION | ELIMINACION | ACCESO
    detalle     TEXT NOT NULL,
    responsable TEXT NOT NULL DEFAULT 'sistema',
    hash        TEXT NOT NULL                  -- sha256(hash_anterior|fecha|entidad|accion|detalle|responsable)
);

-- ============================================================================
-- Vistas de consulta
-- ============================================================================

-- Accesos efectivos por usuario (usuario → rol → matriz)
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

-- Roles con acceso privilegiado (A) — sujetos a revisión trimestral
CREATE VIEW v_roles_criticos AS
SELECT r.codigo, r.abreviatura, r.denominacion, s.nombre AS sistema, s.clasificacion
FROM matriz_acceso ma
JOIN rol r     ON r.id = ma.rol_id
JOIN sistema s ON s.id = ma.sistema_id
WHERE ma.nivel_codigo = 'A' AND r.activo = 1 AND s.activo = 1;

-- Alertas de cumplimiento: usuarios activos sin MFA cuyo rol lo exige
CREATE VIEW v_alertas_mfa AS
SELECT u.id, u.nombre, r.abreviatura AS rol, r.mfa_requerido, u.mfa_activo
FROM usuario u JOIN rol r ON r.id = u.rol_id
WHERE u.estado IN ('Activo','Temporal')
  AND r.mfa_requerido LIKE 'Sí%'
  AND u.mfa_activo NOT LIKE 'Sí%'
  AND r.activo = 1;

CREATE INDEX idx_matriz_sistema ON matriz_acceso(sistema_id);
CREATE INDEX idx_usuario_rol ON usuario(rol_id);
CREATE INDEX idx_log_fecha ON log_auditoria(fecha);
CREATE INDEX idx_excepcion_sistema ON acceso_excepcion(sistema_id);
CREATE INDEX idx_usuario_estado ON usuario(estado);

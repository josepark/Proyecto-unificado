"""Lógica de lectura de la API RBAC — paridad con rbac/api_rest.py (GET)."""
import csv
import io

from rbac.auditoria import verificar_cadena
from rbac.constants import (
    CLASIFICACIONES,
    DIAS_ALERTA_VENCIMIENTO,
    ESTADOS_USUARIO,
    RIESGOS_ATTACK,
)
from rbac.db_util import fetchall, fetchone, scalar
from rbac.sql_compat import (
    date_col,
    dias_hasta,
    hoy_mas_dias,
    hoy_sql,
    sql_activo,
    sql_revision_vencida,
)


def _bool(val):
    return bool(val)


def catalogos(using='rbac'):
    grupos = fetchall(
        'SELECT id, codigo, nombre FROM grupo_rol ORDER BY nombre', using=using,
    )
    categorias = fetchall(
        'SELECT id, nombre FROM categoria_sistema ORDER BY nombre', using=using,
    )
    niveles = fetchall(
        'SELECT codigo, nombre, descripcion, orden FROM nivel_acceso ORDER BY orden',
        using=using,
    )
    entidades = fetchall(
        'SELECT DISTINCT entidad FROM log_auditoria ORDER BY entidad', using=using,
    )
    acciones = fetchall(
        'SELECT DISTINCT accion FROM log_auditoria ORDER BY accion', using=using,
    )
    return {
        'grupos_rol': grupos,
        'categorias_sistema': categorias,
        'niveles_acceso': niveles,
        'riesgos_attack': list(RIESGOS_ATTACK),
        'clasificaciones': list(CLASIFICACIONES),
        'estados_usuario': list(ESTADOS_USUARIO),
        'entidades_auditoria': [r['entidad'] for r in entidades],
        'acciones_auditoria': [r['accion'] for r in acciones],
    }


def resumen(esp, using='rbac'):
    hoy = hoy_sql(using)
    roles_total = scalar(
        f'SELECT COUNT(*) n FROM rol WHERE {sql_activo("activo", using)}', using=using,
    )
    sistemas_total = scalar(
        f'SELECT COUNT(*) n FROM sistema WHERE {sql_activo("activo", using)} AND espacio_codigo=%s',
        [esp], using=using,
    )
    usuarios_activos = scalar(
        "SELECT COUNT(*) n FROM usuario WHERE estado IN ('Activo','Temporal') "
        'AND espacio_codigo=%s',
        [esp], using=using,
    )
    alertas_mfa = scalar(
        f"""SELECT COUNT(*) n FROM usuario u
           JOIN rol r ON r.id = u.rol_id
           WHERE u.estado IN ('Activo','Temporal')
             AND r.mfa_requerido LIKE 'Sí%%'
             AND u.mfa_activo NOT LIKE 'Sí%%'
             AND {sql_activo('r.activo', using)}
             AND u.espacio_codigo=%s""",
        [esp], using=using,
    )
    mfa_total = scalar(
        """SELECT COUNT(*) n FROM usuario u JOIN rol r ON r.id=u.rol_id
           WHERE u.estado IN ('Activo','Temporal') AND r.mfa_requerido LIKE 'Sí%%'
             AND u.espacio_codigo=%s""",
        [esp], using=using,
    )
    mfa_ok = mfa_total - alertas_mfa
    mfa_pct = round(100 * mfa_ok / mfa_total) if mfa_total else 100

    fin_alerta = hoy_mas_dias(DIAS_ALERTA_VENCIMIENTO, using)
    proximos_vencimientos = scalar(
        f"""SELECT COUNT(*) n FROM (
               SELECT u.id FROM usuario u
               WHERE u.estado='Temporal' AND u.fecha_fin IS NOT NULL
                 AND u.espacio_codigo=%s
                 AND {date_col('u.fecha_fin', using)} BETWEEN {hoy} AND {fin_alerta}
               UNION ALL
               SELECT e.usuario_id FROM acceso_excepcion e
               WHERE e.espacio_codigo=%s
                 AND e.fecha_fin IS NOT NULL
                 AND {date_col('e.fecha_fin', using)} BETWEEN {hoy} AND {fin_alerta}
             ) sub""",
        [esp, esp], using=using,
    )
    excepciones_vigentes = scalar(
        f"""SELECT COUNT(*) n FROM acceso_excepcion
            WHERE espacio_codigo=%s
              AND (fecha_fin IS NULL OR {date_col('fecha_fin', using)} >= {hoy})""",
        [esp], using=using,
    )
    excepciones_vencidas = scalar(
        f"""SELECT COUNT(*) n FROM acceso_excepcion
            WHERE espacio_codigo=%s AND fecha_fin IS NOT NULL
              AND {date_col('fecha_fin', using)} < {hoy}""",
        [esp], using=using,
    )
    rev_venc = sql_revision_vencida('r', using)
    roles_certificacion_vencida = scalar(
        f'SELECT COUNT(*) n FROM rol r WHERE {sql_activo("r.activo", using)} AND {rev_venc} = 1',
        using=using,
    )
    pendientes_total = (
        proximos_vencimientos + excepciones_vencidas
        + roles_certificacion_vencida + alertas_mfa
    )
    return {
        'roles_total': roles_total,
        'sistemas_total': sistemas_total,
        'usuarios_activos': usuarios_activos,
        'mfa_pct': mfa_pct,
        'mfa_ok': mfa_ok,
        'mfa_total': mfa_total,
        'proximos_vencimientos': proximos_vencimientos,
        'excepciones_vigentes': excepciones_vigentes,
        'excepciones_vencidas': excepciones_vencidas,
        'roles_certificacion_vencida': roles_certificacion_vencida,
        'alertas_mfa': alertas_mfa,
        'pendientes_total': pendientes_total,
        'desglose_pendientes': {
            'proximos_vencimientos': proximos_vencimientos,
            'excepciones_vencidas': excepciones_vencidas,
            'roles_certificacion_vencida': roles_certificacion_vencida,
            'alertas_mfa': alertas_mfa,
        },
    }


def inicio(esp, using='rbac'):
    hoy = hoy_sql(using)
    fin_alerta = hoy_mas_dias(DIAS_ALERTA_VENCIMIENTO, using)
    stats = {
        'roles': scalar('SELECT COUNT(*) n FROM rol', using=using),
        'sistemas': scalar(
            'SELECT COUNT(*) n FROM sistema WHERE espacio_codigo=%s', [esp], using=using,
        ),
        'usuarios': scalar(
            "SELECT COUNT(*) n FROM usuario WHERE estado IN ('Activo','Temporal') "
            'AND espacio_codigo=%s',
            [esp], using=using,
        ),
        'accesos': scalar(
            """SELECT COUNT(*) n FROM matriz_acceso ma
               JOIN sistema s ON s.id = ma.sistema_id
               WHERE ma.nivel_codigo<>'—' AND s.espacio_codigo=%s""",
            [esp], using=using,
        ),
    }
    alertas_mfa = fetchall(
        f"""SELECT u.id, u.nombre, r.abreviatura AS rol, r.mfa_requerido, u.mfa_activo
           FROM usuario u
           JOIN rol r ON r.id = u.rol_id
           WHERE u.estado IN ('Activo','Temporal')
             AND r.mfa_requerido LIKE 'Sí%%'
             AND u.mfa_activo NOT LIKE 'Sí%%'
             AND {sql_activo('r.activo', using)}
             AND u.espacio_codigo=%s""",
        [esp], using=using,
    )
    criticos = fetchall(
        """SELECT r.abreviatura, r.denominacion, COUNT(*) n_admin
           FROM matriz_acceso ma JOIN rol r ON r.id = ma.rol_id
           JOIN sistema s ON s.id = ma.sistema_id
           WHERE ma.nivel_codigo='A' AND s.espacio_codigo=%s
           GROUP BY r.id, r.abreviatura, r.denominacion ORDER BY n_admin DESC""",
        [esp], using=using,
    )
    temporales = fetchall(
        "SELECT u.nombre, r.abreviatura rol, u.fecha_fin FROM usuario u "
        "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Temporal' AND u.espacio_codigo=%s",
        [esp], using=using,
    )
    revocados = fetchall(
        "SELECT u.nombre, r.abreviatura rol, u.notas FROM usuario u "
        "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Revocado' AND u.espacio_codigo=%s",
        [esp], using=using,
    )
    log = fetchall(
        'SELECT id, fecha, entidad, accion, detalle, responsable, hash '
        'FROM log_auditoria ORDER BY id DESC LIMIT 8',
        using=using,
    )
    riesgo_roles = {
        r['riesgo_attack']: r['n']
        for r in fetchall(
            f'SELECT riesgo_attack, COUNT(*) n FROM rol WHERE {sql_activo("activo", using)} GROUP BY riesgo_attack',
            using=using,
        )
    }
    riesgo = [
        {'nombre': 'Alto', 'n': riesgo_roles.get('Alto', 0), 'color': '#e0475a'},
        {'nombre': 'Medio', 'n': riesgo_roles.get('Medio', 0), 'color': '#e0812f'},
        {'nombre': 'Bajo', 'n': riesgo_roles.get('Bajo', 0), 'color': '#4bab7c'},
    ]
    max_riesgo = max((x['n'] for x in riesgo), default=0) or 1
    mfa_total = scalar(
        """SELECT COUNT(*) n FROM usuario u JOIN rol r ON r.id=u.rol_id
           WHERE u.estado IN ('Activo','Temporal') AND r.mfa_requerido LIKE 'Sí%%'
             AND u.espacio_codigo=%s""",
        [esp], using=using,
    )
    mfa_ok = mfa_total - len(alertas_mfa)
    mfa_pct = round(100 * mfa_ok / mfa_total) if mfa_total else 100
    proximos_vencimientos = fetchall(
        f"""SELECT 'Usuario temporal' tipo, u.nombre nombre,
                   r.abreviatura contexto, u.fecha_fin,
                   {dias_hasta('u.fecha_fin', using)} dias
            FROM usuario u JOIN rol r ON r.id=u.rol_id
            WHERE u.estado='Temporal' AND u.fecha_fin IS NOT NULL
              AND u.espacio_codigo=%s
              AND {date_col('u.fecha_fin', using)} BETWEEN {hoy} AND {fin_alerta}
            UNION ALL
            SELECT 'Excepción de acceso' tipo, us.nombre nombre,
                   s.nombre contexto, e.fecha_fin,
                   {dias_hasta('e.fecha_fin', using)} dias
            FROM acceso_excepcion e
            JOIN usuario us ON us.id=e.usuario_id
            JOIN sistema s ON s.id=e.sistema_id
            WHERE e.espacio_codigo=%s
              AND e.fecha_fin IS NOT NULL
              AND {date_col('e.fecha_fin', using)} BETWEEN {hoy} AND {fin_alerta}
            ORDER BY fecha_fin""",
        [esp, esp], using=using,
    )
    return {
        'stats': stats,
        'alertas_mfa': alertas_mfa,
        'criticos': criticos,
        'temporales': temporales,
        'revocados': revocados,
        'log': log,
        'riesgo': riesgo,
        'max_riesgo': max_riesgo,
        'mfa_pct': mfa_pct,
        'mfa_ok': mfa_ok,
        'mfa_total': mfa_total,
        'proximos_vencimientos': proximos_vencimientos,
        'dias_alerta': DIAS_ALERTA_VENCIMIENTO,
    }


def listar_roles(q='', incluir_inactivos=False, using='rbac'):
    rev_venc = sql_revision_vencida('r', using)
    sql = (
        f'SELECT r.*, g.nombre grupo, {rev_venc} revision_vencida '
        'FROM rol r JOIN grupo_rol g ON g.id = r.grupo_id WHERE 1=1'
    )
    params = []
    if not incluir_inactivos:
        sql += f' AND {sql_activo("r.activo", using)}'
    if q:
        sql += ' AND (r.abreviatura LIKE %s OR r.denominacion LIKE %s OR r.codigo LIKE %s)'
        params += [f'%{q}%'] * 3
    sql += ' ORDER BY r.abreviatura'
    return fetchall(sql, params, using=using)


def obtener_rol(rid, esp, using='rbac'):
    rev_venc = sql_revision_vencida('r', using)
    rol = fetchone(
        f'SELECT r.*, g.nombre grupo, {rev_venc} revision_vencida '
        'FROM rol r JOIN grupo_rol g ON g.id=r.grupo_id WHERE r.id=%s',
        [rid], using=using,
    )
    if not rol:
        return None
    accesos = fetchall(
        """SELECT s.id sistema_id, s.nombre, s.clasificacion, cat.nombre categoria,
                  ma.nivel_codigo nivel, n.nombre nivel_nombre
           FROM matriz_acceso ma
           JOIN sistema s ON s.id=ma.sistema_id
           JOIN categoria_sistema cat ON cat.id=s.categoria_id
           JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
           WHERE ma.rol_id=%s AND ma.nivel_codigo<>'—' AND s.espacio_codigo=%s
           ORDER BY n.orden, s.id""",
        [rid, esp], using=using,
    )
    usuarios = fetchall(
        'SELECT * FROM usuario WHERE rol_id=%s AND espacio_codigo=%s '
        'ORDER BY estado, nombre',
        [rid, esp], using=using,
    )
    rol['accesos'] = accesos
    rol['usuarios'] = usuarios
    return rol


def listar_sistemas(esp, q='', categoria='', clasificacion='', incluir_inactivos=False, using='rbac'):
    hoy = hoy_sql(using)
    sql = """SELECT s.*, cs.nombre categoria,
                    (SELECT COUNT(*) FROM matriz_acceso ma
                     WHERE ma.sistema_id = s.id AND ma.nivel_codigo <> '—') n_roles
             FROM sistema s
             JOIN categoria_sistema cs ON cs.id = s.categoria_id
             WHERE s.espacio_codigo = %s"""
    params = [esp]
    if not incluir_inactivos:
        sql += f' AND {sql_activo("s.activo", using)}'
    if q:
        sql += ' AND s.nombre LIKE %s'
        params.append(f'%{q}%')
    if categoria:
        sql += ' AND s.categoria_id = %s'
        params.append(categoria)
    if clasificacion in CLASIFICACIONES:
        sql += ' AND s.clasificacion = %s'
        params.append(clasificacion)
    sql += ' ORDER BY s.id'
    sistemas = fetchall(sql, params, using=using)

    accesos = fetchall(
        f"""SELECT ma.sistema_id, r.abreviatura rol, r.denominacion,
                  ma.nivel_codigo nivel
           FROM matriz_acceso ma
           JOIN rol r ON r.id = ma.rol_id
           JOIN sistema s ON s.id = ma.sistema_id
           WHERE ma.nivel_codigo <> '—' AND {sql_activo('r.activo', using)} AND s.espacio_codigo = %s""",
        [esp], using=using,
    )
    por_sistema = {}
    for a in accesos:
        por_sistema.setdefault(a['sistema_id'], []).append({
            'rol': a['rol'],
            'denominacion': a['denominacion'],
            'nivel': a['nivel'],
        })
    excepciones_vigentes = {
        r['sistema_id']: r['n']
        for r in fetchall(
            f"""SELECT sistema_id, COUNT(*) n FROM acceso_excepcion
                WHERE espacio_codigo = %s
                  AND (fecha_fin IS NULL OR {date_col('fecha_fin', using)} >= {hoy})
                GROUP BY sistema_id""",
            [esp], using=using,
        )
    }
    return [
        {
            'id': s['id'],
            'nombre': s['nombre'],
            'categoria': s['categoria'],
            'categoria_id': s['categoria_id'],
            'clasificacion': s['clasificacion'],
            'tecnicas_attack': s['tecnicas_attack'],
            'activo': _bool(s['activo']),
            'n_roles': s['n_roles'],
            'accesos': por_sistema.get(s['id'], []),
            'excepciones_vigentes': excepciones_vigentes.get(s['id'], 0),
        }
        for s in sistemas
    ]


def obtener_sistema(sid, esp, using='rbac'):
    hoy = hoy_sql(using)
    sis = fetchone(
        'SELECT s.*, c.nombre categoria FROM sistema s '
        'JOIN categoria_sistema c ON c.id=s.categoria_id '
        'WHERE s.id=%s AND s.espacio_codigo=%s',
        [sid, esp], using=using,
    )
    if not sis:
        return None
    roles_acc = fetchall(
        f"""SELECT r.id, r.abreviatura, r.denominacion, ma.nivel_codigo nivel,
                  n.nombre nivel_nombre
           FROM matriz_acceso ma
           JOIN rol r ON r.id=ma.rol_id
           JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
           WHERE ma.sistema_id=%s AND ma.nivel_codigo<>'—' AND {sql_activo('r.activo', using)}
           ORDER BY n.orden, r.id""",
        [sid], using=using,
    )
    usuarios = fetchall(
        f"""SELECT u.nombre, u.estado, r.abreviatura rol,
                   COALESCE(e.nivel_codigo, ma.nivel_codigo) nivel,
                   CASE WHEN e.usuario_id IS NOT NULL THEN 1 ELSE 0 END es_excepcion
            FROM usuario u
            JOIN rol r ON r.id=u.rol_id
            JOIN matriz_acceso ma ON ma.rol_id=r.id AND ma.sistema_id=%s
            LEFT JOIN acceso_excepcion e ON e.usuario_id=u.id
                 AND e.sistema_id=%s
                 AND (e.fecha_fin IS NULL OR {date_col('e.fecha_fin', using)} >= {hoy})
            WHERE COALESCE(e.nivel_codigo, ma.nivel_codigo) <> '—'
              AND u.estado IN ('Activo','Temporal') AND {sql_activo('r.activo', using)}
              AND u.espacio_codigo=%s
            ORDER BY u.nombre""",
        [sid, sid, esp], using=using,
    )
    sis['roles'] = roles_acc
    sis['usuarios'] = usuarios
    return sis


def listar_usuarios(esp, q='', estado='', rol='', using='rbac'):
    hoy = hoy_sql(using)
    sql = f"""SELECT u.*, r.abreviatura rol, r.denominacion, r.mfa_requerido,
                     (SELECT COUNT(*) FROM matriz_acceso ma
                      JOIN sistema s ON s.id = ma.sistema_id
                      LEFT JOIN acceso_excepcion e ON e.usuario_id = u.id
                           AND e.sistema_id = s.id
                           AND (e.fecha_fin IS NULL OR {date_col('e.fecha_fin', using)} >= {hoy})
                      WHERE ma.rol_id = u.rol_id
                        AND COALESCE(e.nivel_codigo, ma.nivel_codigo) <> '—'
                        AND {sql_activo('s.activo', using)} AND s.espacio_codigo = u.espacio_codigo
                        AND u.estado IN ('Activo','Temporal')) n_sistemas,
                     (SELECT COUNT(*) FROM acceso_excepcion e
                      WHERE e.usuario_id = u.id) n_excepciones
              FROM usuario u JOIN rol r ON r.id=u.rol_id
              WHERE u.espacio_codigo=%s"""
    params = [esp]
    if q:
        sql += ' AND (u.nombre LIKE %s OR r.abreviatura LIKE %s OR r.denominacion LIKE %s)'
        params += [f'%{q}%'] * 3
    if estado in ESTADOS_USUARIO:
        sql += ' AND u.estado=%s'
        params.append(estado)
    if rol:
        sql += ' AND u.rol_id=%s'
        params.append(rol)
    sql += (
        " ORDER BY CASE u.estado WHEN 'Activo' THEN 0 WHEN 'Temporal' THEN 1 "
        "WHEN 'Suspendido' THEN 2 ELSE 3 END, u.nombre"
    )
    return fetchall(sql, params, using=using)


def obtener_usuario(uid, esp, using='rbac'):
    u = fetchone(
        'SELECT u.*, r.abreviatura rol_abrev, r.denominacion, r.mfa_requerido '
        'FROM usuario u JOIN rol r ON r.id=u.rol_id '
        'WHERE u.id=%s AND u.espacio_codigo=%s',
        [uid, esp], using=using,
    )
    if not u:
        return None
    accesos = fetchall(
        f"""SELECT s.id sistema_id, s.nombre, cat.nombre categoria,
                  s.clasificacion, ma.nivel_codigo nivel_rol,
                  e.nivel_codigo nivel_exc, e.motivo, e.fecha_fin exc_fin,
                  COALESCE(e.nivel_codigo, ma.nivel_codigo) nivel_efectivo
           FROM sistema s
           JOIN categoria_sistema cat ON cat.id = s.categoria_id
           JOIN matriz_acceso ma ON ma.sistema_id = s.id
                AND ma.rol_id = (SELECT rol_id FROM usuario WHERE id=%s)
           LEFT JOIN acceso_excepcion e
                  ON e.usuario_id = %s AND e.sistema_id = s.id
           WHERE {sql_activo('s.activo', using)} AND s.espacio_codigo=%s
           ORDER BY cat.id, s.id""",
        [uid, uid, esp], using=using,
    )
    u['accesos'] = accesos
    return u


def matriz(esp, grupo='', categoria='', using='rbac'):
    q_rol = (
        'SELECT r.*, g.nombre grupo, g.codigo gcod FROM rol r '
        f'JOIN grupo_rol g ON g.id=r.grupo_id WHERE {sql_activo("r.activo", using)}'
    )
    params = []
    if grupo:
        q_rol += ' AND g.codigo=%s'
        params.append(grupo)
    roles = fetchall(q_rol + ' ORDER BY r.id', params, using=using)

    q_sis = (
        'SELECT s.*, c.nombre categoria FROM sistema s '
        'JOIN categoria_sistema c ON c.id=s.categoria_id '
        f'WHERE {sql_activo("s.activo", using)} AND s.espacio_codigo=%s'
    )
    p2 = [esp]
    if categoria:
        q_sis += ' AND c.nombre=%s'
        p2.append(categoria)
    sistemas = fetchall(q_sis + ' ORDER BY s.id', p2, using=using)
    sis_ids = {s['id'] for s in sistemas}
    celdas = {
        f"{m['rol_id']}:{m['sistema_id']}": m['nivel_codigo']
        for m in fetchall('SELECT rol_id, sistema_id, nivel_codigo FROM matriz_acceso', using=using)
        if m['sistema_id'] in sis_ids
    }
    niveles = fetchall('SELECT * FROM nivel_acceso ORDER BY orden', using=using)
    return {'roles': roles, 'sistemas': sistemas, 'celdas': celdas, 'niveles': niveles}


def matriz_heatmap(esp, using='rbac'):
    return fetchall(
        f"""SELECT cat.nombre categoria,
                  COUNT(DISTINCT s.id) sistemas,
                  SUM(CASE WHEN ma.nivel_codigo='A' THEN 1 ELSE 0 END) n_admin,
                  SUM(CASE WHEN ma.nivel_codigo NOT IN ('—','L') THEN 1 ELSE 0 END) n_elevados
           FROM sistema s
           JOIN categoria_sistema cat ON cat.id = s.categoria_id
           JOIN matriz_acceso ma ON ma.sistema_id = s.id
           JOIN rol r ON r.id = ma.rol_id AND {sql_activo('r.activo', using)}
           WHERE {sql_activo('s.activo', using)} AND s.espacio_codigo=%s
           GROUP BY cat.id, cat.nombre ORDER BY n_admin DESC, cat.nombre""",
        [esp], using=using,
    )


def matriz_comparar(esp, rol_a_id, rol_b_id, using='rbac'):
    rol_a = fetchone(
        'SELECT id, abreviatura, denominacion FROM rol WHERE id=%s',
        [rol_a_id], using=using,
    )
    rol_b = fetchone(
        'SELECT id, abreviatura, denominacion FROM rol WHERE id=%s',
        [rol_b_id], using=using,
    )
    if not rol_a or not rol_b:
        return None
    niveles_a = {
        m['sistema_id']: m['nivel_codigo']
        for m in fetchall(
            'SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=%s',
            [rol_a_id], using=using,
        )
    }
    niveles_b = {
        m['sistema_id']: m['nivel_codigo']
        for m in fetchall(
            'SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=%s',
            [rol_b_id], using=using,
        )
    }
    sistemas = fetchall(
        f"""SELECT s.id, s.nombre, cat.nombre categoria FROM sistema s
           JOIN categoria_sistema cat ON cat.id=s.categoria_id
           WHERE {sql_activo('s.activo', using)} AND s.espacio_codigo=%s
           ORDER BY cat.nombre, s.nombre""",
        [esp], using=using,
    )
    filas = []
    for s in sistemas:
        na = niveles_a.get(s['id'], '—')
        nb = niveles_b.get(s['id'], '—')
        filas.append({
            'sistema': s['nombre'],
            'categoria': s['categoria'],
            'nivel_a': na,
            'nivel_b': nb,
            'difiere': na != nb,
        })
    return {
        'rol_a': rol_a,
        'rol_b': rol_b,
        'filas': filas,
        'num_diferencias': sum(1 for f in filas if f['difiere']),
    }


def listar_excepciones(esp, incluir_vencidas=False, using='rbac'):
    hoy = hoy_sql(using)
    sql = f"""SELECT u.id usuario_id, u.nombre usuario, u.estado usuario_estado,
                     s.id sistema_id, s.nombre sistema, r.abreviatura rol,
                     COALESCE(ma.nivel_codigo, '—') nivel_rol,
                     e.nivel_codigo nivel_excepcion, e.motivo, e.fecha_fin, e.creado,
                     CASE WHEN e.fecha_fin IS NOT NULL
                               AND {date_col('e.fecha_fin', using)} < {hoy}
                          THEN 1 ELSE 0 END vencida
              FROM acceso_excepcion e
              JOIN usuario u ON u.id = e.usuario_id
              JOIN sistema s ON s.id = e.sistema_id
              JOIN rol r ON r.id = u.rol_id
              LEFT JOIN matriz_acceso ma
                     ON ma.rol_id = u.rol_id AND ma.sistema_id = e.sistema_id
              WHERE e.espacio_codigo=%s"""
    params = [esp]
    if not incluir_vencidas:
        sql += f' AND (e.fecha_fin IS NULL OR {date_col("e.fecha_fin", using)} >= {hoy})'
    sql += f""" ORDER BY
              CASE WHEN e.fecha_fin IS NOT NULL AND {date_col('e.fecha_fin', using)} < {hoy}
                   THEN 1 ELSE 0 END DESC,
              e.fecha_fin IS NULL, e.fecha_fin, u.nombre"""
    filas = fetchall(sql, params, using=using)
    for f in filas:
        f['vencida'] = _bool(f['vencida'])
    total_vigentes = scalar(
        f"""SELECT COUNT(*) n FROM acceso_excepcion
            WHERE espacio_codigo=%s
              AND (fecha_fin IS NULL OR {date_col('fecha_fin', using)} >= {hoy})""",
        [esp], using=using,
    )
    total_vencidas = scalar(
        f"""SELECT COUNT(*) n FROM acceso_excepcion
            WHERE espacio_codigo=%s AND fecha_fin IS NOT NULL
              AND {date_col('fecha_fin', using)} < {hoy}""",
        [esp], using=using,
    )
    return {
        'filas': filas,
        'total_vigentes': total_vigentes,
        'total_vencidas': total_vencidas,
    }


def auditoria(entidad='', accion='', q='', pagina=1, limite=50, using='rbac'):
    pagina = max(1, pagina)
    por_pagina = max(1, min(limite, 500))
    where = ' WHERE 1=1'
    params = []
    if entidad:
        where += ' AND entidad=%s'
        params.append(entidad)
    if accion:
        where += ' AND accion=%s'
        params.append(accion)
    if q:
        where += ' AND (detalle LIKE %s OR responsable LIKE %s)'
        params += [f'%{q}%', f'%{q}%']
    total = scalar(f'SELECT COUNT(*) n FROM log_auditoria{where}', params, using=using)
    offset = (pagina - 1) * por_pagina
    registros = fetchall(
        'SELECT id, fecha, entidad, accion, detalle, responsable, hash '
        f'FROM log_auditoria{where} ORDER BY id DESC LIMIT %s OFFSET %s',
        params + [por_pagina, offset],
        using=using,
    )
    return {
        'registros': registros,
        'total': total,
        'pagina': pagina,
        'total_paginas': max(1, -(-total // por_pagina)),
    }


def auditoria_verificar(using='rbac'):
    ok, dato = verificar_cadena(using=using)
    return {'integra': ok, 'detalle': dato}


def export_matriz_csv(esp, using='rbac'):
    roles = fetchall('SELECT id, abreviatura FROM rol ORDER BY id', using=using)
    sistemas = fetchall(
        'SELECT id, nombre FROM sistema WHERE espacio_codigo=%s ORDER BY id',
        [esp], using=using,
    )
    celdas = {
        (m['rol_id'], m['sistema_id']): m['nivel_codigo']
        for m in fetchall('SELECT rol_id, sistema_id, nivel_codigo FROM matriz_acceso', using=using)
    }
    encabezados = ['Sistema'] + [r['abreviatura'] for r in roles]
    filas = [
        [s['nombre']] + [celdas.get((r['id'], s['id']), '—') for r in roles]
        for s in sistemas
    ]
    return _csv_bytes('SUIIN-SGSI-MCA-001_matriz.csv', encabezados, filas)


def export_accesos_csv(esp, using='rbac'):
    hoy = hoy_sql(using)
    filas = fetchall(
        f"""SELECT u.nombre usuario, u.estado, r.abreviatura rol, s.nombre sistema,
                   cat.nombre categoria, s.clasificacion,
                   COALESCE(e.nivel_codigo, ma.nivel_codigo) nivel,
                   CASE WHEN e.usuario_id IS NOT NULL THEN 'Sí' ELSE '' END excepcion
            FROM usuario u
            JOIN rol r ON r.id = u.rol_id
            JOIN matriz_acceso ma ON ma.rol_id = r.id
            JOIN sistema s ON s.id = ma.sistema_id
            JOIN categoria_sistema cat ON cat.id = s.categoria_id
            LEFT JOIN acceso_excepcion e ON e.usuario_id = u.id AND e.sistema_id = s.id
                 AND (e.fecha_fin IS NULL OR {date_col('e.fecha_fin', using)} >= {hoy})
            WHERE COALESCE(e.nivel_codigo, ma.nivel_codigo) <> '—'
              AND u.estado IN ('Activo','Temporal') AND {sql_activo('r.activo', using)} AND {sql_activo('s.activo', using)}
              AND u.espacio_codigo = %s AND s.espacio_codigo = %s
            ORDER BY u.nombre, s.nombre""",
        [esp, esp], using=using,
    )
    encabezados = [
        'Usuario', 'Estado', 'Rol', 'Sistema', 'Categoría',
        'Clasificación', 'Nivel', 'Excepción',
    ]
    return _csv_bytes(
        'SUIIN-SGSI-MCA-001_accesos_efectivos.csv',
        encabezados,
        [[f['usuario'], f['estado'], f['rol'], f['sistema'], f['categoria'],
          f['clasificacion'], f['nivel'], f['excepcion']] for f in filas],
    )


def _celda_segura(valor):
    txt = '' if valor is None else str(valor)
    if txt and txt[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + txt
    return txt


def _csv_bytes(nombre, encabezados, filas):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow([_celda_segura(h) for h in encabezados])
    writer.writerows([[_celda_segura(v) for v in fila] for fila in filas])
    contenido = '\ufeff' + buf.getvalue()
    return nombre, contenido

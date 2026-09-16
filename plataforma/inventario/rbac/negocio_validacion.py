"""Validaciones de negocio — paridad con rbac/negocio.py."""
import csv
import io
from datetime import datetime

from rbac.constants import CLASIFICACIONES, ESTADOS_USUARIO, RIESGOS_ATTACK
from rbac.db_util import fetchall, fetchone, rbac_cursor, scalar


def fecha_valida(txt):
    if not txt:
        return True
    try:
        datetime.strptime(txt, '%Y-%m-%d')
        return True
    except (TypeError, ValueError):
        return False


def _valor_str(body, key, default=''):
    val = body.get(key, default)
    if val is None:
        return default
    return str(val).strip() if not isinstance(val, str) else val.strip()


def _valor_bool01(body, key):
    val = body.get(key)
    if val in (True, 1, '1', 'true', 'True'):
        return True
    return False


def validar_datos_rol(body, using='rbac'):
    codigo = _valor_str(body, 'codigo')
    abreviatura = _valor_str(body, 'abreviatura').upper()
    denominacion = _valor_str(body, 'denominacion')
    if not codigo or not abreviatura or not denominacion:
        return None, 'El código, la abreviatura y la denominación son obligatorios.'
    try:
        grupo_id = int(body.get('grupo_id'))
    except (TypeError, ValueError):
        return None, 'Seleccione un grupo de rol válido.'
    if not fetchone('SELECT 1 n FROM grupo_rol WHERE id=%s', [grupo_id], using=using):
        return None, 'Seleccione un grupo de rol válido.'
    riesgo = body.get('riesgo_attack', '')
    if riesgo not in RIESGOS_ATTACK:
        return None, 'Seleccione un nivel de riesgo ATT&CK válido (Alto/Medio/Bajo).'
    mfa = _valor_str(body, 'mfa_requerido')
    revision = _valor_str(body, 'revision_periodica')
    if not mfa or not revision:
        return None, 'El requisito de MFA y la periodicidad de revisión son obligatorios.'
    return {
        'codigo': codigo,
        'abreviatura': abreviatura,
        'denominacion': denominacion,
        'grupo_id': grupo_id,
        'cosecha': _valor_str(body, 'cosecha') or None,
        'en_det7': _valor_bool01(body, 'en_det7'),
        'funcion': _valor_str(body, 'funcion') or None,
        'mfa_requerido': mfa,
        'riesgo_attack': riesgo,
        'revision_periodica': revision,
        'observaciones': _valor_str(body, 'observaciones') or None,
    }, None


def validar_datos_sistema(body, using='rbac', crear_categoria=False):
    nombre = _valor_str(body, 'nombre')
    if not nombre:
        return None, 'El nombre del sistema o recurso es obligatorio.'
    clasificacion = body.get('clasificacion', '')
    if clasificacion not in CLASIFICACIONES:
        return None, 'Seleccione una clasificación válida.'
    cat_nueva = _valor_str(body, 'categoria_nueva')
    if cat_nueva:
        fila = fetchone(
            'SELECT id FROM categoria_sistema WHERE nombre=%s', [cat_nueva], using=using,
        )
        if fila:
            cat_id = fila['id']
        elif crear_categoria:
            from rbac.models import CategoriaSistema
            cat, _ = CategoriaSistema.objects.using(using).get_or_create(nombre=cat_nueva)
            cat_id = cat.pk
        else:
            return None, 'Seleccione una categoría válida o indique una nueva.'
    else:
        try:
            cat_id = int(body.get('categoria_id'))
        except (TypeError, ValueError):
            return None, 'Seleccione una categoría válida o indique una nueva.'
        if not fetchone('SELECT 1 n FROM categoria_sistema WHERE id=%s', [cat_id], using=using):
            return None, 'Seleccione una categoría válida o indique una nueva.'

    tecnicas_raw = _valor_str(body, 'tecnicas_attack')
    codigos = [t.strip().upper() for t in tecnicas_raw.split('/') if t.strip()]
    if codigos:
        placeholders = ','.join(['%s'] * len(codigos))
        reconocidos = {
            r['id'] for r in fetchall(
                f'SELECT id FROM attack_tecnica WHERE id IN ({placeholders})',
                codigos, using=using,
            )
        }
        desconocidos = [c for c in codigos if c not in reconocidos]
        if desconocidos:
            return None, (
                'Técnica(s) ATT&CK no reconocida(s) del catálogo: '
                f"{', '.join(desconocidos)}."
            )
    return {
        'nombre': nombre,
        'categoria_id': cat_id,
        'clasificacion': clasificacion,
        'tecnicas_attack': '/'.join(codigos) or None,
    }, None


def validar_datos_usuario(body, using='rbac', uid_actual=None):
    nombre = _valor_str(body, 'nombre')
    if not nombre:
        return None, 'El nombre completo es obligatorio.'
    try:
        rol_id = int(body.get('rol_id'))
    except (TypeError, ValueError):
        return None, 'Seleccione un rol válido.'
    rol = fetchone('SELECT id, activo FROM rol WHERE id=%s', [rol_id], using=using)
    if not rol or (uid_actual is None and not rol['activo']):
        return None, 'Seleccione un rol activo válido.'
    estado = body.get('estado', 'Activo')
    if estado not in ESTADOS_USUARIO:
        return None, 'Estado no reconocido.'
    fecha_inicio = body.get('fecha_inicio') or None
    fecha_fin = body.get('fecha_fin') or None
    if not fecha_valida(fecha_inicio) or not fecha_valida(fecha_fin):
        return None, 'Las fechas deben tener el formato AAAA-MM-DD.'
    if estado == 'Temporal':
        if not fecha_inicio or not fecha_fin:
            return None, 'El acceso Temporal requiere fecha de inicio y de fin.'
        if fecha_fin < fecha_inicio:
            return None, 'La fecha de fin no puede ser anterior a la de inicio.'
    elif fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
        return None, 'La fecha de fin no puede ser anterior a la de inicio.'
    return {
        'nombre': nombre,
        'rol_id': rol_id,
        'estado': estado,
        'mfa_activo': body.get('mfa_activo', 'No'),
        'nda': body.get('nda') or None,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'notas': _valor_str(body, 'notas') or None,
    }, None


def analizar_importacion_matriz(texto, using='rbac'):
    filas_csv = list(csv.reader(io.StringIO(texto), delimiter=';'))
    if not filas_csv:
        return None, 'El archivo está vacío.'

    encabezado, datos = filas_csv[0], filas_csv[1:]
    roles_por_abrev = {
        r['abreviatura']: r['id']
        for r in fetchall('SELECT id, abreviatura FROM rol WHERE activo=1', using=using)
    }
    sistemas_por_nombre = {
        s['nombre']: s['id']
        for s in fetchall('SELECT id, nombre FROM sistema WHERE activo=1', using=using)
    }
    niveles_validos = {
        n['codigo'] for n in fetchall('SELECT codigo FROM nivel_acceso', using=using)
    }
    actuales = {
        (m['rol_id'], m['sistema_id']): m['nivel_codigo']
        for m in fetchall('SELECT rol_id, sistema_id, nivel_codigo FROM matriz_acceso', using=using)
    }

    columnas, errores = [], []
    for i, abrev in enumerate(encabezado[1:], start=1):
        abrev = abrev.strip()
        if abrev in roles_por_abrev:
            columnas.append((i, roles_por_abrev[abrev], abrev))
        else:
            errores.append(
                f'Columna «{abrev}»: no coincide con ningún rol activo; se ignoró toda la columna.'
            )

    cambios = []
    for fila in datos:
        if not fila or not fila[0].strip():
            continue
        nombre_sis = fila[0].strip()
        sid = sistemas_por_nombre.get(nombre_sis)
        if sid is None:
            errores.append(
                f'Sistema «{nombre_sis}»: no coincide con ningún sistema activo; se ignoró la fila.'
            )
            continue
        for i, rid, abrev in columnas:
            if i >= len(fila):
                continue
            nivel = fila[i].strip()
            if not nivel:
                continue
            if nivel not in niveles_validos:
                errores.append(
                    f'«{nombre_sis}» × {abrev}: valor «{nivel}» no es un nivel válido; '
                    'se ignoró esa celda.'
                )
                continue
            actual = actuales.get((rid, sid), '—')
            if nivel != actual:
                cambios.append({
                    'rol_id': rid,
                    'rol': abrev,
                    'sistema_id': sid,
                    'sistema': nombre_sis,
                    'actual': actual,
                    'nuevo': nivel,
                })

    if len(errores) > 50:
        errores = errores[:50] + [f'… y {len(errores) - 50} advertencia(s) más.']
    return (cambios, errores), None


def aplicar_importacion_matriz(cambios, audit_fn, using='rbac'):
    aplicados, detalle_partes = 0, []
    for item in cambios:
        try:
            rid = int(item['rol_id'])
            sid = int(item['sistema_id'])
        except (TypeError, ValueError, KeyError):
            continue
        nivel = item.get('nuevo', '')
        if not fetchone('SELECT 1 n FROM nivel_acceso WHERE codigo=%s', [nivel], using=using):
            continue
        rol = fetchone('SELECT abreviatura FROM rol WHERE id=%s', [rid], using=using)
        sis = fetchone('SELECT nombre FROM sistema WHERE id=%s', [sid], using=using)
        if not rol or not sis:
            continue
        with rbac_cursor(using) as cursor:
            cursor.execute(
                'UPDATE matriz_acceso SET nivel_codigo=%s WHERE rol_id=%s AND sistema_id=%s',
                [nivel, rid, sid],
            )
        aplicados += 1
        if len(detalle_partes) < 30:
            detalle_partes.append(f"{rol['abreviatura']}×{sis['nombre']}→{nivel}")
    if aplicados:
        detalle = f'Importación CSV: {aplicados} cambio(s) aplicado(s): ' + '; '.join(detalle_partes)
        if aplicados > len(detalle_partes):
            detalle += f'; … y {aplicados - len(detalle_partes)} más.'
        audit_fn('matriz_acceso', 'IMPORTACION', detalle)
    return aplicados

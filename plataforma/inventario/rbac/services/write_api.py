"""Operaciones de escritura — paridad con rbac/api_rest.py (POST/PUT/DELETE)."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from rbac import auditoria
from rbac.constants import ESTADOS_USUARIO
from rbac.db_util import fetchone, rbac_cursor, scalar
from rbac.models import AccesoExcepcion, Usuario
from rbac.negocio_validacion import (
    analizar_importacion_matriz,
    aplicar_importacion_matriz,
    validar_datos_rol,
    validar_datos_sistema,
    validar_datos_usuario,
)


class WriteError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status
        super().__init__(detail)


def _audit(entidad, accion, detalle, responsable):
    auditoria.registrar(entidad, accion, detalle, responsable=responsable)


def _mfa_aviso(rol_row, mfa_activo):
    return (
        str(rol_row.get('mfa_requerido', '')).startswith('Sí')
        and not str(mfa_activo).startswith('Sí')
    )


def crear_rol(body, responsable, using='rbac'):
    datos, error = validar_datos_rol(body, using=using)
    if error:
        raise WriteError(error)
    clonar_raw = str(body.get('clonar_de') or '').strip()
    clonar_de = None
    rol_origen = None
    if clonar_raw:
        try:
            clonar_de = int(clonar_raw)
        except (TypeError, ValueError):
            raise WriteError('El rol a clonar no es válido.')
        rol_origen = fetchone(
            'SELECT abreviatura FROM rol WHERE id=%s', [clonar_de], using=using,
        )
        if not rol_origen:
            raise WriteError('El rol elegido para clonar ya no existe.')

    try:
        with transaction.atomic(using=using):
            with rbac_cursor(using) as cursor:
                cursor.execute(
                    """INSERT INTO rol (codigo, abreviatura, denominacion, grupo_id,
                                        cosecha, en_det7, funcion, mfa_requerido,
                                        riesgo_attack, revision_periodica, observaciones)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       RETURNING id""",
                    [
                        datos['codigo'], datos['abreviatura'], datos['denominacion'],
                        datos['grupo_id'], datos['cosecha'], datos['en_det7'],
                        datos['funcion'], datos['mfa_requerido'], datos['riesgo_attack'],
                        datos['revision_periodica'], datos['observaciones'],
                    ],
                )
                rid = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo)
                       SELECT %s, s.id, COALESCE(origen.nivel_codigo, '—')
                       FROM sistema s
                       LEFT JOIN matriz_acceso origen
                              ON origen.sistema_id = s.id AND origen.rol_id = %s""",
                    [rid, clonar_de],
                )
    except IntegrityError:
        raise WriteError('Ya existe un rol con ese código o abreviatura.', status=409)

    origen_txt = (
        f'clonando los accesos de {rol_origen["abreviatura"]}'
        if rol_origen else 'sin accesos'
    )
    _audit(
        'rol', 'ALTA',
        f"Rol {datos['abreviatura']} ({datos['denominacion']}) creado vía API. "
        f'Matriz inicializada {origen_txt}.',
        responsable,
    )
    return {'id': rid, **datos}


def editar_rol(rid, body, responsable, using='rbac'):
    if not fetchone('SELECT 1 n FROM rol WHERE id=%s', [rid], using=using):
        raise WriteError('Rol no encontrado.', status=404)
    datos, error = validar_datos_rol(body, using=using)
    if error:
        raise WriteError(error)
    try:
        with rbac_cursor(using) as cursor:
            cursor.execute(
                """UPDATE rol SET codigo=%s, abreviatura=%s, denominacion=%s,
                                  grupo_id=%s, cosecha=%s, en_det7=%s, funcion=%s,
                                  mfa_requerido=%s, riesgo_attack=%s,
                                  revision_periodica=%s, observaciones=%s
                   WHERE id=%s""",
                [
                    datos['codigo'], datos['abreviatura'], datos['denominacion'],
                    datos['grupo_id'], datos['cosecha'], datos['en_det7'],
                    datos['funcion'], datos['mfa_requerido'], datos['riesgo_attack'],
                    datos['revision_periodica'], datos['observaciones'], rid,
                ],
            )
    except IntegrityError:
        raise WriteError('Ya existe otro rol con ese código o abreviatura.', status=409)
    _audit('rol', 'MODIFICACION', f"Rol {datos['abreviatura']} (id {rid}) actualizado vía API.", responsable)
    return {'id': rid, **datos}


def toggle_activo_rol(rid, responsable, using='rbac'):
    r = fetchone('SELECT abreviatura, activo FROM rol WHERE id=%s', [rid], using=using)
    if not r:
        raise WriteError('Rol no encontrado.', status=404)
    nuevo = not bool(r['activo'])
    if not nuevo:
        n = scalar(
            "SELECT COUNT(*) n FROM usuario WHERE rol_id=%s "
            "AND estado IN ('Activo','Temporal')",
            [rid], using=using,
        )
        if n:
            raise WriteError(
                f"No se puede desactivar {r['abreviatura']}: tiene {n} "
                'usuario(s) activo(s). Reasigne o revoque primero.',
                status=409,
            )
    with rbac_cursor(using) as cursor:
        cursor.execute('UPDATE rol SET activo=%s WHERE id=%s', [nuevo, rid])
    _audit(
        'rol', 'MODIFICACION',
        f"Rol {r['abreviatura']} marcado como {'activo' if nuevo else 'inactivo'} vía API.",
        responsable,
    )
    return {'id': rid, 'activo': nuevo}


def certificar_rol(rid, nota, responsable, using='rbac'):
    r = fetchone(
        'SELECT abreviatura, denominacion, revision_periodica FROM rol WHERE id=%s',
        [rid], using=using,
    )
    if not r:
        raise WriteError('Rol no encontrado.', status=404)
    hoy = timezone.localtime().strftime('%Y-%m-%d')
    with rbac_cursor(using) as cursor:
        cursor.execute('UPDATE rol SET ultima_revision=%s WHERE id=%s', [hoy, rid])
    detalle = (
        f"Rol {r['abreviatura']} ({r['denominacion']}) revisado conforme a su "
        f"periodicidad ({r['revision_periodica']}, POL-SI-002) vía API."
    )
    if nota:
        detalle += f' Nota: {nota}'
    _audit('rol', 'REVISION', detalle, responsable)
    return {'id': rid, 'certificado': True}


def eliminar_rol(rid, responsable, using='rbac'):
    r = fetchone(
        'SELECT abreviatura, denominacion FROM rol WHERE id=%s', [rid], using=using,
    )
    if not r:
        raise WriteError('Rol no encontrado.', status=404)
    n = scalar('SELECT COUNT(*) n FROM usuario WHERE rol_id=%s', [rid], using=using)
    if n:
        raise WriteError(
            f"No se puede eliminar {r['abreviatura']}: {n} usuario(s) lo referencian "
            '(incluidos revocados). Eliminar el rol destruiría su trazabilidad — '
            'use Desactivar, o elimine antes esos usuarios.',
            status=409,
        )
    with rbac_cursor(using) as cursor:
        cursor.execute('DELETE FROM rol WHERE id=%s', [rid])
    _audit(
        'rol', 'ELIMINACION',
        f"Rol {r['abreviatura']} ({r['denominacion']}) eliminado definitivamente "
        'vía API, junto con su fila de la matriz.',
        responsable,
    )


def crear_sistema(body, esp, responsable, using='rbac'):
    datos, error = validar_datos_sistema(body, using=using, crear_categoria=True)
    if error:
        raise WriteError(error)
    try:
        with transaction.atomic(using=using):
            with rbac_cursor(using) as cursor:
                cursor.execute(
                    """INSERT INTO sistema (nombre, categoria_id, clasificacion,
                                            tecnicas_attack, espacio_codigo)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                    [
                        datos['nombre'], datos['categoria_id'], datos['clasificacion'],
                        datos['tecnicas_attack'], esp,
                    ],
                )
                sid = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo) "
                    "SELECT id, %s, '—' FROM rol",
                    [sid],
                )
    except IntegrityError:
        raise WriteError('Ya existe un sistema con ese nombre.', status=409)
    _audit(
        'sistema', 'ALTA',
        f"Sistema «{datos['nombre']}» creado vía API ({datos['clasificacion']}). "
        'Matriz inicializada sin accesos.',
        responsable,
    )
    return {'id': sid, **datos}


def editar_sistema(sid, esp, body, responsable, using='rbac'):
    if not fetchone(
        'SELECT 1 n FROM sistema WHERE id=%s AND espacio_codigo=%s', [sid, esp], using=using,
    ):
        raise WriteError('Sistema no encontrado.', status=404)
    datos, error = validar_datos_sistema(body, using=using, crear_categoria=False)
    if error:
        raise WriteError(error)
    try:
        with rbac_cursor(using) as cursor:
            cursor.execute(
                """UPDATE sistema SET nombre=%s, categoria_id=%s, clasificacion=%s,
                                      tecnicas_attack=%s WHERE id=%s""",
                [
                    datos['nombre'], datos['categoria_id'], datos['clasificacion'],
                    datos['tecnicas_attack'], sid,
                ],
            )
    except IntegrityError:
        raise WriteError('Ya existe otro sistema con ese nombre.', status=409)
    _audit('sistema', 'MODIFICACION', f"Sistema «{datos['nombre']}» (id {sid}) actualizado vía API.", responsable)
    return {'id': sid, **datos}


def toggle_activo_sistema(sid, esp, responsable, using='rbac'):
    s = fetchone(
        'SELECT nombre, activo FROM sistema WHERE id=%s AND espacio_codigo=%s',
        [sid, esp], using=using,
    )
    if not s:
        raise WriteError('Sistema no encontrado.', status=404)
    nuevo = not bool(s['activo'])
    with rbac_cursor(using) as cursor:
        cursor.execute('UPDATE sistema SET activo=%s WHERE id=%s', [nuevo, sid])
    _audit(
        'sistema', 'MODIFICACION' if nuevo else 'REVOCACION',
        f"Sistema «{s['nombre']}» "
        + ('reactivado vía API.' if nuevo else
           'desactivado vía API. Se conserva su historial y su columna en la matriz.'),
        responsable,
    )
    return {'id': sid, 'activo': nuevo}


def eliminar_sistema(sid, esp, responsable, using='rbac'):
    s = fetchone(
        'SELECT nombre FROM sistema WHERE id=%s AND espacio_codigo=%s', [sid, esp], using=using,
    )
    if not s:
        raise WriteError('Sistema no encontrado.', status=404)
    n = scalar(
        'SELECT COUNT(*) n FROM acceso_excepcion WHERE sistema_id=%s', [sid], using=using,
    )
    if n:
        raise WriteError(
            f"No se puede eliminar «{s['nombre']}»: tiene {n} excepción(es) "
            'de acceso documentada(s) (control 5.18). Use Desactivar, o retire '
            'antes esas excepciones.',
            status=409,
        )
    with rbac_cursor(using) as cursor:
        cursor.execute('DELETE FROM sistema WHERE id=%s', [sid])
    _audit(
        'sistema', 'ELIMINACION',
        f"Sistema «{s['nombre']}» eliminado definitivamente vía API junto con su "
        'columna de la matriz.',
        responsable,
    )
    return {'id': sid, 'eliminado': True}


def crear_usuario(body, esp, responsable, using='rbac'):
    datos, error = validar_datos_usuario(body, using=using)
    if error:
        raise WriteError(error)
    rol = fetchone(
        'SELECT abreviatura, denominacion, mfa_requerido FROM rol WHERE id=%s',
        [datos['rol_id']], using=using,
    )
    with transaction.atomic(using=using):
        usuario = Usuario.objects.using(using).create(
            nombre=datos['nombre'],
            rol_id=datos['rol_id'],
            mfa_activo=datos['mfa_activo'],
            nda=datos['nda'],
            estado=datos['estado'],
            fecha_inicio=datos['fecha_inicio'],
            fecha_fin=datos['fecha_fin'],
            notas=datos['notas'],
            espacio_codigo=esp,
        )
        uid = usuario.pk
    _audit(
        'usuario', 'ALTA',
        f"{datos['nombre']} asignado al rol {rol['abreviatura']} "
        f"({rol['denominacion']}) vía API.",
        responsable,
    )
    return {
        'id': uid, **datos,
        'aviso_mfa': _mfa_aviso(rol, datos['mfa_activo']),
    }


def editar_usuario(uid, esp, body, responsable, using='rbac'):
    if not fetchone(
        'SELECT 1 n FROM usuario WHERE id=%s AND espacio_codigo=%s', [uid, esp], using=using,
    ):
        raise WriteError('Usuario no encontrado.', status=404)
    datos, error = validar_datos_usuario(body, using=using, uid_actual=uid)
    if error:
        raise WriteError(error)
    rol = fetchone(
        'SELECT abreviatura, mfa_requerido FROM rol WHERE id=%s',
        [datos['rol_id']], using=using,
    )
    with rbac_cursor(using) as cursor:
        cursor.execute(
            """UPDATE usuario SET nombre=%s, rol_id=%s, mfa_activo=%s, nda=%s,
                                  estado=%s, fecha_inicio=%s, fecha_fin=%s, notas=%s
               WHERE id=%s""",
            [
                datos['nombre'], datos['rol_id'], datos['mfa_activo'], datos['nda'],
                datos['estado'], datos['fecha_inicio'], datos['fecha_fin'],
                datos['notas'], uid,
            ],
        )
    _audit(
        'usuario', 'MODIFICACION',
        f"{datos['nombre']} actualizado vía API; rol {rol['abreviatura']}.",
        responsable,
    )
    return {
        'id': uid, **datos,
        'aviso_mfa': _mfa_aviso(rol, datos['mfa_activo']),
    }


def cambiar_estado_usuario(uid, esp, estado, motivo, responsable, using='rbac'):
    if estado not in ESTADOS_USUARIO:
        raise WriteError('Estado no reconocido.')
    u = fetchone(
        """SELECT u.nombre, r.abreviatura rol FROM usuario u
           JOIN rol r ON r.id=u.rol_id
           WHERE u.id=%s AND u.espacio_codigo=%s""",
        [uid, esp], using=using,
    )
    if not u:
        raise WriteError('Usuario no encontrado.', status=404)
    with rbac_cursor(using) as cursor:
        if motivo:
            cursor.execute(
                'UPDATE usuario SET estado=%s, notas=%s WHERE id=%s',
                [estado, motivo, uid],
            )
        else:
            cursor.execute('UPDATE usuario SET estado=%s WHERE id=%s', [estado, uid])
    accion = 'REVOCACION' if estado == 'Revocado' else 'MODIFICACION'
    detalle = f"{u['nombre']} ({u['rol']}) → estado {estado} vía API."
    if motivo:
        detalle += f' Motivo: {motivo}'
    _audit('usuario', accion, detalle, responsable)
    return {'id': uid, 'estado': estado}


def eliminar_usuario(uid, esp, responsable, using='rbac'):
    u = fetchone(
        """SELECT u.nombre, r.abreviatura rol FROM usuario u
           JOIN rol r ON r.id=u.rol_id
           WHERE u.id=%s AND u.espacio_codigo=%s""",
        [uid, esp], using=using,
    )
    if not u:
        raise WriteError('Usuario no encontrado.', status=404)
    with rbac_cursor(using) as cursor:
        cursor.execute('DELETE FROM usuario WHERE id=%s', [uid])
    _audit(
        'usuario', 'ELIMINACION',
        f"Usuario {u['nombre']} ({u['rol']}) eliminado del registro vía API. "
        'La bitácora conserva sus movimientos previos.',
        responsable,
    )
    return {'id': uid, 'eliminado': True}


def editar_celda_matriz(body, esp, responsable, using='rbac'):
    try:
        rol_id = int(body.get('rol_id'))
        sistema_id = int(body.get('sistema_id'))
    except (TypeError, ValueError):
        raise WriteError('Rol o sistema inválido.')
    nivel = body.get('nivel', '')
    if not fetchone('SELECT 1 n FROM nivel_acceso WHERE codigo=%s', [nivel], using=using):
        raise WriteError('Nivel de acceso no reconocido.')
    rol = fetchone('SELECT abreviatura FROM rol WHERE id=%s', [rol_id], using=using)
    sis = fetchone(
        'SELECT nombre FROM sistema WHERE id=%s AND espacio_codigo=%s',
        [sistema_id, esp], using=using,
    )
    if not rol or not sis:
        raise WriteError('Rol o sistema no encontrado.', status=404)
    prev = fetchone(
        'SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=%s AND sistema_id=%s',
        [rol_id, sistema_id], using=using,
    )
    anterior = prev['nivel_codigo'] if prev else '—'
    with rbac_cursor(using) as cursor:
        cursor.execute(
            'UPDATE matriz_acceso SET nivel_codigo=%s WHERE rol_id=%s AND sistema_id=%s',
            [nivel, rol_id, sistema_id],
        )
    _audit(
        'matriz_acceso', 'MODIFICACION',
        f"{rol['abreviatura']} × {sis['nombre']}: {anterior} → {nivel} vía API",
        responsable,
    )
    return {
        'rol_id': rol_id,
        'sistema_id': sistema_id,
        'anterior': anterior,
        'nuevo': nivel,
    }


def importar_matriz_analizar(archivo_bytes, using='rbac'):
    if not archivo_bytes:
        raise WriteError('Seleccione un archivo CSV para importar.')
    try:
        texto = archivo_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise WriteError(
            'No se pudo leer el archivo: use codificación UTF-8 '
            '(el mismo formato que genera «Exportar matriz»).'
        )
    resultado, error = analizar_importacion_matriz(texto, using=using)
    if error:
        raise WriteError(error)
    cambios, errores = resultado
    return {'cambios': cambios, 'errores': errores, 'total_cambios': len(cambios)}


def importar_matriz_confirmar(cambios, responsable, using='rbac'):
    if not isinstance(cambios, list) or not cambios:
        raise WriteError('No hay cambios para aplicar.')
    aplicados = aplicar_importacion_matriz(
        cambios,
        lambda ent, acc, det: _audit(ent, acc, det, responsable),
        using=using,
    )
    if not aplicados:
        raise WriteError('No se aplicó ningún cambio.')
    return {'aplicados': aplicados}


def excepcion_masiva(body, esp, responsable, using='rbac'):
    motivo = (body.get('motivo') or '').strip()
    if not motivo:
        raise WriteError('Toda excepción debe registrar un motivo (control 5.18).')
    try:
        sistema_id = int(body.get('sistema_id'))
    except (TypeError, ValueError):
        raise WriteError('Sistema inválido.')
    nivel = body.get('nivel', '')
    fecha_fin = body.get('fecha_fin') or None
    from rbac.negocio_validacion import fecha_valida
    if not fecha_valida(fecha_fin):
        raise WriteError('La fecha debe tener el formato AAAA-MM-DD.')
    s = fetchone(
        'SELECT nombre FROM sistema WHERE id=%s AND espacio_codigo=%s',
        [sistema_id, esp], using=using,
    )
    if not s or not fetchone('SELECT 1 n FROM nivel_acceso WHERE codigo=%s', [nivel], using=using):
        raise WriteError('Sistema o nivel no válido.', status=404)
    ids = [i for i in (body.get('usuario_ids') or []) if isinstance(i, int)]
    if not ids:
        raise WriteError('Seleccione al menos un usuario.')

    aplicados = 0
    for uid in ids:
        u = fetchone(
            """SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u
               JOIN rol r ON r.id=u.rol_id
               WHERE u.id=%s AND u.espacio_codigo=%s""",
            [uid, esp], using=using,
        )
        if not u:
            continue
        fila_rol = fetchone(
            'SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=%s AND sistema_id=%s',
            [u['rol_id'], sistema_id], using=using,
        )
        nivel_rol = fila_rol['nivel_codigo'] if fila_rol else '—'
        AccesoExcepcion.objects.using(using).update_or_create(
            usuario_id=uid,
            sistema_id=sistema_id,
            defaults={
                'nivel_id': nivel,
                'motivo': motivo,
                'fecha_fin': fecha_fin,
                'espacio_codigo': esp,
            },
        )
        _audit(
            'usuario', 'MODIFICACION',
            f'Excepción de acceso (asignación masiva vía API): {u["nombre"]} sobre '
            f'«{s["nombre"]}» → {nivel} (el rol {u["rol"]} otorga {nivel_rol}). '
            f'Motivo: {motivo}',
            responsable,
        )
        aplicados += 1
    return {'aplicados': aplicados, 'sistema': s['nombre']}


def crear_excepcion(uid, esp, body, responsable, using='rbac'):
    motivo = (body.get('motivo') or '').strip()
    if not motivo:
        raise WriteError('Toda excepción debe registrar un motivo (control 5.18).')
    try:
        sistema_id = int(body.get('sistema_id'))
    except (TypeError, ValueError):
        raise WriteError('Sistema inválido.')
    nivel = body.get('nivel', '')
    fecha_fin = body.get('fecha_fin') or None
    from rbac.negocio_validacion import fecha_valida
    if not fecha_valida(fecha_fin):
        raise WriteError('La fecha debe tener el formato AAAA-MM-DD.')

    u = fetchone(
        """SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u
           JOIN rol r ON r.id=u.rol_id
           WHERE u.id=%s AND u.espacio_codigo=%s""",
        [uid, esp], using=using,
    )
    s = fetchone(
        'SELECT nombre FROM sistema WHERE id=%s AND espacio_codigo=%s',
        [sistema_id, esp], using=using,
    )
    if not u or not s or not fetchone('SELECT 1 n FROM nivel_acceso WHERE codigo=%s', [nivel], using=using):
        raise WriteError('Usuario, sistema o nivel no válido.', status=404)
    fila_rol = fetchone(
        'SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=%s AND sistema_id=%s',
        [u['rol_id'], sistema_id], using=using,
    )
    nivel_rol = fila_rol['nivel_codigo'] if fila_rol else '—'
    AccesoExcepcion.objects.using(using).update_or_create(
        usuario_id=uid,
        sistema_id=sistema_id,
        defaults={
            'nivel_id': nivel,
            'motivo': motivo,
            'fecha_fin': fecha_fin,
            'espacio_codigo': esp,
        },
    )
    _audit(
        'usuario', 'MODIFICACION',
        f'Excepción de acceso vía API: {u["nombre"]} sobre «{s["nombre"]}» → '
        f'{nivel} (el rol {u["rol"]} otorga {nivel_rol}). Motivo: {motivo}',
        responsable,
    )
    return {'usuario_id': uid, 'sistema_id': sistema_id, 'nivel': nivel}


def eliminar_excepcion(uid, sid, esp, responsable, using='rbac'):
    u = fetchone(
        'SELECT nombre FROM usuario WHERE id=%s AND espacio_codigo=%s', [uid, esp], using=using,
    )
    s = fetchone(
        'SELECT nombre FROM sistema WHERE id=%s AND espacio_codigo=%s', [sid, esp], using=using,
    )
    if not u or not s:
        raise WriteError('Usuario o sistema no encontrado.', status=404)
    AccesoExcepcion.objects.using(using).filter(
        usuario_id=uid, sistema_id=sid, espacio_codigo=esp,
    ).delete()
    _audit(
        'usuario', 'MODIFICACION',
        f'Excepción retirada vía API: {u["nombre"]} sobre «{s["nombre"]}» '
        'vuelve al nivel de su rol.',
        responsable,
    )
    return {'eliminado': True}

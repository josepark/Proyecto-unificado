"""Vistas DRF — contrato /rbac/api/ (Fase 1.2 lectura, 1.3 escritura)."""
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rbac.csrf_util import token_actual, validar_csrf
from rbac.espacio import espacio_codigo_actual
from rbac.services import read_api, write_api


def _responsable(request):
    return request.headers.get('X-Usuario-SGSI') or 'operador local'


class RbacApiBase(APIView):
    """La autorización la hace nginx (auth_request); Flask confía en los headers."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def dispatch(self, request, *args, **kwargs):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not validar_csrf(request):
            return JsonResponse({'detail': 'CSRF token missing or incorrect.'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def _write(self, fn, *args, status_ok=200, empty=False, audit=True, **kwargs):
        try:
            if audit:
                result = fn(*args, responsable=_responsable(self.request), **kwargs)
            else:
                result = fn(*args, **kwargs)
        except write_api.WriteError as exc:
            return Response({'detail': exc.detail}, status=exc.status)
        if empty:
            return Response(status=204)
        return Response(result, status=status_ok)


@method_decorator(csrf_exempt, name='dispatch')
class CsrfView(RbacApiBase):
    def get(self, request):
        return Response({'csrf_token': token_actual(request)})


class CatalogosView(RbacApiBase):
    def get(self, request):
        return Response(read_api.catalogos())


class ResumenView(RbacApiBase):
    def get(self, request):
        return Response(read_api.resumen(espacio_codigo_actual(request)))


class InicioView(RbacApiBase):
    def get(self, request):
        return Response(read_api.inicio(espacio_codigo_actual(request)))


class RolesListView(RbacApiBase):
    def get(self, request):
        return Response(read_api.listar_roles(
            q=request.query_params.get('q', '').strip(),
            incluir_inactivos=request.query_params.get('incluir_inactivos') == '1',
        ))

    def post(self, request):
        return self._write(write_api.crear_rol, request.data, status_ok=201)


class RolDetailView(RbacApiBase):
    def get(self, request, rid):
        rol = read_api.obtener_rol(rid, espacio_codigo_actual(request))
        if not rol:
            return Response({'detail': 'Rol no encontrado.'}, status=404)
        return Response(rol)

    def put(self, request, rid):
        return self._write(write_api.editar_rol, rid, request.data)

    def delete(self, request, rid):
        return self._write(write_api.eliminar_rol, rid, empty=True)


class RolActivoView(RbacApiBase):
    def delete(self, request, rid):
        return self._write(write_api.toggle_activo_rol, rid)

    def post(self, request, rid):
        return self._write(write_api.toggle_activo_rol, rid)


class RolCertificarView(RbacApiBase):
    def post(self, request, rid):
        nota = (request.data or {}).get('nota', '').strip()
        return self._write(write_api.certificar_rol, rid, nota)


class SistemasListView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.listar_sistemas(
            esp,
            q=request.query_params.get('q', '').strip(),
            categoria=request.query_params.get('categoria', ''),
            clasificacion=request.query_params.get('clasificacion', ''),
            incluir_inactivos=request.query_params.get('incluir_inactivos') == '1',
        ))

    def post(self, request):
        return self._write(
            write_api.crear_sistema, request.data, espacio_codigo_actual(request),
            status_ok=201,
        )


class SistemaDetailView(RbacApiBase):
    def get(self, request, sid):
        sistema = read_api.obtener_sistema(sid, espacio_codigo_actual(request))
        if not sistema:
            return Response({'detail': 'Sistema no encontrado.'}, status=404)
        return Response(sistema)

    def put(self, request, sid):
        return self._write(
            write_api.editar_sistema, sid, espacio_codigo_actual(request), request.data,
        )

    def delete(self, request, sid):
        return self._write(
            write_api.eliminar_sistema, sid, espacio_codigo_actual(request),
        )


class SistemaActivoView(RbacApiBase):
    def delete(self, request, sid):
        return self._write(write_api.toggle_activo_sistema, sid, espacio_codigo_actual(request))

    def post(self, request, sid):
        return self._write(write_api.toggle_activo_sistema, sid, espacio_codigo_actual(request))


class UsuariosListView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.listar_usuarios(
            esp,
            q=request.query_params.get('q', '').strip(),
            estado=request.query_params.get('estado', ''),
            rol=request.query_params.get('rol', ''),
        ))

    def post(self, request):
        return self._write(
            write_api.crear_usuario, request.data, espacio_codigo_actual(request),
            status_ok=201,
        )


class UsuarioDetailView(RbacApiBase):
    def get(self, request, uid):
        usuario = read_api.obtener_usuario(uid, espacio_codigo_actual(request))
        if not usuario:
            return Response({'detail': 'Usuario no encontrado.'}, status=404)
        return Response(usuario)

    def put(self, request, uid):
        return self._write(
            write_api.editar_usuario, uid, espacio_codigo_actual(request), request.data,
        )

    def delete(self, request, uid):
        return self._write(write_api.eliminar_usuario, uid, espacio_codigo_actual(request))


class UsuarioEstadoView(RbacApiBase):
    def put(self, request, uid):
        body = request.data or {}
        return self._write(
            write_api.cambiar_estado_usuario,
            uid,
            espacio_codigo_actual(request),
            body.get('estado', ''),
            (body.get('motivo') or '').strip(),
        )


class MatrizView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.matriz(
            esp,
            grupo=request.query_params.get('grupo', ''),
            categoria=request.query_params.get('categoria', ''),
        ))

    def put(self, request):
        return self._write(
            write_api.editar_celda_matriz, request.data, espacio_codigo_actual(request),
        )


class MatrizHeatmapView(RbacApiBase):
    def get(self, request):
        return Response(read_api.matriz_heatmap(espacio_codigo_actual(request)))


class MatrizCompararView(RbacApiBase):
    def get(self, request):
        try:
            rol_a = int(request.query_params['rol_a'])
            rol_b = int(request.query_params['rol_b'])
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'Indique rol_a y rol_b (ids numéricos).'}, status=400)
        resultado = read_api.matriz_comparar(espacio_codigo_actual(request), rol_a, rol_b)
        if resultado is None:
            return Response({'detail': 'Uno de los roles seleccionados ya no existe.'}, status=404)
        return Response(resultado)


class MatrizImportarAnalizarView(RbacApiBase):
    def post(self, request):
        archivo = request.FILES.get('archivo')
        contenido = archivo.read() if archivo else b''
        return self._write(write_api.importar_matriz_analizar, contenido, audit=False)


class MatrizImportarConfirmarView(RbacApiBase):
    def post(self, request):
        cambios = (request.data or {}).get('cambios')
        return self._write(write_api.importar_matriz_confirmar, cambios)


class ExcepcionesListView(RbacApiBase):
    def get(self, request):
        return Response(read_api.listar_excepciones(
            espacio_codigo_actual(request),
            incluir_vencidas=request.query_params.get('vencidas') == '1',
        ))


class ExcepcionesMasivaView(RbacApiBase):
    def post(self, request):
        return self._write(
            write_api.excepcion_masiva, request.data, espacio_codigo_actual(request),
            status_ok=201,
        )


class UsuarioExcepcionesView(RbacApiBase):
    def post(self, request, uid):
        return self._write(
            write_api.crear_excepcion, uid, espacio_codigo_actual(request), request.data,
            status_ok=201,
        )


class UsuarioExcepcionDetailView(RbacApiBase):
    def delete(self, request, uid, sid):
        return self._write(
            write_api.eliminar_excepcion, uid, sid, espacio_codigo_actual(request),
        )


class AuditoriaListView(RbacApiBase):
    def get(self, request):
        try:
            pagina = max(1, int(request.query_params.get('pagina', '1')))
        except ValueError:
            pagina = 1
        try:
            limite = int(request.query_params.get('limite', '50'))
        except (TypeError, ValueError):
            limite = 50
        return Response(read_api.auditoria(
            entidad=request.query_params.get('entidad', ''),
            accion=request.query_params.get('accion', ''),
            q=request.query_params.get('q', '').strip(),
            pagina=pagina,
            limite=limite,
        ))


class AuditoriaVerificarView(RbacApiBase):
    def get(self, request):
        return Response(read_api.auditoria_verificar())


class ExportMatrizCsvView(RbacApiBase):
    def get(self, request):
        nombre, contenido = read_api.export_matriz_csv(espacio_codigo_actual(request))
        return HttpResponse(
            contenido,
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nombre}'},
        )


class ExportAccesosCsvView(RbacApiBase):
    def get(self, request):
        nombre, contenido = read_api.export_accesos_csv(espacio_codigo_actual(request))
        return HttpResponse(
            contenido,
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nombre}'},
        )

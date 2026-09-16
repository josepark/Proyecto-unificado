"""Vistas DRF read-only — contrato /rbac/api/ (Fase 1.2)."""
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rbac.espacio import espacio_codigo_actual
from rbac.services import read_api


class RbacApiBase(APIView):
    """La autorización la hace nginx (auth_request); Flask confía en los headers."""
    permission_classes = [AllowAny]
    authentication_classes = []


class CsrfView(RbacApiBase):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({'csrf_token': get_token(request)})


class CatalogosView(RbacApiBase):
    def get(self, request):
        return Response(read_api.catalogos())


class ResumenView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.resumen(esp))


class InicioView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.inicio(esp))


class RolesListView(RbacApiBase):
    def get(self, request):
        return Response(read_api.listar_roles(
            q=request.query_params.get('q', '').strip(),
            incluir_inactivos=request.query_params.get('incluir_inactivos') == '1',
        ))


class RolDetailView(RbacApiBase):
    def get(self, request, rid):
        esp = espacio_codigo_actual(request)
        rol = read_api.obtener_rol(rid, esp)
        if not rol:
            return Response({'detail': 'Rol no encontrado.'}, status=404)
        return Response(rol)


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


class SistemaDetailView(RbacApiBase):
    def get(self, request, sid):
        esp = espacio_codigo_actual(request)
        sistema = read_api.obtener_sistema(sid, esp)
        if not sistema:
            return Response({'detail': 'Sistema no encontrado.'}, status=404)
        return Response(sistema)


class UsuariosListView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.listar_usuarios(
            esp,
            q=request.query_params.get('q', '').strip(),
            estado=request.query_params.get('estado', ''),
            rol=request.query_params.get('rol', ''),
        ))


class UsuarioDetailView(RbacApiBase):
    def get(self, request, uid):
        esp = espacio_codigo_actual(request)
        usuario = read_api.obtener_usuario(uid, esp)
        if not usuario:
            return Response({'detail': 'Usuario no encontrado.'}, status=404)
        return Response(usuario)


class MatrizView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.matriz(
            esp,
            grupo=request.query_params.get('grupo', ''),
            categoria=request.query_params.get('categoria', ''),
        ))


class MatrizHeatmapView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.matriz_heatmap(esp))


class MatrizCompararView(RbacApiBase):
    def get(self, request):
        try:
            rol_a = int(request.query_params['rol_a'])
            rol_b = int(request.query_params['rol_b'])
        except (KeyError, TypeError, ValueError):
            return Response(
                {'detail': 'Indique rol_a y rol_b (ids numéricos).'},
                status=400,
            )
        esp = espacio_codigo_actual(request)
        resultado = read_api.matriz_comparar(esp, rol_a, rol_b)
        if resultado is None:
            return Response(
                {'detail': 'Uno de los roles seleccionados ya no existe.'},
                status=404,
            )
        return Response(resultado)


class ExcepcionesListView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        return Response(read_api.listar_excepciones(
            esp,
            incluir_vencidas=request.query_params.get('vencidas') == '1',
        ))


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
        esp = espacio_codigo_actual(request)
        nombre, contenido = read_api.export_matriz_csv(esp)
        return HttpResponse(
            contenido,
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nombre}'},
        )


class ExportAccesosCsvView(RbacApiBase):
    def get(self, request):
        esp = espacio_codigo_actual(request)
        nombre, contenido = read_api.export_accesos_csv(esp)
        return HttpResponse(
            contenido,
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={nombre}'},
        )

from itertools import chain

from django.db.models import Count, Q
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permisos import RolPermiso, RolPermisoOServicioInterno, SoloAdministrador


class CatalogoPagination(PageNumberPagination):
    """Paginacion amplia para catalogos de referencia (MITRE, controles)."""
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 2000

from .models import (Activo, ActivoInfraestructura, SistemaInformacion,
                     EquipoComputo, ClaseActivo, AmenazaMITRE, ControlISO)
from .serializers import (ActivoListSerializer, ActivoDetailSerializer,
                          ActivoWriteSerializer, ClaseActivoSerializer,
                          AmenazaMITRESerializer, ControlISOSerializer,
                          HistorialSerializer)
from .meta_inventario import meta_inventario, catalogo_clases_activo


class ActivoViewSet(viewsets.ModelViewSet):
    """CRUD completo de activos. Lectura libre; escritura requiere sesion."""
    permission_classes = [RolPermisoOServicioInterno]
    queryset = Activo.objects.all().prefetch_related(
        "amenazas", "controles", "dependencias").select_related(
        "infraestructura", "sistema")
    filterset_fields = ["clase", "clasificacion_si", "nivel_riesgo",
                        "estado", "ciclo_vida", "procesa_datos_personales"]
    search_fields = ["id_activo", "nombre", "descripcion", "notas_seguridad",
                     "propietario", "custodio"]
    ordering_fields = ["id_activo", "valor", "nivel_riesgo"]

    def get_serializer_class(self):
        if self.action == "list":
            return ActivoListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ActivoWriteSerializer
        return ActivoDetailSerializer

    @action(detail=False)
    def estadisticas(self, request):
        qs = Activo.objects.all()
        por_riesgo = dict(qs.values_list("nivel_riesgo").annotate(n=Count("id")))
        por_clase = dict(qs.values_list("clase").annotate(n=Count("id")))
        por_clasif = dict(qs.values_list("clasificacion_si").annotate(n=Count("id")))
        top_amenazas = list(AmenazaMITRE.objects.annotate(
            n=Count("activos")).filter(n__gt=0).order_by("-n")[:10].values(
            "codigo", "descripcion", "n"))
        clases = catalogo_clases_activo()
        return Response({
            "total_activos": qs.count(),
            "datos_personales": qs.filter(procesa_datos_personales=True).count(),
            "por_nivel_riesgo": por_riesgo,
            "por_clase": por_clase,
            "por_clasificacion": por_clasif,
            "top_amenazas": top_amenazas,
            "clases": clases,
        })

    @action(detail=False, methods=["get"])
    def meta(self, request):
        """Metadatos para la SPA: clases configurables, enums y colores."""
        return Response(meta_inventario())

    @action(detail=True)
    def historial(self, request, pk=None):
        """Bitacora de un activo especifico."""
        activo = self.get_object()
        registros = activo.history.all().order_by("-history_date")
        return Response(HistorialSerializer(registros, many=True).data)


class AmenazaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RolPermisoOServicioInterno]
    queryset = AmenazaMITRE.objects.annotate(num_activos=Count("activos"))
    serializer_class = AmenazaMITRESerializer
    filterset_fields = ["tipo"]
    search_fields = ["codigo", "nombre", "descripcion", "tacticas"]
    ordering_fields = ["codigo", "nombre"]
    pagination_class = CatalogoPagination


class ControlViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RolPermisoOServicioInterno]
    queryset = ControlISO.objects.annotate(num_activos=Count("activos"))
    serializer_class = ControlISOSerializer
    search_fields = ["codigo", "descripcion"]


class ClaseActivoViewSet(viewsets.ModelViewSet):
    """Catálogo dinámico de clases de activo — editable por Dinamizador/Admin."""
    queryset = ClaseActivo.objects.all()
    serializer_class = ClaseActivoSerializer
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["orden", "codigo"]

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        n = Activo.objects.filter(clase=obj.codigo).count()
        if n:
            return Response(
                {"detail": f"No se puede eliminar: hay {n} activo(s) con la clase {obj.codigo}."},
                status=409,
            )
        return super().destroy(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([RolPermiso])
def bitacora_global(request):
    """Bitacora consolidada de los ultimos cambios en todo el inventario."""
    limite = int(request.GET.get("limite", 60))
    registros = list(chain(
        Activo.history.all(),
        ActivoInfraestructura.history.all(),
        SistemaInformacion.history.all(),
    ))
    registros.sort(key=lambda r: r.history_date, reverse=True)
    return Response(HistorialSerializer(registros[:limite], many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def sesion_info(request):
    """Indica al tablero si hay un usuario autenticado (para mostrar CRUD)."""
    return Response({
        "autenticado": request.user.is_authenticated,
        "usuario": request.user.get_username() if request.user.is_authenticated else None,
    })


@ensure_csrf_cookie
def dashboard(request):
    """Redirige a la SPA unificada (nginx sirve React en /).

    Se conserva la ruta por compatibilidad con acceso directo a Django
    (p. ej. inventario:8000 en desarrollo) y con tests de cabeceras.
    """
    return redirect("/inventario/dashboard")


# ---------------------------------------------------------------------------
# v3 - Datacenter, Diagrama, Hoja de vida
# ---------------------------------------------------------------------------
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from . import deteccion_diagramas
from .models import Datacenter, Diagrama, EventoHojaVida, Rack
from .serializers import (DatacenterSerializer, DiagramaSerializer,
                          EventoHojaVidaSerializer, RackSerializer)


class DatacenterViewSet(viewsets.ModelViewSet):
    queryset = Datacenter.objects.all()
    serializer_class = DatacenterSerializer
    search_fields = ["codigo", "nombre", "ciudad"]

    def destroy(self, request, *args, **kwargs):
        dc = self.get_object()
        n = dc.activos.count()
        if n and request.query_params.get("confirmar") != "1":
            return Response(
                {"detail": f"El centro {dc.codigo} tiene {n} activo(s) asignado(s). "
                           "Confirme para eliminarlo; los activos quedarán sin sede.",
                 "activos_afectados": n},
                status=409,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True)
    def activos(self, request, pk=None):
        dc = self.get_object()
        data = ActivoListSerializer(dc.activos.all(), many=True).data
        return Response(data)

    @action(detail=True)
    def racks(self, request, pk=None):
        dc = self.get_object()
        qs = dc.racks.all()
        return Response(RackSerializer(qs, many=True).data)


class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.select_related("datacenter").all()
    serializer_class = RackSerializer
    filterset_fields = ["datacenter"]
    search_fields = ["codigo", "ubicacion"]


class DiagramaViewSet(viewsets.ModelViewSet):
    queryset = Diagrama.objects.all().prefetch_related("activos")
    serializer_class = DiagramaSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["tipo", "datacenter"]
    search_fields = ["titulo", "descripcion"]

    def get_queryset(self):
        qs = super().get_queryset()
        activo = self.request.query_params.get("activo")
        if activo:
            qs = qs.filter(activos__id=activo)
        return qs

    @action(detail=False, methods=["post"])
    def sugerir_activos(self, request):
        """Analiza (sin guardar nada) el archivo que se está por subir y
        sugiere qué activos del inventario menciona el diagrama, para
        pre-marcarlos en el formulario en vez de obligar a buscarlos uno
        por uno en la lista completa. Solo funciona con SVG — es el único
        formato donde el texto queda accesible sin OCR; para PDF/imagen se
        devuelve una lista vacía y el front explica por qué."""
        archivo = request.FILES.get("archivo")
        if not archivo:
            return Response({"detail": "Debe adjuntar un archivo."}, status=400)

        contenido = archivo.read()
        if not deteccion_diagramas.es_svg(archivo.name, contenido):
            return Response({
                "soportado": False,
                "sugerencias": [],
                "detalle": ("La detección automática solo está disponible "
                           "para archivos SVG (el texto de una imagen o un "
                           "PDF no se puede leer de forma confiable sin "
                           "reconocimiento óptico)."),
            })

        sugerencias = deteccion_diagramas.sugerir_activos(
            contenido, Activo.objects.only("id", "id_activo", "nombre"))
        return Response({"soportado": True, "sugerencias": sugerencias})


class HojaVidaViewSet(viewsets.ModelViewSet):
    queryset = EventoHojaVida.objects.all().select_related("activo")
    serializer_class = EventoHojaVidaSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["activo", "tipo_evento"]
    ordering_fields = ["fecha"]

    def perform_create(self, serializer):
        usuario = (self.request.user.get_username()
                   if self.request.user.is_authenticated else "")
        serializer.save(registrado_por=usuario)


# ---------------------------------------------------------------------------
# v4 - Tablero de alertas: ciclo de vida y completitud del inventario
# ---------------------------------------------------------------------------
from datetime import timedelta
from django.utils import timezone
from django.db.models import Max


def calcular_alertas():
    """
    Calcula alertas operativas del inventario:
      - Ciclo de vida: fin de soporte (EOL) y garantia vencidos o proximos.
      - Mantenimiento preventivo vencido o nunca registrado.
      - Escaneo de vulnerabilidades desactualizado y hallazgos abiertos.
      - Completitud: activos criticos sin propietario, sin valoracion C-I-D,
        o sin centro de datos asignado.
    Cada item incluye severidad: crit | alto | medio | bajo.

    Extraida de la vista alertas() (antes vivia solo ahi) para que el
    comando de notificaciones por correo (management/commands/
    enviar_resumen_alertas.py) pueda reusar exactamente el mismo calculo
    en vez de duplicarlo — una sola definicion de que cuenta como alerta.
    """
    hoy = timezone.now().date()
    prox_eol = hoy + timedelta(days=180)
    prox_gar = hoy + timedelta(days=90)
    limite_mant = hoy - timedelta(days=365)
    limite_scan = hoy - timedelta(days=90)

    def item(a, detalle, sev):
        return {"id": a.id, "id_activo": a.id_activo, "nombre": a.nombre,
                "detalle": detalle, "severidad": sev}

    eol, garantia, mantenimiento, escaneo = [], [], [], []
    hallazgos, sin_propietario, sin_cid, sin_dc, sin_rack = [], [], [], [], []

    infra = ActivoInfraestructura.objects.select_related("activo").all()
    for inf in infra:
        a = inf.activo
        # EOL
        if inf.fin_soporte_eol:
            if inf.fin_soporte_eol < hoy:
                eol.append(item(a, f"Soporte (EOL) vencido el {inf.fin_soporte_eol}", "crit"))
            elif inf.fin_soporte_eol <= prox_eol:
                dias = (inf.fin_soporte_eol - hoy).days
                eol.append(item(a, f"Soporte (EOL) vence en {dias} dias ({inf.fin_soporte_eol})", "alto"))
        # Garantia
        if inf.fin_garantia:
            if inf.fin_garantia < hoy:
                garantia.append(item(a, f"Garantia vencida el {inf.fin_garantia}", "medio"))
            elif inf.fin_garantia <= prox_gar:
                dias = (inf.fin_garantia - hoy).days
                garantia.append(item(a, f"Garantia vence en {dias} dias ({inf.fin_garantia})", "bajo"))
        # Escaneo de vulnerabilidades
        if inf.fecha_ultimo_escaneo is None:
            escaneo.append(item(a, "Sin fecha de ultimo escaneo (OpenVAS)", "medio"))
        elif inf.fecha_ultimo_escaneo < limite_scan:
            escaneo.append(item(a, f"Ultimo escaneo hace mas de 90 dias ({inf.fecha_ultimo_escaneo})", "medio"))
        # Hallazgos abiertos
        if inf.hallazgos_abiertos and inf.hallazgos_abiertos > 0:
            sev = "alto" if inf.hallazgos_abiertos > 5 else "medio"
            hallazgos.append(item(a, f"{inf.hallazgos_abiertos} hallazgo(s) de vulnerabilidad abiertos", sev))

    # Garantia de equipos de computo (mismo criterio que infraestructura)
    for eq in EquipoComputo.objects.select_related("activo").all():
        a = eq.activo
        if eq.fin_garantia:
            if eq.fin_garantia < hoy:
                garantia.append(item(a, f"Garantia vencida el {eq.fin_garantia}", "medio"))
            elif eq.fin_garantia <= prox_gar:
                dias = (eq.fin_garantia - hoy).days
                garantia.append(item(a, f"Garantia vence en {dias} dias ({eq.fin_garantia})", "bajo"))

    # Mantenimiento preventivo (solo infraestructura)
    ultimo_mant = dict(
        EventoHojaVida.objects.filter(tipo_evento="MPRE")
        .values("activo").annotate(u=Max("fecha")).values_list("activo", "u"))
    for inf in infra:
        a = inf.activo
        if a.estado in ("RET",) or a.ciclo_vida == "RETI":
            continue
        u = ultimo_mant.get(a.id)
        if u is None:
            mantenimiento.append(item(a, "Sin mantenimiento preventivo registrado", "medio"))
        elif u < limite_mant:
            mantenimiento.append(item(a, f"Ultimo mantenimiento hace mas de 12 meses ({u})", "alto"))

    # Completitud
    for a in Activo.objects.all():
        if a.nivel_riesgo in ("CRIT", "ALTO") and not a.propietario.strip():
            sin_propietario.append(item(a, f"Activo {a.get_nivel_riesgo_display()} sin propietario asignado (ISO 5.9)", "alto"))
        if a.confidencialidad is None or a.integridad is None or a.disponibilidad is None:
            sin_cid.append(item(a, "Sin valoracion C-I-D completa", "medio"))
        if a.datacenter_id is None:
            sin_dc.append(item(a, "Sin centro de datos asignado", "bajo"))
        if a.clase == "INFRA" and a.datacenter_id:
            inf = getattr(a, "infraestructura", None)
            if inf and not inf.rack_fk_id and not (inf.rack or "").strip():
                sin_rack.append(item(
                    a, f"Infraestructura en {a.datacenter.codigo} sin rack/U asignados",
                    "medio"))

    # Correlacion de riesgo cruzado
    # riesgoso por si solo, que ademas tiene excepciones de acceso vigentes
    # en RBAC, es una senal compuesta que ninguna de las dos apps ve por
    # separado. Se cruza por sistema_mca_equivalente contra el catalogo
    # canonico de RBAC (servidor-a-servidor, ver integracion_rbac.py); si
    # RBAC no responde, este grupo simplemente queda vacio (no rompe el
    # resto de las alertas, que son propias del Inventario).
    riesgo_cruzado = []
    catalogo_rbac = catalogo_sistemas_rbac()
    if catalogo_rbac:
        mapa_rbac = {s["nombre"].strip().lower(): s for s in catalogo_rbac}
        activos_riesgo = (Activo.objects.filter(nivel_riesgo__in=("CRIT", "ALTO"))
                          .select_related("sistema"))
        for a in activos_riesgo:
            if not hasattr(a, "sistema"):
                continue
            sis = a.sistema
            coincidencia = None
            if sis.sistema_rbac_id:
                coincidencia = next(
                    (s for s in catalogo_rbac if s.get("id") == sis.sistema_rbac_id), None)
            if not coincidencia:
                nombre_mca = (sis.sistema_mca_equivalente or "").strip()
                if nombre_mca:
                    coincidencia = mapa_rbac.get(nombre_mca.lower())
            if coincidencia and coincidencia.get("excepciones_vigentes", 0) > 0:
                n = coincidencia["excepciones_vigentes"]
                sev = "crit" if a.nivel_riesgo == "CRIT" else "alto"
                riesgo_cruzado.append(item(
                    a, f"Riesgo {a.get_nivel_riesgo_display()} con {n} "
                       f"excepcion(es) de acceso vigentes en RBAC "
                       f"({coincidencia['nombre']})", sev))

    grupos = [
        {"clave": "eol", "titulo": "Fin de soporte (EOL)", "items": eol},
        {"clave": "garantia", "titulo": "Garantia", "items": garantia},
        {"clave": "mantenimiento", "titulo": "Mantenimiento preventivo", "items": mantenimiento},
        {"clave": "escaneo", "titulo": "Escaneo de vulnerabilidades", "items": escaneo},
        {"clave": "hallazgos", "titulo": "Hallazgos abiertos", "items": hallazgos},
        {"clave": "sin_propietario", "titulo": "Activos criticos sin propietario", "items": sin_propietario},
        {"clave": "sin_cid", "titulo": "Sin valoracion C-I-D", "items": sin_cid},
        {"clave": "sin_dc", "titulo": "Sin centro de datos", "items": sin_dc},
        {"clave": "sin_rack", "titulo": "Infra en DC sin rack/U", "items": sin_rack},
        {"clave": "riesgo_cruzado", "titulo": "Riesgo cruzado (activo riesgoso + excepciones RBAC vigentes)", "items": riesgo_cruzado},
    ]
    total = sum(len(g["items"]) for g in grupos)
    criticas = sum(1 for g in grupos for i in g["items"] if i["severidad"] in ("crit", "alto"))
    return {
        "fecha": hoy, "total_alertas": total, "alertas_criticas": criticas,
        "grupos": [g for g in grupos if g["items"]],
    }


@api_view(["GET"])
@permission_classes([RolPermiso])
def alertas(request):
    return Response(calcular_alertas())


# ---------------------------------------------------------------------------
# v8 - Motor de riesgos, cobertura de controles (SoA), dashboard ejecutivo,
#      exportaciones (Excel/PDF), codigos QR, auditoria de accesos.
# ---------------------------------------------------------------------------
import io
from collections import Counter, defaultdict
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta

from . import riesgo as motor_riesgo
from .models import ControlISO, RegistroAcceso, RegistroIntegridad
from .integridad import verificar_cadena
from .permisos import roles_de, ROL_DINAMIZADOR, ROL_ADMIN


def _activos_full():
    return Activo.objects.all().prefetch_related(
        "amenazas", "controles").select_related("infraestructura")


def calcular_riesgos():
    """Calcula el riesgo (probabilidad x impacto) de cada activo y la
    matriz. Extraída de la vista riesgos() para que el reporte consolidado
    (reporte_consolidado.py) pueda reusar el mismo cálculo."""
    filas = []
    matriz = defaultdict(int)          # (prob, impacto) -> conteo
    conteo_nivel = Counter()
    for a in _activos_full():
        r = motor_riesgo.calcular_activo(a)
        conteo_nivel[r["nivel"]] += 1
        if r["impacto"] is not None:
            matriz[f"{r['probabilidad']},{r['impacto']}"] += 1
        filas.append({
            "id": a.id, "id_activo": a.id_activo, "nombre": a.nombre,
            "clase": a.clase, "nivel_registrado": a.nivel_riesgo, **r})
    filas.sort(key=lambda x: (x["score"] or -1), reverse=True)
    return {
        "activos": filas, "matriz": dict(matriz), "por_nivel": dict(conteo_nivel),
        "sin_valorar": conteo_nivel.get("SIN", 0)}


@api_view(["GET"])
@permission_classes([RolPermiso])
def riesgos(request):
    return Response(calcular_riesgos())


@api_view(["POST"])
@permission_classes([RolPermiso])
def recalcular_riesgos(request):
    """Aplica el riesgo calculado al campo nivel_riesgo de cada activo con C-I-D."""
    n = 0
    for a in _activos_full():
        r = motor_riesgo.calcular_activo(a)
        if r["nivel"] != "SIN" and a.nivel_riesgo != r["nivel"]:
            a.nivel_riesgo = r["nivel"]
            a.save()
            n += 1
    return Response({"actualizados": n})


def calcular_cobertura():
    """Declaracion de Aplicabilidad dinamica: cobertura de controles.
    Extraída de la vista para que el reporte consolidado la reuse."""
    controles = ControlISO.objects.annotate(n=Count("activos")).order_by("-n", "codigo")
    total_ctrl = controles.count()
    usados = sum(1 for c in controles if c.n > 0)
    total_activos = Activo.objects.count()
    con_control = Activo.objects.annotate(nc=Count("controles")).filter(nc__gt=0).count()
    detalle = [{"codigo": c.codigo, "descripcion": c.descripcion, "num_activos": c.n}
               for c in controles]
    return {
        "total_controles": total_ctrl, "controles_usados": usados,
        "total_activos": total_activos, "activos_con_control": con_control,
        "cobertura_activos_pct": round(con_control / total_activos * 100, 1) if total_activos else 0,
        "detalle": detalle}


@api_view(["GET"])
@permission_classes([RolPermiso])
def cobertura_controles(request):
    return Response(calcular_cobertura())


# Despliegue integrado: KPIs de RBAC para el Panel ejecutivo consolidado.
# Ver inventario/integracion_rbac.py.
from .integracion_rbac import catalogo_sistemas_rbac
from .integracion_rbac import resumen_rbac as _resumen_rbac


def calcular_panel_ejecutivo():
    """Indicadores gerenciales de madurez del SGSI. Extraída de la vista
    dashboard_ejecutivo() para que el reporte consolidado la reuse."""
    qs = Activo.objects.all()
    total = qs.count() or 1
    con_cid = qs.exclude(confidencialidad=None).exclude(integridad=None).exclude(disponibilidad=None).count()
    con_prop = qs.exclude(propietario="").count()
    con_dc = qs.exclude(datacenter=None).count()
    con_ctrl = qs.annotate(nc=Count("controles")).filter(nc__gt=0).count()
    dp = qs.filter(procesa_datos_personales=True).count()
    por_riesgo = dict(qs.values_list("nivel_riesgo").annotate(n=Count("id")))
    por_ciclo = dict(qs.values_list("ciclo_vida").annotate(n=Count("id")))
    hace30 = timezone.now() - timedelta(days=30)
    cambios30 = Activo.history.filter(history_date__gte=hace30).count()
    total_ctrl = ControlISO.objects.count()
    ctrl_usados = ControlISO.objects.annotate(n=Count("activos")).filter(n__gt=0).count()
    datacenters_resumen = list(
        Datacenter.objects.annotate(
            total_activos=Count("activos"),
            criticos=Count("activos", filter=Q(activos__nivel_riesgo="CRIT")),
            sin_rack=Count("activos", filter=Q(
                activos__clase="INFRA",
                activos__infraestructura__rack_fk__isnull=True,
                activos__infraestructura__rack="",
            )),
        ).order_by("codigo").values(
            "id", "codigo", "nombre", "tipo", "total_activos", "criticos", "sin_rack",
        )
    )
    return {
        "total_activos": qs.count(),
        "completitud": {
            "valoracion_cid": round(con_cid / total * 100),
            "propietario": round(con_prop / total * 100),
            "centro_datos": round(con_dc / total * 100),
            "con_control": round(con_ctrl / total * 100),
        },
        "cobertura_controles": {
            "usados": ctrl_usados, "total": total_ctrl,
            "pct": round(ctrl_usados / total_ctrl * 100) if total_ctrl else 0},
        "datos_personales": dp,
        "por_nivel_riesgo": por_riesgo,
        "por_ciclo_vida": por_ciclo,
        "cambios_30dias": cambios30,
        "datacenters": datacenters_resumen,
        "rbac": _resumen_rbac(),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_ejecutivo(request):
    return Response(calcular_panel_ejecutivo())


@api_view(["GET"])
@permission_classes([RolPermiso])
def reporte_consolidado_pdf(request):
    """PDF único con SoA, riesgos, alertas y cumplimiento RBAC — antes,
    esto significaba combinar a mano varias exportaciones parciales para
    preparar evidencia de auditoría."""
    from .reporte_consolidado import generar_pdf
    contenido = generar_pdf()
    resp = HttpResponse(contenido, content_type="application/pdf")
    fecha = timezone.localtime(timezone.now()).strftime("%Y%m%d")
    resp["Content-Disposition"] = f'inline; filename="reporte_consolidado_suiin_{fecha}.pdf"'
    return resp


# ---------------------- Exportaciones ----------------------
def _xlsx_response(wb, nombre):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return resp


@api_view(["GET"])
@permission_classes([RolPermiso])
def exportar_inventario_xlsx(request):
    from .importar_activos import generar_export_inventario
    return _xlsx_response(generar_export_inventario(), "inventario_suiin.xlsx")


@api_view(["GET"])
@permission_classes([RolPermiso])
def importar_plantilla_xlsx(request):
    """Plantilla descargable para la importación masiva: encabezados,
    una fila de ejemplo y una hoja de referencia con los valores válidos
    de cada campo de opciones."""
    from .importar_activos import generar_plantilla
    return _xlsx_response(generar_plantilla(), "plantilla_importar_activos.xlsx")


@api_view(["POST"])
@permission_classes([RolPermiso])
def importar_activos_analizar(request):
    """Paso 1 de la importación masiva: analiza el archivo subido y
    devuelve, fila por fila, si está lista para crearse o qué error
    tiene — sin guardar nada todavía (mismo patrón de dos pasos que ya
    usaba RBAC para importar la matriz por CSV)."""
    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"detail": "Debe adjuntar un archivo .xlsx."}, status=400)
    from .importar_activos import analizar_archivo
    try:
        filas = analizar_archivo(archivo)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    except Exception:
        return Response({"detail": "No se pudo leer el archivo. ¿Es un .xlsx válido?"}, status=400)
    ok = sum(1 for f in filas if f["estado"] == "ok")
    return Response({"filas": filas, "total": len(filas), "listas": ok,
                     "con_error": len(filas) - ok})


@api_view(["POST"])
@permission_classes([RolPermiso])
def importar_activos_confirmar(request):
    """Paso 2: crea las filas que el usuario confirmó (ya analizadas en
    el paso 1). Cada activo creado pasa por el mismo ActivoWriteSerializer
    del formulario individual, así que la bitácora y la cadena de
    integridad (sección 8.16) se llenan exactamente igual que si se
    hubiera creado a mano, uno por uno."""
    filas = request.data.get("filas", [])
    if not isinstance(filas, list) or not filas:
        return Response({"detail": "No se recibió ninguna fila para crear."}, status=400)
    from .importar_activos import aplicar_filas
    creados, fallidos = aplicar_filas(filas, request.user)
    return Response({"creados": creados, "fallidos": fallidos,
                     "total_creados": len(creados), "total_fallidos": len(fallidos)})


@api_view(["GET"])
@permission_classes([RolPermiso])
def exportar_hojavida_pdf(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    activo = Activo.objects.select_related("infraestructura", "datacenter").get(pk=pk)
    eventos = activo.hoja_vida.all().order_by("fecha")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Hoja de vida {activo.id_activo}")
    styles = getSampleStyleSheet()
    verde = colors.HexColor("#0d2b23")
    h = ParagraphStyle("h", parent=styles["Title"], textColor=verde, fontSize=16)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=colors.HexColor("#5a6b64"), fontSize=9)
    el = [Paragraph("Hoja de Vida del Activo", h),
          Paragraph("SUIIN-SGSI-INV-001 · SUIIN — CRIC · ISO/IEC 27001:2022", sub),
          Spacer(1, 0.4 * cm)]
    inf = getattr(activo, "infraestructura", None)
    datos = [["ID", activo.id_activo, "Nombre", activo.nombre],
             ["Clase", activo.get_clase_display(), "Riesgo", activo.get_nivel_riesgo_display()],
             ["Propietario", activo.propietario or "—", "Datacenter",
              activo.datacenter.codigo if activo.datacenter else "—"]]
    if inf:
        datos.append(["Modelo", inf.modelo or "—", "Serial", inf.serial_placa or "—"])
    t = Table(datos, colWidths=[3 * cm, 5.5 * cm, 3 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e2dd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f1")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef4f1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    el += [t, Spacer(1, 0.5 * cm), Paragraph("Registro de eventos", h), Spacer(1, 0.2 * cm)]
    filas = [["Fecha", "Tipo", "Titulo / Descripcion", "Responsable"]]
    for e in eventos:
        desc = e.titulo + (f"\n{e.descripcion}" if e.descripcion else "")
        filas.append([str(e.fecha), e.get_tipo_evento_display(),
                      Paragraph(desc, styles["Normal"]), e.responsable or "—"])
    if not eventos:
        filas.append(["—", "—", "Sin eventos registrados", "—"])
    te = Table(filas, colWidths=[2.2 * cm, 3 * cm, 8.3 * cm, 3.5 * cm], repeatRows=1)
    te.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), verde), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e2dd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f5")])]))
    el.append(te)
    doc.build(el)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="hoja_vida_{activo.id_activo}.pdf"'
    return resp


@api_view(["GET"])
@permission_classes([RolPermiso])
def qr_activo(request, pk):
    """Genera un codigo QR PNG con el enlace a la ficha del activo."""
    import qrcode
    activo = Activo.objects.get(pk=pk)
    base = request.build_absolute_uri("/")[:-1]
    url = f"{base}/?activo={activo.id_activo}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="image/png")
    resp["Content-Disposition"] = f'inline; filename="qr_{activo.id_activo}.png"'
    return resp


def _dibujar_etiqueta(c, activo, ancho, alto, base_url):
    """Dibuja una etiqueta adhesiva (70x40mm) del activo en la posicion
    actual del lienzo de ReportLab: codigo, nombre, ubicacion y QR.

    Deliberadamente NO incluye clasificacion de seguridad ni nivel de
    riesgo — un adhesivo pegado en el equipo fisico es visible para
    cualquiera que pase por el sitio, y anunciar ahi que un activo es
    "Altamente Confidencial" o "Riesgo Critico" lo convierte en un blanco
    mas facil de identificar en vez de protegerlo.
    """
    import qrcode
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader, simpleSplit

    verde = colors.HexColor("#0d2b23")
    dorado = colors.HexColor("#9a7d1f")
    gris = colors.HexColor("#5a6b64")
    texto = colors.HexColor("#1a1a1a")
    borde = colors.HexColor("#d9e2dd")

    margen = 2.5 * mm
    qr_lado = 30 * mm

    # Guia de corte sutil (util si se imprime en hoja y se recorta a mano)
    c.setStrokeColor(borde)
    c.setLineWidth(0.4)
    c.rect(0.6, 0.6, ancho - 1.2, alto - 1.2)

    # --- Codigo QR, alineado a la derecha ---
    url = f"{base_url}/?activo={activo.id_activo}"
    qr_buf = io.BytesIO()
    qrcode.make(url).save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_x = ancho - margen - qr_lado
    qr_y = (alto - qr_lado) / 2
    c.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_lado, height=qr_lado,
                preserveAspectRatio=True, mask="auto")

    # --- Columna de texto, a la izquierda del QR ---
    # Se mide todo el bloque primero para poder centrarlo verticalmente
    # (igual que el QR), en vez de dejarlo pegado arriba con un vacio
    # abajo cuando el activo no tiene nombre largo ni rack/ubicacion.
    tx = margen
    tw = qr_x - margen - (3 * mm)

    codigo = activo.id_activo or "—"
    fuente_cod = 15
    while fuente_cod > 8 and c.stringWidth(codigo, "Helvetica-Bold", fuente_cod) > tw:
        fuente_cod -= 1

    ubic = []
    if activo.datacenter_id:
        ubic.append(activo.datacenter.codigo)
    inf = getattr(activo, "infraestructura", None)
    from .rack_utils import texto_ubicacion_rack
    texto_rack = texto_ubicacion_rack(inf)
    if texto_rack:
        ubic.append(texto_rack)

    filas = [("SUIIN · CRIC", "Helvetica-Bold", 6, dorado, 1.5)]
    filas.append((codigo, "Helvetica-Bold", fuente_cod, verde, 1.25))
    for linea in simpleSplit(activo.nombre or "", "Helvetica", 6.5, tw)[:2]:
        filas.append((linea, "Helvetica", 6.5, texto, 1.35))
    if ubic:
        linea_ubic = simpleSplit(" · ".join(ubic), "Helvetica", 6, tw)[0]
        filas.append((linea_ubic, "Helvetica", 6, gris, 1.35))

    alturas = [tam * interlineado for (_, _, tam, _, interlineado) in filas]
    alto_bloque = sum(alturas)
    y = margen + (alto - 2 * margen - alto_bloque) / 2 + alto_bloque

    for (linea, fuente, tam, color, _), h in zip(filas, alturas):
        y -= h
        c.setFillColor(color)
        c.setFont(fuente, tam)
        c.drawString(tx, y + (h - tam) / 2, linea)


@api_view(["GET"])
@permission_classes([RolPermiso])
def etiqueta_activo(request, pk):
    """Etiqueta adhesiva individual (70x40mm) lista para imprimir y pegar
    en el activo fisico: codigo, nombre, ubicacion y QR a la ficha."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    activo = Activo.objects.select_related(
        "datacenter", "infraestructura", "infraestructura__rack_fk",
    ).get(pk=pk)
    base = request.build_absolute_uri("/")[:-1]
    ancho, alto = 70 * mm, 40 * mm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho, alto))
    c.setTitle(f"Etiqueta {activo.id_activo}")
    _dibujar_etiqueta(c, activo, ancho, alto, base)
    c.showPage()
    c.save()
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="etiqueta_{activo.id_activo}.pdf"'
    return resp


@api_view(["GET"])
@permission_classes([RolPermiso])
def etiquetas_lote(request):
    """Impresion masiva: una etiqueta de 70x40mm por pagina, una pagina por
    cada activo indicado en ?ids=1,2,3 (ids internos, como ya usa el QR
    individual). Pensado para imprimirse directo en una impresora de rollo
    de etiquetas adhesivas, respetando el orden de seleccion."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    ids_crudos = [s.strip() for s in request.GET.get("ids", "").split(",") if s.strip()]
    ids = []
    for s in ids_crudos:
        if s.isdigit():
            ids.append(int(s))
    if not ids:
        return JsonResponse(
            {"detail": "Indique al menos un activo valido en ?ids=1,2,3"}, status=400)

    por_pk = {a.pk: a for a in Activo.objects.select_related(
        "datacenter", "infraestructura").filter(pk__in=ids)}
    activos = [por_pk[i] for i in ids if i in por_pk]
    if not activos:
        return JsonResponse({"detail": "Ningun activo encontrado para esos ids."}, status=400)

    base = request.build_absolute_uri("/")[:-1]
    ancho, alto = 70 * mm, 40 * mm
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho, alto))
    c.setTitle("Etiquetas de activos — SUIIN")
    for activo in activos:
        _dibujar_etiqueta(c, activo, ancho, alto, base)
        c.showPage()
    c.save()
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="etiquetas_suiin.pdf"'
    return resp


@api_view(["GET"])
@permission_classes([RolPermiso])
def accesos(request):
    """Auditoria de accesos recientes."""
    regs = RegistroAcceso.objects.all()[:80]
    return Response([{"usuario": r.usuario, "tipo": r.get_accion_display(),
                      "recurso": r.recurso, "detalle": r.detalle,
                      "ip": r.ip, "fecha": r.fecha, "modulo": "Inventario"}
                     for r in regs])


def _serializar_acceso_inventario(r):
    return {"usuario": r.usuario, "tipo": r.get_accion_display(),
            "recurso": r.recurso, "detalle": r.detalle,
            "ip": r.ip, "fecha": r.fecha.isoformat(), "modulo": "Inventario"}


def _serializar_acceso_rbac(fila):
    return {
        "usuario": fila.get("responsable") or fila.get("usuario") or "",
        "tipo": fila.get("accion") or "",
        "recurso": fila.get("entidad") or "",
        "detalle": fila.get("detalle") or "",
        "ip": "",
        "fecha": fila.get("fecha") or "",
        "modulo": "RBAC",
    }


@api_view(["GET"])
@permission_classes([SoloAdministrador])
def accesos_unificado(request):
    """Panel de auditoría entre módulos — Inventario + RBAC (ISO 8.15)."""
    from .integracion_rbac import auditoria_rbac

    limite = min(int(request.GET.get("limite", 80)), 200)
    inv = [_serializar_acceso_inventario(r) for r in RegistroAcceso.objects.all()[:limite]]
    rbac_filas = auditoria_rbac(limite=limite) or []
    rbac = [_serializar_acceso_rbac(f) for f in rbac_filas]
    combinado = inv + rbac
    combinado.sort(key=lambda x: x.get("fecha") or "", reverse=True)
    return Response(combinado[:limite])


@api_view(["GET"])
@permission_classes([RolPermiso])
def integridad_lista(request):
    """Bitácora encadenada del Inventario (mismo esquema que RBAC) — las
    últimas N filas, más recientes primero."""
    limite = int(request.GET.get("limite", 80))
    regs = RegistroIntegridad.objects.order_by("-id")[:limite]
    return Response([{"id": r.id, "fecha": r.fecha, "entidad": r.entidad,
                      "accion": r.accion, "detalle": r.detalle,
                      "responsable": r.responsable, "hash": r.hash}
                     for r in regs])


@api_view(["GET"])
@permission_classes([RolPermiso])
def integridad_verificar(request):
    """Recorre toda la cadena y confirma que nadie la alteró por fuera de
    la aplicación — mismo endpoint en espíritu que
    GET /api/auditoria/verificar de RBAC."""
    integra, dato = verificar_cadena()
    if integra:
        return Response({"integra": True, "total_verificado": dato})
    return Response({"integra": False, "registro_alterado": dato})


from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.db.utils import OperationalError
import time


def _uid_desde_sesion(sesion):
    return sesion.get("_auth_user_id")


def _cargar_sesion_por_cookie(clave):
    """Carga sesión desde cookie con reintento breve (SQLite bajo ráfaga concurrente)."""
    for intento in range(3):
        sesion = SessionStore(session_key=clave)
        try:
            sesion.load()
            return _uid_desde_sesion(sesion)
        except OperationalError:
            if intento == 2:
                return None
            time.sleep(0.05 * (intento + 1))
        except Exception:
            return None
    return None


def _usuario_por_id(uid):
    for intento in range(3):
        try:
            return get_user_model().objects.get(pk=uid)
        except OperationalError:
            if intento == 2:
                raise
            time.sleep(0.05 * (intento + 1))
        except get_user_model().DoesNotExist:
            return None
    return None


def _usuario_desde_sesion(request):
    """Usuario de la sesión Django — respaldo si DRF no re-hidrato request.user."""
    user = get_user(request)
    if getattr(user, "is_authenticated", False):
        return user

    uid = None
    if request.session.session_key:
        uid = _uid_desde_sesion(request.session)

    if not uid:
        clave = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if clave:
            uid = _cargar_sesion_por_cookie(clave)

    if not uid:
        return None
    return _usuario_por_id(uid)


def _permisos_plataforma(user):
    rs = sorted(roles_de(user))
    puede_editar = bool(set(rs) & {ROL_DINAMIZADOR, ROL_ADMIN})
    return rs, puede_editar, ROL_ADMIN in rs


# Ampliar sesion_info con el rol del usuario
@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def sesion_info_v2(request):
    user = _usuario_desde_sesion(request)
    if user is None:
        return Response({
            "autenticado": False,
            "usuario": None,
            "roles": [],
            "puede_editar": False,
            "puede_eliminar": False,
        }, headers={"Cache-Control": "no-store"})
    rs, puede_editar, puede_eliminar = _permisos_plataforma(user)
    return Response({
        "autenticado": True,
        "usuario": user.get_username(),
        "roles": rs, "puede_editar": puede_editar, "puede_eliminar": puede_eliminar},
        headers={"Cache-Control": "no-store"})


# --- Login/Logout propios para el tablero (permite roles no-staff) ---
from django.contrib.auth import authenticate as _auth_login_user
from django.contrib.auth import login as _auth_login
from django.contrib.auth import logout as _logout
from django.shortcuts import redirect


def _respuesta_sesion(user):
    rs, puede_editar, puede_eliminar = _permisos_plataforma(user)
    return {
        "autenticado": True,
        "usuario": user.get_username(),
        "roles": rs,
        "puede_editar": puede_editar,
        "puede_eliminar": puede_eliminar,
    }


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def api_login(request):
    """Login JSON para la SPA de React — misma sesión por cookie que /login/.

    GET prepara la cookie CSRF (mismo patrón que LoginView en HTML).
    POST valida credenciales con django-axes y abre sesión real
    (django.contrib.auth.login), no solo un JWT.
    """
    if request.method == "GET":
        return Response({"listo": True})

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return Response({"detail": "Usuario y contraseña son obligatorios."}, status=400)

    from axes.handlers.proxy import AxesProxyHandler

    credenciales = {"username": username}
    if AxesProxyHandler.is_locked(request, credenciales):
        return Response(
            {"detail": "Acceso bloqueado temporalmente por demasiados intentos fallidos."},
            status=429,
        )

    user = _auth_login_user(request, username=username, password=password)
    if user is None:
        return Response({"detail": "Usuario o contraseña incorrectos."}, status=401)

    _auth_login(request, user)
    return Response(_respuesta_sesion(user))


def logout_view(request):
    _logout(request)
    return redirect("/")


# ---------------------------------------------------------------------------
# Despliegue integrado — puerta de autorización para SUIIN-RBAC
# ---------------------------------------------------------------------------
# SUIIN-RBAC (Flask, API JSON bajo /rbac/api/) no tiene inicio de sesión
# propio por diseño. nginx delega la autorización en la sesión del
# Inventario (auth_request) antes de reenviar a Flask.
#
# Devuelve 204 si la sesión activa tiene rol Dinamizador o Administrador
# (lectura y escritura), o Consultor solo en peticiones GET de la SPA
# (lectura de /rbac/api/). 401 en caso contrario.
@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_check_rbac(request):
    from .permisos import ROL_CONSULTOR

    user = _usuario_desde_sesion(request)
    if user is None:
        return Response(status=401, headers={"Cache-Control": "no-store"})
    rs = roles_de(user)
    metodo_original = request.META.get("HTTP_X_ORIGINAL_METHOD", "GET").upper()
    puede_editar = bool(rs & {ROL_DINAMIZADOR, ROL_ADMIN})
    puede_leer = puede_editar or (ROL_CONSULTOR in rs and metodo_original == "GET")
    if puede_leer:
        resp = Response(status=204, headers={"Cache-Control": "no-store"})
        resp["X-Usuario-Autorizado"] = user.get_username()
        return resp
    return Response(status=401, headers={"Cache-Control": "no-store"})


@api_view(["GET"])
@permission_classes([AllowAny])
def catalogo_mitre_interno(request):
    """Catálogo MITRE para sync servidor-a-servidor (Riesgos/RBAC).

    No usa sesión de usuario: exige cabecera X-Plataforma-Secret = JWT_SHARED_SECRET.
    Misma respuesta paginada que /api/amenazas/ pero accesible desde la red interna
    de docker-compose sin depender de RolPermisoOServicioInterno en el ViewSet.
    """
    from django.conf import settings
    secreto = request.headers.get("X-Plataforma-Secret", "")
    if not settings.JWT_SHARED_SECRET or secreto != settings.JWT_SHARED_SECRET:
        return Response(
            {"detail": "Acceso denegado. Configure JWT_SHARED_SECRET en .env y envíe "
             "X-Plataforma-Secret en la petición."},
            status=403,
        )
    try:
        page_size = min(max(int(request.GET.get("page_size", 200)), 1), 2000)
        page = max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        return Response({"detail": "page y page_size deben ser enteros."}, status=400)

    qs = AmenazaMITRE.objects.all().order_by("codigo")
    total = qs.count()
    inicio = (page - 1) * page_size
    fin = inicio + page_size
    resultados = AmenazaMITRESerializer(qs[inicio:fin], many=True).data

    def _url(p):
        if p < 1 or (p - 1) * page_size >= total:
            return None
        return request.build_absolute_uri(
            f"{request.path}?page={p}&page_size={page_size}")

    return Response({
        "count": total,
        "next": _url(page + 1) if fin < total else None,
        "previous": _url(page - 1) if page > 1 else None,
        "results": resultados,
    })


@api_view(["GET"])
@permission_classes([RolPermiso])
def catalogo_sistemas_rbac_view(request):
    """Catálogo de sistemas RBAC para vincular activos SIST (Ola 2)."""
    from .integracion_rbac import catalogo_sistemas_rbac
    data = catalogo_sistemas_rbac()
    if data is None:
        return Response({"disponible": False, "sistemas": []})
    return Response({
        "disponible": True,
        "sistemas": [{
            "id": s.get("id"),
            "nombre": s.get("nombre"),
            "categoria": s.get("categoria"),
            "clasificacion": s.get("clasificacion"),
            "excepciones_vigentes": s.get("excepciones_vigentes", 0),
        } for s in data],
    })


# ---------------------------------------------------------------------------
# Sesión única con SUIIN-SGSI-RIESGOS — emisión de JWT
# ---------------------------------------------------------------------------
from django.contrib.auth import authenticate as _authenticate
from .jwt_plataforma import emitir_jwt, JWTNoConfigurado


@api_view(["GET"])
@permission_classes([AllowAny])
def jwt_version_usuario(request, username):
    """Versión vigente del JWT para un usuario — solo backends internos
    (Riesgos) con el secreto compartido; invalida tokens emitidos antes de
    un cambio de rol."""
    secreto = request.headers.get("X-Plataforma-Secret", "")
    if not settings.JWT_SHARED_SECRET or secreto != settings.JWT_SHARED_SECRET:
        return Response(status=403)
    from .models import PerfilPlataforma
    try:
        ver = PerfilPlataforma.objects.get(user__username=username).jwt_version
    except PerfilPlataforma.DoesNotExist:
        ver = 1
    return Response({"username": username, "ver": ver})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def token_jwt(request):
    """
    GET  — usa la sesión ya activa (cookie) del Inventario, si hay una.
    POST — {"username": ..., "password": ...}: valida credenciales directo
           (permite iniciar sesión desde la pantalla de Riesgos sin haber
           pasado antes por /login/ del Inventario — mismo usuario y
           contraseña, protegido por django-axes igual que /login/).

    Devuelve {"token": "...", "expira": "...", "username": "...", "roles": [...]}
    o 401 si no hay sesión / las credenciales son inválidas.
    """
    user = _usuario_desde_sesion(request)

    if user is None and request.method == "POST":
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = _authenticate(request, username=username, password=password)
        if user is not None:
            # django-axes solo resetea el contador de fallos en un login
            # exitoso si se llama a django.contrib.auth.login() (señal
            # user_logged_in) — esta rama valida credenciales pero no abre
            # sesión de verdad (entrega un JWT en su lugar), así que el
            # reset se hace explícito. La rama GET de arriba no lo necesita:
            # ya viene de una sesión creada por /login/, que sí pasa por
            # LoginView y por lo tanto sí dispara el reset normalmente.
            from axes.utils import reset
            reset(username=username, ip=request.META.get("REMOTE_ADDR"))

    if user is None:
        return Response({"detail": "No hay sesión activa ni credenciales válidas."}, status=401)

    try:
        token, expira = emitir_jwt(user)
    except JWTNoConfigurado as e:
        return Response({"detail": str(e)}, status=503)

    return Response({
        "token": token,
        "expira": expira.isoformat(),
        "username": user.get_username(),
        "roles": sorted(roles_de(user)),
    }, headers={"Cache-Control": "no-store"})

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate

from .auth_jwt import ROLES_CON_ESCRITURA
from .models import (
    Activo, PuertoServicio, Vulnerabilidad, RiesgoActivo, RiesgoContextual,
    CampanaRedTeam, PlanTratamientoRiesgos, AccionTratamiento, ControlISO27001,
    Evidencia, CatalogoValor, TecnicaMitre,
)
from .serializers import (
    ActivoListSerializer, ActivoDetailSerializer, PuertoServicioSerializer,
    VulnerabilidadSerializer, RiesgoActivoSerializer, RiesgoContextualSerializer,
    CampanaRedTeamSerializer, PlanTratamientoRiesgosListSerializer,
    PlanTratamientoRiesgosDetailSerializer, AccionTratamientoSerializer,
    ControlISO27001Serializer, EvidenciaSerializer, CatalogoValorSerializer,
    TecnicaMitreSerializer,
)


class HistorialMixin:
    """
    Agrega GET /api/<recurso>/{id}/historial/ a cualquier ViewSet cuyo modelo tenga
    HistoricalRecords() (django-simple-history). Devuelve una lista de versiones con
    el diff campo a campo contra la versión inmediatamente anterior.
    """
    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        obj = self.get_object()
        registros = list(obj.historial.all().order_by("-history_date"))
        TIPO_LABEL = {"+": "Creación", "~": "Edición", "-": "Eliminación"}
        resultado = []
        for i, record in enumerate(registros):
            anterior = registros[i + 1] if i + 1 < len(registros) else None
            cambios = []
            if anterior:
                delta = record.diff_against(anterior)
                for change in delta.changes:
                    cambios.append({
                        "campo": change.field,
                        "antes": "" if change.old is None else str(change.old),
                        "despues": "" if change.new is None else str(change.new),
                    })
            resultado.append({
                "fecha": record.history_date,
                "usuario": record.history_user.username if record.history_user else "—",
                "tipo": TIPO_LABEL.get(record.history_type, record.history_type),
                "cambios": cambios,
            })
        return Response(resultado)


class ActivoViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = Activo.objects.all().select_related("campana_red_team").annotate(
        total_vulnerabilidades_ann=Count("vulnerabilidades", distinct=True),
        vulnerabilidades_criticas_ann=Count(
            "vulnerabilidades", filter=Q(vulnerabilidades__severidad_ov="CRITICAL"), distinct=True),
    ).order_by("id_activo")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "riesgo_matriz", "clasificacion_si", "cobertura", "afectado_red_team", "tipo", "inventario_id",
    ]
    search_fields = ["id_activo", "nombre", "ip_principal"]
    ordering_fields = ["valor", "id_activo", "nombre"]

    def get_serializer_class(self):
        if self.action == "list":
            return ActivoListSerializer
        return ActivoDetailSerializer

    def create(self, request, *args, **kwargs):
        from django.conf import settings
        if getattr(settings, "PLATAFORMA_ACTIVOS_SOLO_INVENTARIO", False):
            return Response({
                "detail": "En la plataforma unificada los activos se crean en el Inventario. "
                          "Use sincronizar_activos_inventario o ./desplegar.sh para reflejarlos aquí.",
            }, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="hoja-riesgo.pdf")
    def hoja_riesgo_pdf(self, request, pk=None):
        """Hoja de riesgo del activo en PDF — vulnerabilidades, riesgos evaluados,
        acciones de tratamiento vinculadas y evidencia adjunta, todo en un solo
        documento descargable. Equivalente en riesgos a hojavida.pdf del Inventario."""
        from django.http import HttpResponse
        from .pdf_hoja_riesgo import generar_hoja_riesgo_pdf
        activo = self.get_object()
        buf = generar_hoja_riesgo_pdf(activo)
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="hoja_riesgo_{activo.id_activo}.pdf"'
        return resp


class PuertoServicioViewSet(viewsets.ModelViewSet):
    queryset = PuertoServicio.objects.select_related("activo").all()
    serializer_class = PuertoServicioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo"]


class VulnerabilidadViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = Vulnerabilidad.objects.select_related("activo").all()
    serializer_class = VulnerabilidadSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["severidad_ov", "nivel_riesgo", "estado", "activo", "tratamiento"]
    search_fields = ["nombre_vulnerabilidad", "cves", "activo__id_activo", "activo__nombre"]
    ordering_fields = ["score", "cvss"]

    @action(detail=False, methods=["post"], url_path="bulk-actualizar")
    def bulk_actualizar(self, request):
        """
        POST /api/vulnerabilidades/bulk-actualizar/  {ids: [...], campos: {estado: "X", tratamiento: "Y"}}

        Hallazgo del análisis de gestionabilidad del 2026-08-24: con 225
        vulnerabilidades, cambiar el estado de varias a la vez (ej. tras un
        ciclo de parches) significaba abrirlas una por una — ningún listado
        del sistema tenía operaciones en lote todavía.

        Guarda cada objeto por separado (no un UPDATE masivo de una sola
        pasada) a propósito: django-simple-history solo registra el
        historial en la señal post_save de cada .save() individual — un
        QuerySet.update() la salta por completo y dejaría el cambio en lote
        sin rastro de auditoría, algo que no es aceptable en este sistema.
        """
        ids = request.data.get("ids", [])
        campos = request.data.get("campos", {})
        CAMPOS_PERMITIDOS = {"estado", "tratamiento"}
        campos_validos = {k: v for k, v in campos.items() if k in CAMPOS_PERMITIDOS and v}

        if not ids:
            return Response({"detail": "Se requiere 'ids' (lista no vacía)."}, status=400)
        if not campos_validos:
            return Response(
                {"detail": f"Se requiere al menos un campo permitido en 'campos': {sorted(CAMPOS_PERMITIDOS)}."},
                status=400)

        actualizados = 0
        for obj in Vulnerabilidad.objects.filter(id__in=ids):
            for campo, valor in campos_validos.items():
                setattr(obj, campo, valor)
            obj.save()
            actualizados += 1

        return Response({"actualizados": actualizados, "campos_aplicados": campos_validos})


class RiesgoActivoViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = RiesgoActivo.objects.select_related("activo").all()
    serializer_class = RiesgoActivoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["nivel_riesgo", "tratamiento", "estado", "activo"]
    ordering_fields = ["score"]


class RiesgoContextualViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = RiesgoContextual.objects.prefetch_related("activos_relacionados").all()
    serializer_class = RiesgoContextualSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["nivel_riesgo", "clasificacion_si", "estado_actual"]
    ordering_fields = ["score"]


class CampanaRedTeamViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = CampanaRedTeam.objects.all()
    serializer_class = CampanaRedTeamSerializer


class PlanTratamientoRiesgosViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = PlanTratamientoRiesgos.objects.select_related("campana_red_team").prefetch_related("acciones")
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["estado_plan", "campana_red_team"]
    ordering_fields = ["fecha_emision", "referencia"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            incluir = self.request.query_params.get("incluir_archivados", "").lower() in ("1", "true", "yes")
            if not incluir:
                qs = qs.filter(estado_plan="ACTIVO")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PlanTratamientoRiesgosListSerializer
        return PlanTratamientoRiesgosDetailSerializer

    @action(detail=True, methods=["get"], url_path="informe.pdf")
    def informe_pdf(self, request, pk=None):
        from django.http import HttpResponse
        from .pdf_informe_ptr import generar_informe_ptr_pdf
        plan = self.get_object()
        buf = generar_informe_ptr_pdf(plan)
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="informe_ptr_{plan.referencia.replace(" ", "_")}.pdf"'
        return resp


class AccionTratamientoViewSet(HistorialMixin, viewsets.ModelViewSet):
    queryset = AccionTratamiento.objects.select_related("plan").all()
    serializer_class = AccionTratamientoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["fase", "estado", "nivel_riesgo", "opcion_tratamiento", "plan"]
    ordering_fields = ["score", "id_riesgo"]


class ControlISO27001ViewSet(HistorialMixin, viewsets.ModelViewSet):
    # Nota: el orden natural (5.2 antes de 5.10) se resuelve en el frontend — hacerlo
    # aquí con Python sobre una lista rompería el encadenamiento de filter_backends
    # (DjangoFilterBackend/SearchFilter necesitan un QuerySet real, no una lista).
    # acciones_count / riesgos_contextuales_count se resuelven en el serializer vía
    # el manager relacionado (.count()), no por anotación — no hace falta anotar aquí.
    queryset = ControlISO27001.objects.all()
    serializer_class = ControlISO27001Serializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["categoria", "aplicable", "estado_implementacion"]
    search_fields = ["codigo", "nombre"]


class TecnicaMitreViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/tecnicas-mitre/?search=T1190 — de solo lectura, el catálogo se
    mantiene sincronizado desde el Inventario (sincronizar_tecnicas_mitre),
    no se edita campo a campo aquí."""
    queryset = TecnicaMitre.objects.all()
    serializer_class = TecnicaMitreSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tipo"]
    search_fields = ["codigo", "nombre", "tacticas"]
    ordering_fields = ["codigo", "nombre"]


class CatalogoValorViewSet(viewsets.ModelViewSet):
    """
    GET  /api/catalogo/?categoria=TIPO_ACTIVO         → valores de esa categoría
    (por defecto solo activos=True; ?activo=false para ver los desactivados,
    útil en la página de gestión del catálogo)
    POST /api/catalogo/obtener-o-crear/  {categoria, valor} → idempotente: usa
    el existente si ya está (case-insensitive, sin espacios sobrantes), o crea
    uno nuevo — es lo que llama el combo del formulario al escribir un valor
    que todavía no está en la lista.
    """
    queryset = CatalogoValor.objects.all()
    serializer_class = CatalogoValorSerializer
    filterset_fields = ["categoria"]

    def get_queryset(self):
        qs = super().get_queryset()
        activo_param = self.request.query_params.get("activo")
        if activo_param is None:
            qs = qs.filter(activo=True)
        elif activo_param.lower() in ("false", "0"):
            qs = qs.filter(activo=False)
        return qs

    @action(detail=False, methods=["post"], url_path="obtener-o-crear")
    def obtener_o_crear(self, request):
        categoria = request.data.get("categoria", "").strip()
        valor = request.data.get("valor", "").strip()
        if not categoria or not valor:
            return Response({"detail": "Se requieren 'categoria' y 'valor'."}, status=400)

        existente = CatalogoValor.objects.filter(categoria=categoria, valor__iexact=valor).first()
        if existente:
            if not existente.activo:
                existente.activo = True
                existente.save(update_fields=["activo"])
            return Response(CatalogoValorSerializer(existente).data, status=200)

        obj = CatalogoValor.objects.create(categoria=categoria, valor=valor)
        return Response(CatalogoValorSerializer(obj).data, status=201)


class EvidenciaViewSet(viewsets.ModelViewSet):
    """
    GET  /api/evidencias/?modelo=vulnerabilidad&object_id=4   → evidencia de ese registro
    POST /api/evidencias/  (multipart/form-data: modelo, object_id, archivo, descripcion)
    """
    queryset = Evidencia.objects.select_related("content_type", "subido_por").all()
    serializer_class = EvidenciaSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        modelo = self.request.query_params.get("modelo")
        object_id = self.request.query_params.get("object_id")
        if modelo:
            qs = qs.filter(content_type__model=modelo)
        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def auth_login(request):
    """Login simple por token para la SPA. Devuelve {token, username} o 400 si las
    credenciales son inválidas. El usuario debe existir previamente (ver
    `python manage.py createsuperuser` o el admin de Django)."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({"detail": "Usuario o contraseña incorrectos."},
                         status=status.HTTP_400_BAD_REQUEST)
    # django-axes resetea el contador de fallos en un login exitoso solo si se
    # llama a django.contrib.auth.login() (se engancha a la señal
    # user_logged_in) — esta vista no la usa, entrega un token DRF en su
    # lugar, así que el reset se hace explícito aquí. Sin esto, alguien que
    # se equivocó 3 veces y luego acertó la clave seguiría acumulando ese
    # historial de fallos en vez de arrancar de cero.
    from axes.utils import reset
    reset(username=username, ip=request.META.get("REMOTE_ADDR"))
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "username": user.username, "is_staff": user.is_staff})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_me(request):
    roles = []
    puede_editar = True
    if isinstance(request.auth, dict):
        roles = request.auth.get("roles", [])
        puede_editar = bool(set(roles) & ROLES_CON_ESCRITURA)
    return Response({
        "username": request.user.username,
        "is_staff": request.user.is_staff,
        "roles": roles,
        "puede_editar": puede_editar,
    })


@api_view(["GET"])
def alertas_resumen(request):
    """
    Acciones de tratamiento, riesgos por activo y riesgos contextuales con fecha
    límite/objetivo vencida o próxima a vencer (7 días). Solo considera registros
    con fecha real definida y no cerrados — es la contraparte "operativa" del
    dashboard de riesgo.
    """
    acciones = AccionTratamiento.objects.exclude(fecha_limite=None).exclude(
        estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"]).select_related("plan")
    riesgos = RiesgoActivo.objects.exclude(fecha_objetivo=None).exclude(
        estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"]).select_related("activo")
    riesgos_ctx = RiesgoContextual.objects.exclude(fecha_limite=None).exclude(
        estado__in=["CERRADO", "FALSO_POSITIVO", "ACEPTADO"])

    acciones_vencidas = [a for a in acciones if a.esta_vencida]
    acciones_por_vencer = [a for a in acciones if a.por_vencer]
    riesgos_vencidos = [r for r in riesgos if r.esta_vencido]
    riesgos_por_vencer = [r for r in riesgos if r.por_vencer]
    ctx_vencidos = [r for r in riesgos_ctx if r.esta_vencido]
    ctx_por_vencer = [r for r in riesgos_ctx if r.por_vencer]

    return Response({
        "total_vencidas": len(acciones_vencidas) + len(riesgos_vencidos) + len(ctx_vencidos),
        "total_por_vencer": len(acciones_por_vencer) + len(riesgos_por_vencer) + len(ctx_por_vencer),
        "acciones_vencidas": AccionTratamientoSerializer(acciones_vencidas, many=True).data,
        "acciones_por_vencer": AccionTratamientoSerializer(acciones_por_vencer, many=True).data,
        "riesgos_activo_vencidos": RiesgoActivoSerializer(riesgos_vencidos, many=True).data,
        "riesgos_activo_por_vencer": RiesgoActivoSerializer(riesgos_por_vencer, many=True).data,
        "riesgos_contextuales_vencidos": RiesgoContextualSerializer(ctx_vencidos, many=True).data,
        "riesgos_contextuales_por_vencer": RiesgoContextualSerializer(ctx_por_vencer, many=True).data,
    })


@api_view(["GET"])
def cumplimiento_resumen(request):
    """
    Cobertura del Anexo A: por cada control aplicable, ¿tiene evidencia (al menos
    una acción de tratamiento o riesgo contextual vinculado)? Agregado por categoría
    y global — es la vista que responde "¿qué tan cubierto está el SoA en la práctica?"
    """
    controles = ControlISO27001.objects.prefetch_related("acciones_tratamiento", "riesgos_contextuales")

    def con_evidencia(c):
        return c.acciones_tratamiento.exists() or c.riesgos_contextuales.exists()

    por_categoria = {}
    for cat_key, cat_label in ControlISO27001.CATEGORIA_CHOICES:
        controles_cat = [c for c in controles if c.categoria == cat_key]
        aplicables = [c for c in controles_cat if c.aplicable]
        con_ev = [c for c in aplicables if con_evidencia(c)]
        por_categoria[cat_key] = {
            "categoria": cat_key,
            "categoria_display": cat_label,
            "total": len(controles_cat),
            "aplicables": len(aplicables),
            "con_evidencia": len(con_ev),
            "sin_evidencia": len(aplicables) - len(con_ev),
            "porcentaje_cobertura": round((len(con_ev) / len(aplicables)) * 100) if aplicables else 0,
        }

    todos_aplicables = [c for c in controles if c.aplicable]
    todos_con_ev = [c for c in todos_aplicables if con_evidencia(c)]

    distribucion_estado = {}
    for key, label in ControlISO27001.ESTADO_IMPLEMENTACION_CHOICES:
        distribucion_estado[key] = controles.filter(estado_implementacion=key).count()

    return Response({
        "total_controles": controles.count(),
        "total_aplicables": len(todos_aplicables),
        "total_con_evidencia": len(todos_con_ev),
        "porcentaje_cobertura_global": round((len(todos_con_ev) / len(todos_aplicables)) * 100) if todos_aplicables else 0,
        "por_categoria": list(por_categoria.values()),
        "distribucion_estado_implementacion": distribucion_estado,
        "controles_sin_evidencia": ControlISO27001Serializer(
            [c for c in todos_aplicables if not con_evidencia(c)], many=True
        ).data,
        "controles_con_detalle": [
            {
                "id": c.id,
                "codigo": c.codigo,
                "nombre": c.nombre,
                "categoria": c.categoria,
                "acciones": [
                    {"id": a.id, "id_riesgo": a.id_riesgo, "plan_id": a.plan_id, "plan_referencia": a.plan.referencia}
                    for a in c.acciones_tratamiento.select_related("plan").all()[:20]
                ],
                "riesgos_contextuales": [
                    {"id": r.id, "id_riesgo_contextual": r.id_riesgo_contextual}
                    for r in c.riesgos_contextuales.all()[:20]
                ],
            }
            for c in todos_aplicables if con_evidencia(c)
        ],
    })


@api_view(["GET"])
def dashboard_resumen(request):
    """
    Agregaciones para el panel principal: KPIs, mapa de calor Probabilidad x Impacto
    (ISO/IEC 27005), distribución por nivel de riesgo y avance global de tratamiento.
    """
    activos = Activo.objects.all()
    vulns = Vulnerabilidad.objects.all()
    riesgos_activo = RiesgoActivo.objects.all()
    riesgos_contextuales = RiesgoContextual.objects.all()
    acciones = AccionTratamiento.objects.all()

    def distribucion_nivel(qs):
        agregados = qs.values("nivel_riesgo").annotate(total=Count("id"))
        base = {"CRITICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0, "SIN_DATO": 0}
        for row in agregados:
            base[row["nivel_riesgo"]] = row["total"]
        return base

    # Mapa de calor: combina RiesgoActivo + Vulnerabilidad + RiesgoContextual como
    # "hallazgos de riesgo" únicos, cada uno con su celda (probabilidad, impacto).
    heatmap = {}
    for qs in (riesgos_activo.values("probabilidad", "impacto"),
               vulns.exclude(probabilidad=None).values("probabilidad", "impacto"),
               riesgos_contextuales.values("probabilidad", "impacto")):
        for row in qs:
            key = (row["probabilidad"], row["impacto"])
            heatmap[key] = heatmap.get(key, 0) + 1
    heatmap_cells = [
        {"probabilidad": p, "impacto": i, "total": total}
        for (p, i), total in heatmap.items()
    ]

    campanas = CampanaRedTeam.objects.annotate(num_activos=Count("activos"))

    data = {
        "kpis": {
            "total_activos": activos.count(),
            "activos_sin_cobertura": activos.filter(cobertura="SIN_COBERTURA").count(),
            "activos_comprometidos": activos.filter(afectado_red_team=True).count(),
            "total_vulnerabilidades": vulns.count(),
            "vulnerabilidades_criticas": vulns.filter(severidad_ov="CRITICAL").count(),
            "riesgos_contextuales_criticos": riesgos_contextuales.filter(nivel_riesgo="CRITICO").count(),
            "acciones_pendientes": acciones.filter(estado="PENDIENTE").count(),
            "acciones_cerradas": acciones.filter(estado__in=["CERRADO", "FALSO_POSITIVO"]).count(),
            "acciones_total": acciones.count(),
        },
        "distribucion_riesgo_activos": distribucion_nivel(riesgos_activo),
        "distribucion_riesgo_vulnerabilidades": distribucion_nivel(vulns),
        "distribucion_riesgo_contextual": distribucion_nivel(riesgos_contextuales),
        "heatmap_probabilidad_impacto": heatmap_cells,
        "campanas_red_team": [
            {
                "nombre": c.nombre, "host_ip": c.host_ip, "estado_compromiso": c.estado_compromiso,
                "riesgos_criticos": c.riesgos_criticos, "riesgos_altos": c.riesgos_altos,
                "riesgos_medios": c.riesgos_medios, "riesgos_bajos": c.riesgos_bajos,
                "num_activos": c.num_activos,
            } for c in campanas
        ],
        "activos_criticos_top": ActivoListSerializer(
            Activo.objects.filter(riesgo_matriz="CRITICO").annotate(
                total_vulnerabilidades_ann=Count("vulnerabilidades", distinct=True),
                vulnerabilidades_criticas_ann=Count(
                    "vulnerabilidades", filter=Q(vulnerabilidades__severidad_ov="CRITICAL"), distinct=True),
            ).order_by("-valor")[:10], many=True
        ).data,
    }
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def importar_excel(request):
    """POST multipart: matriz_riesgos y/o ptr (uno o varios archivos .xlsx)."""
    import os
    import tempfile
    from django.db import transaction
    from riesgos.management.commands.importar_matrices import Command

    matriz = request.FILES.get("matriz_riesgos")
    ptr_files = request.FILES.getlist("ptr")
    if not matriz and not ptr_files:
        return Response({"detail": "Envíe al menos matriz_riesgos y/o ptr (.xlsx)."}, status=400)

    forzar = request.data.get("forzar_sobrescritura", "").lower() in ("1", "true", "yes")
    cmd = Command()
    cmd.stdout = cmd.stderr = open(os.devnull, "w")
    cmd.protector = None

    resumen = {"matriz_riesgos": False, "ptr_importados": 0, "errores": []}
    tmp_paths = []

    try:
        if matriz:
            if not matriz.name.lower().endswith((".xlsx", ".xls")):
                return Response({"detail": "matriz_riesgos debe ser .xlsx"}, status=400)
            fd, path = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            with open(path, "wb") as f:
                for chunk in matriz.chunks():
                    f.write(chunk)
            tmp_paths.append(path)
            with transaction.atomic():
                cmd.protector = __import__("riesgos.sincronizacion", fromlist=["ProtectorSincronizacion"]).ProtectorSincronizacion(forzar=forzar)
                cmd.importar_matriz_riesgos(path)
            resumen["matriz_riesgos"] = True

        for ptr in ptr_files:
            if not ptr.name.lower().endswith((".xlsx", ".xls")):
                resumen["errores"].append(f"{ptr.name}: formato no válido")
                continue
            fd, path = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            with open(path, "wb") as f:
                for chunk in ptr.chunks():
                    f.write(chunk)
            tmp_paths.append(path)
            with transaction.atomic():
                if cmd.protector is None:
                    cmd.protector = __import__("riesgos.sincronizacion", fromlist=["ProtectorSincronizacion"]).ProtectorSincronizacion(forzar=forzar)
                cmd.importar_ptr(path)
            resumen["ptr_importados"] += 1
    except Exception as exc:
        return Response({**resumen, "detail": str(exc)}, status=500)
    finally:
        for path in tmp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass
        cmd.stdout.close()

    return Response({"ok": True, **resumen})

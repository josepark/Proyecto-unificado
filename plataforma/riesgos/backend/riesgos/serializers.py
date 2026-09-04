from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    Activo, PuertoServicio, Vulnerabilidad, RiesgoActivo, RiesgoContextual,
    CampanaRedTeam, PlanTratamientoRiesgos, AccionTratamiento, ControlISO27001,
    Evidencia, MODELOS_CON_EVIDENCIA, CatalogoValor, TecnicaMitre,
)


class TecnicaMitreSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = TecnicaMitre
        fields = ("id", "codigo", "nombre", "tipo", "tipo_display", "tacticas", "codigo_padre", "url")


class CatalogoValorSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)

    class Meta:
        model = CatalogoValor
        fields = "__all__"

    def validate_valor(self, valor):
        return valor.strip()


class EvidenciaSerializer(serializers.ModelSerializer):
    """
    Expone `modelo` como slug legible (ej. 'vulnerabilidad') en vez del ID crudo
    de ContentType — el frontend nunca necesita conocer esos IDs internos.
    """
    modelo = serializers.CharField(write_only=True)
    modelo_actual = serializers.SerializerMethodField()
    subido_por_username = serializers.CharField(source="subido_por.username", read_only=True, default=None)
    archivo_url = serializers.SerializerMethodField()
    tipo_archivo_display = serializers.CharField(source="get_tipo_archivo_display", read_only=True, default="")

    class Meta:
        model = Evidencia
        fields = [
            "id", "modelo", "modelo_actual", "object_id", "archivo", "archivo_url",
            "nombre_original", "tipo_archivo", "tipo_archivo_display", "tamano_bytes",
            "descripcion", "subido_por_username", "creado_en",
        ]
        read_only_fields = ["nombre_original", "tipo_archivo", "tamano_bytes"]
        extra_kwargs = {"archivo": {"write_only": True}}

    def get_modelo_actual(self, obj):
        return obj.content_type.model

    def get_archivo_url(self, obj):
        request = self.context.get("request")
        if not obj.archivo:
            return None
        url = obj.archivo.url
        return request.build_absolute_uri(url) if request else url

    def validate_modelo(self, valor):
        if valor not in MODELOS_CON_EVIDENCIA:
            raise serializers.ValidationError(
                f"'{valor}' no admite evidencia. Modelos válidos: {', '.join(MODELOS_CON_EVIDENCIA)}.")
        return valor

    def create(self, validated_data):
        modelo_slug = validated_data.pop("modelo")
        content_type = ContentType.objects.get(app_label="riesgos", model=modelo_slug)
        # Confirma que el objeto destino realmente existe antes de adjuntarle un
        # archivo huérfano — un object_id inventado fallaría más adelante, pero es
        # mejor rechazarlo aquí con un mensaje claro.
        Modelo = content_type.model_class()
        object_id = validated_data["object_id"]
        if not Modelo.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError(
                {"object_id": f"No existe un(a) {modelo_slug} con id={object_id}."})
        validated_data["content_type"] = content_type
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["subido_por"] = request.user
        return super().create(validated_data)


class ControlISO27001Serializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    estado_implementacion_display = serializers.CharField(source="get_estado_implementacion_display", read_only=True)
    acciones_count = serializers.IntegerField(source="acciones_tratamiento.count", read_only=True)
    riesgos_contextuales_count = serializers.IntegerField(source="riesgos_contextuales.count", read_only=True)

    class Meta:
        model = ControlISO27001
        fields = "__all__"


class PuertoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuertoServicio
        fields = "__all__"


class VulnerabilidadSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(source="activo.nombre", read_only=True)
    activo_id_activo = serializers.CharField(source="activo.id_activo", read_only=True)
    severidad_ov_display = serializers.CharField(source="get_severidad_ov_display", read_only=True)
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Vulnerabilidad
        fields = "__all__"
        read_only_fields = ["score", "nivel_riesgo"]


class CampanaRedTeamSerializer(serializers.ModelSerializer):
    estado_compromiso_display = serializers.CharField(source="get_estado_compromiso_display", read_only=True)
    total_riesgos = serializers.SerializerMethodField()
    riesgos_actuales_por_nivel = serializers.ReadOnlyField()

    class Meta:
        model = CampanaRedTeam
        fields = "__all__"

    def get_total_riesgos(self, obj):
        return obj.riesgos_criticos + obj.riesgos_altos + obj.riesgos_medios + obj.riesgos_bajos


class ActivoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para tablas/listados."""
    riesgo_matriz_display = serializers.CharField(source="get_riesgo_matriz_display", read_only=True)
    clasificacion_si_display = serializers.CharField(source="get_clasificacion_si_display", read_only=True)
    cobertura_display = serializers.CharField(source="get_cobertura_display", read_only=True)
    campana_red_team_nombre = serializers.CharField(source="campana_red_team.nombre", read_only=True)
    total_vulnerabilidades = serializers.IntegerField(source="total_vulnerabilidades_ann", read_only=True)
    vulnerabilidades_criticas = serializers.IntegerField(source="vulnerabilidades_criticas_ann", read_only=True)

    class Meta:
        model = Activo
        fields = [
            "id", "id_activo", "nombre", "tipo", "ip_principal", "valor", "riesgo_matriz",
            "riesgo_matriz_display", "clasificacion_si", "clasificacion_si_display", "vlan",
            "en_nmap", "cobertura", "cobertura_display", "afectado_red_team",
            "campana_red_team_nombre", "total_vulnerabilidades", "vulnerabilidades_criticas",
        ]


class ActivoDetailSerializer(serializers.ModelSerializer):
    puertos = PuertoServicioSerializer(many=True, read_only=True)
    vulnerabilidades = VulnerabilidadSerializer(many=True, read_only=True)
    campana_red_team = CampanaRedTeamSerializer(read_only=True)
    campana_red_team_id = serializers.PrimaryKeyRelatedField(
        source="campana_red_team", queryset=CampanaRedTeam.objects.all(),
        write_only=True, required=False, allow_null=True)
    riesgo_matriz_display = serializers.CharField(source="get_riesgo_matriz_display", read_only=True)
    clasificacion_si_display = serializers.CharField(source="get_clasificacion_si_display", read_only=True)

    class Meta:
        model = Activo
        fields = "__all__"


class RiesgoActivoSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(source="activo.nombre", read_only=True)
    activo_id_activo = serializers.CharField(source="activo.id_activo", read_only=True)
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    tratamiento_display = serializers.CharField(source="get_tratamiento_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)
    por_vencer = serializers.BooleanField(read_only=True)

    class Meta:
        model = RiesgoActivo
        fields = "__all__"
        read_only_fields = ["score", "nivel_riesgo"]


class RiesgoContextualSerializer(serializers.ModelSerializer):
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    activos_relacionados_ids = serializers.PrimaryKeyRelatedField(
        source="activos_relacionados", many=True, queryset=Activo.objects.all(), required=False)
    activos_relacionados_resumen = serializers.SerializerMethodField()
    controles_iso_vinculados_resumen = serializers.SerializerMethodField()
    dias_para_vencer = serializers.IntegerField(read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)
    por_vencer = serializers.BooleanField(read_only=True)

    class Meta:
        model = RiesgoContextual
        fields = "__all__"
        read_only_fields = ["score", "nivel_riesgo"]

    def get_activos_relacionados_resumen(self, obj):
        return [a.id_activo for a in obj.activos_relacionados.all()]

    def get_controles_iso_vinculados_resumen(self, obj):
        return [f"{c.codigo} — {c.nombre}" for c in obj.controles_iso_vinculados.all()]


class AccionTratamientoSerializer(serializers.ModelSerializer):
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    fase_display = serializers.CharField(source="get_fase_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    opcion_tratamiento_display = serializers.CharField(source="get_opcion_tratamiento_display", read_only=True)
    origen_vulnerabilidad_nombre = serializers.CharField(source="origen_vulnerabilidad.nombre_vulnerabilidad", read_only=True, default=None)
    origen_riesgo_activo_id = serializers.CharField(source="origen_riesgo_activo.id_riesgo", read_only=True, default=None)
    origen_riesgo_contextual_id = serializers.CharField(source="origen_riesgo_contextual.id_riesgo_contextual", read_only=True, default=None)
    controles_iso_vinculados_resumen = serializers.SerializerMethodField()
    dias_para_vencer = serializers.IntegerField(read_only=True)
    esta_vencida = serializers.BooleanField(read_only=True)
    por_vencer = serializers.BooleanField(read_only=True)

    class Meta:
        model = AccionTratamiento
        fields = "__all__"
        read_only_fields = ["score", "nivel_riesgo"]

    def get_controles_iso_vinculados_resumen(self, obj):
        return [f"{c.codigo} — {c.nombre}" for c in obj.controles_iso_vinculados.all()]


class PlanTratamientoRiesgosListSerializer(serializers.ModelSerializer):
    campana_red_team_nombre = serializers.CharField(source="campana_red_team.nombre", read_only=True)
    porcentaje_avance_global = serializers.IntegerField(read_only=True)
    total_acciones = serializers.SerializerMethodField()

    class Meta:
        model = PlanTratamientoRiesgos
        fields = [
            "id", "referencia", "titulo", "campana_red_team", "campana_red_team_nombre",
            "clasificacion_documento", "fecha_emision", "porcentaje_avance_global", "total_acciones",
        ]

    def get_total_acciones(self, obj):
        return obj.acciones.count()


class PlanTratamientoRiesgosDetailSerializer(serializers.ModelSerializer):
    acciones = AccionTratamientoSerializer(many=True, read_only=True)
    campana_red_team = CampanaRedTeamSerializer(read_only=True)
    campana_red_team_id = serializers.PrimaryKeyRelatedField(
        source="campana_red_team", queryset=CampanaRedTeam.objects.all(), write_only=True)
    porcentaje_avance_global = serializers.IntegerField(read_only=True)

    class Meta:
        model = PlanTratamientoRiesgos
        fields = "__all__"

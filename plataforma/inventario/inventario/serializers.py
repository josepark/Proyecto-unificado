from rest_framework import serializers
from .models import (Activo, ActivoInfraestructura, SistemaInformacion,
                     EquipoComputo, Zona, VLAN, AmenazaMITRE, ControlISO,
                     RolMCA, AccesoRol)


class AmenazaMITRESerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = AmenazaMITRE
        fields = ("id", "codigo", "nombre", "descripcion", "tipo", "tipo_display",
                  "tacticas", "plataformas", "codigo_padre", "url", "version")


class ControlISOSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlISO
        fields = "__all__"


class InfraestructuraSerializer(serializers.ModelSerializer):
    zona = serializers.StringRelatedField()
    vlan = serializers.StringRelatedField()

    class Meta:
        model = ActivoInfraestructura
        exclude = ("activo",)


class EquipoSerializer(serializers.ModelSerializer):
    tipo_equipo_display = serializers.CharField(source="get_tipo_equipo_display", read_only=True)

    class Meta:
        model = EquipoComputo
        exclude = ("activo",)


class AccesoRolSerializer(serializers.ModelSerializer):
    rol = serializers.StringRelatedField()

    class Meta:
        model = AccesoRol
        fields = ("rol", "nivel")


class SistemaSerializer(serializers.ModelSerializer):
    accesos = serializers.SerializerMethodField()
    accesos_rbac = serializers.SerializerMethodField()

    class Meta:
        model = SistemaInformacion
        exclude = ("activo", "roles")

    def get_accesos(self, obj):
        return AccesoRolSerializer(
            AccesoRol.objects.filter(sistema=obj), many=True).data

    def get_accesos_rbac(self, obj):
        """Despliegue integrado: accesos reales según la Matriz RBAC
        (fuente canónica, SUIIN-SGSI-MCA-001), cruzados en vivo por nombre
        contra `sistema_mca_equivalente`. None si no hay ese campo
        capturado, si RBAC no respondió, o si el nombre no coincide con
        ningún sistema de la matriz — ver integracion_rbac.py."""
        from .integracion_rbac import accesos_rbac_por_sistema
        return accesos_rbac_por_sistema(obj.sistema_mca_equivalente)


class ActivoListSerializer(serializers.ModelSerializer):
    clase_display = serializers.CharField(source="get_clase_display", read_only=True)
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Activo
        fields = ("id", "id_activo", "nombre", "clase", "clase_display",
                  "clasificacion_si", "confidencialidad", "integridad",
                  "disponibilidad", "valor", "nivel_riesgo",
                  "nivel_riesgo_display", "estado", "estado_display",
                  "propietario", "procesa_datos_personales")


class ActivoDetailSerializer(serializers.ModelSerializer):
    clase_display = serializers.CharField(source="get_clase_display", read_only=True)
    clasificacion_si_display = serializers.CharField(
        source="get_clasificacion_si_display", read_only=True)
    nivel_riesgo_display = serializers.CharField(
        source="get_nivel_riesgo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    ciclo_vida_display = serializers.CharField(
        source="get_ciclo_vida_display", read_only=True)
    amenazas = AmenazaMITRESerializer(many=True, read_only=True)
    controles = ControlISOSerializer(many=True, read_only=True)
    infraestructura = InfraestructuraSerializer(read_only=True)
    sistema = SistemaSerializer(read_only=True)
    equipo = EquipoSerializer(read_only=True)
    dependencias = serializers.SerializerMethodField()
    datacenter_info = serializers.SerializerMethodField()

    class Meta:
        model = Activo
        fields = "__all__"

    def get_dependencias(self, obj):
        return [{"id": d.id, "id_activo": d.id_activo, "nombre": d.nombre}
                for d in obj.dependencias.all()]

    def get_datacenter_info(self, obj):
        if not obj.datacenter:
            return None
        dc = obj.datacenter
        return {"id": dc.id, "codigo": dc.codigo, "nombre": dc.nombre,
                "ciudad": dc.ciudad, "tier": dc.get_nivel_tier_display()}


# ---------------------------------------------------------------------------
# Serializadores de ESCRITURA (CRUD)
# ---------------------------------------------------------------------------
class InfraestructuraWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInfraestructura
        exclude = ("activo",)


class EquipoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoComputo
        exclude = ("activo",)


class SistemaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SistemaInformacion
        exclude = ("activo", "roles")


class ActivoWriteSerializer(serializers.ModelSerializer):
    """
    Permite crear/editar un activo junto con su detalle 1:1 (infra o sistema),
    y asociar amenazas/controles por codigo (get_or_create).
    Si no se envia id_activo al crear, se genera automaticamente (RED-0NN / SIS-0NN).
    """
    id_activo = serializers.CharField(required=False, allow_blank=True)
    infraestructura = InfraestructuraWriteSerializer(required=False)
    sistema = SistemaWriteSerializer(required=False)
    equipo = EquipoWriteSerializer(required=False)
    amenazas_codigos = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True)
    controles_codigos = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True)
    dependencias_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Activo
        fields = ("id", "id_activo", "nombre", "descripcion", "clase",
                  "clasificacion_si", "confidencialidad", "integridad",
                  "disponibilidad", "nivel_riesgo", "estado", "fecha_registro",
                  "notas_seguridad", "propietario", "custodio", "area_responsable",
                  "procesa_datos_personales", "rto", "rpo", "ciclo_vida",
                  "documentos_relacionados", "datacenter", "infraestructura",
                  "sistema", "equipo", "amenazas_codigos", "controles_codigos", "dependencias_ids")

    def _sync_m2m(self, activo, validated):
        if "amenazas_codigos" in validated:
            objs = []
            for c in validated.pop("amenazas_codigos"):
                o, _ = AmenazaMITRE.objects.get_or_create(codigo=c.strip())
                objs.append(o)
            activo.amenazas.set(objs)
        if "controles_codigos" in validated:
            objs = []
            for c in validated.pop("controles_codigos"):
                o, _ = ControlISO.objects.get_or_create(codigo=c.strip())
                objs.append(o)
            activo.controles.set(objs)
        if "dependencias_ids" in validated:
            ids = validated.pop("dependencias_ids")
            activo.dependencias.set(Activo.objects.filter(id__in=ids))

    def create(self, validated):
        infra = validated.pop("infraestructura", None)
        sist = validated.pop("sistema", None)
        equipo = validated.pop("equipo", None)
        # extraer m2m antes de crear
        m2m = {k: validated.pop(k) for k in
               ["amenazas_codigos", "controles_codigos", "dependencias_ids"]
               if k in validated}
        activo = Activo.objects.create(**validated)
        if infra:
            ActivoInfraestructura.objects.create(activo=activo, **infra)
        if sist:
            SistemaInformacion.objects.create(activo=activo, **sist)
        if equipo:
            EquipoComputo.objects.create(activo=activo, **equipo)
        self._sync_m2m(activo, m2m)
        return activo

    def update(self, instance, validated):
        infra = validated.pop("infraestructura", None)
        sist = validated.pop("sistema", None)
        equipo = validated.pop("equipo", None)
        m2m = {k: validated.pop(k) for k in
               ["amenazas_codigos", "controles_codigos", "dependencias_ids"]
               if k in validated}
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        if infra is not None:
            ActivoInfraestructura.objects.update_or_create(
                activo=instance, defaults=infra)
        if sist is not None:
            SistemaInformacion.objects.update_or_create(
                activo=instance, defaults=sist)
        if equipo is not None:
            EquipoComputo.objects.update_or_create(
                activo=instance, defaults=equipo)
        self._sync_m2m(instance, m2m)
        return instance


class HistorialSerializer(serializers.Serializer):
    """Serializa un registro de bitacora (django-simple-history) para
    cualquiera de los modelos versionados (Activo / Infraestructura / Sistema)."""
    fecha = serializers.DateTimeField(source="history_date")
    modelo = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()
    id_activo = serializers.SerializerMethodField()
    nombre = serializers.SerializerMethodField()
    cambios = serializers.SerializerMethodField()

    TIPO = {"+": "Creacion", "~": "Modificacion", "-": "Eliminacion"}
    MODELO = {"HistoricalActivo": "Activo",
              "HistoricalActivoInfraestructura": "Infraestructura",
              "HistoricalSistemaInformacion": "Sistema",
              "HistoricalEquipoComputo": "Equipo"}

    def get_modelo(self, obj):
        return self.MODELO.get(type(obj).__name__, type(obj).__name__)

    def get_tipo(self, obj):
        return self.TIPO.get(obj.history_type, obj.history_type)

    def get_usuario(self, obj):
        u = obj.history_user
        return u.get_username() if u else "sistema/importacion"

    def _activo_id(self, obj):
        """id numerico del Activo asociado, sin tocar la FK (que puede
        apuntar a un activo ya eliminado)."""
        if hasattr(obj, "id_activo"):
            return getattr(obj, "id_activo")
        # Historicos 1:1: el campo FK 'activo_id' guarda el pk del Activo
        return getattr(obj, "activo_id", None)

    def get_id_activo(self, obj):
        # Para HistoricalActivo el codigo esta en el campo 'id_activo'
        if hasattr(obj, "id_activo"):
            return obj.id_activo
        # Para infra/sistema, buscar el codigo via el pk del Activo
        pk = getattr(obj, "activo_id", None)
        if pk:
            a = Activo.objects.filter(pk=pk).first()
            if a:
                return a.id_activo
            return f"(activo #{pk})"
        return None

    def get_nombre(self, obj):
        if hasattr(obj, "nombre"):
            return obj.nombre
        pk = getattr(obj, "activo_id", None)
        if pk:
            a = Activo.objects.filter(pk=pk).first()
            if a:
                return a.nombre
        return ""

    def get_cambios(self, obj):
        # Diferencia contra el registro anterior
        try:
            prev = obj.prev_record
        except Exception:
            prev = None
        if not prev or obj.history_type != "~":
            return []
        try:
            delta = obj.diff_against(prev)
        except Exception:
            return []
        return [{"campo": c.field, "antes": str(c.old), "despues": str(c.new)}
                for c in delta.changes]


# ---------------------------------------------------------------------------
# v3 - Datacenter, Diagrama, Hoja de vida
# ---------------------------------------------------------------------------
from .models import Datacenter, Diagrama, EventoHojaVida


class DatacenterSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    tier_display = serializers.CharField(source="get_nivel_tier_display", read_only=True)
    num_activos = serializers.SerializerMethodField()

    class Meta:
        model = Datacenter
        fields = "__all__"

    def get_num_activos(self, obj):
        return obj.activos.count()


class DiagramaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    archivo_url = serializers.SerializerMethodField()
    activos_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Activo.objects.all(), source="activos",
        required=False, write_only=True)
    activos_codigos = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Diagrama
        fields = ("id", "titulo", "tipo", "tipo_display", "archivo", "archivo_url",
                  "descripcion", "fecha", "version", "datacenter",
                  "activos_ids", "activos_codigos", "creado")
        extra_kwargs = {"archivo": {"write_only": True}}

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None

    def get_activos_codigos(self, obj):
        return [{"id": a.id, "id_activo": a.id_activo} for a in obj.activos.all()]


class EventoHojaVidaSerializer(serializers.ModelSerializer):
    tipo_evento_display = serializers.CharField(
        source="get_tipo_evento_display", read_only=True)
    documento_url = serializers.SerializerMethodField()
    id_activo = serializers.CharField(source="activo.id_activo", read_only=True)

    class Meta:
        model = EventoHojaVida
        fields = ("id", "activo", "id_activo", "fecha", "tipo_evento",
                  "tipo_evento_display", "titulo", "descripcion", "responsable",
                  "costo", "documento", "documento_url", "registrado_por", "creado")
        extra_kwargs = {"documento": {"write_only": True, "required": False}}

    def get_documento_url(self, obj):
        return obj.documento.url if obj.documento else None

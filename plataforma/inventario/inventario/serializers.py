from rest_framework import serializers
from django.db.models import Q
from .models import (Activo, ActivoInfraestructura, SistemaInformacion,
                     EquipoComputo, ClaseActivo, Zona, VLAN, AmenazaMITRE, ControlISO,
                     Rack, Datacenter)
from .detalle_schema import validar_detalle_extra


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


class ZonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zona
        fields = ("id", "nombre")


class VlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLAN
        fields = ("id", "etiqueta")


class InfraestructuraSerializer(serializers.ModelSerializer):
    zona = serializers.StringRelatedField()
    vlan = serializers.StringRelatedField()
    zona_id = serializers.IntegerField(read_only=True, allow_null=True)
    vlan_id = serializers.IntegerField(read_only=True, allow_null=True)
    rack_codigo = serializers.CharField(source="rack_fk.codigo", read_only=True, default=None)
    rack_datacenter = serializers.CharField(source="rack_fk.datacenter.codigo", read_only=True, default=None)

    class Meta:
        model = ActivoInfraestructura
        exclude = ("activo",)


class EquipoSerializer(serializers.ModelSerializer):
    tipo_equipo_display = serializers.CharField(source="get_tipo_equipo_display", read_only=True)

    class Meta:
        model = EquipoComputo
        exclude = ("activo",)


class SistemaSerializer(serializers.ModelSerializer):
    accesos_rbac = serializers.SerializerMethodField()
    sistema_rbac_nombre = serializers.SerializerMethodField()

    class Meta:
        model = SistemaInformacion
        exclude = ("activo", "roles")

    def get_accesos_rbac(self, obj):
        """Accesos reales según la Matriz RBAC (fuente canónica)."""
        from .integracion_rbac import accesos_rbac_por_sistema
        if not obj.sistema_rbac_id and not (obj.sistema_mca_equivalente or "").strip():
            return None
        return accesos_rbac_por_sistema(
            nombre_sistema=obj.sistema_mca_equivalente,
            sistema_rbac_id=obj.sistema_rbac_id,
        )

    def get_sistema_rbac_nombre(self, obj):
        from .integracion_rbac import sistema_rbac_resumen
        s = sistema_rbac_resumen(
            nombre_sistema=obj.sistema_mca_equivalente,
            sistema_rbac_id=obj.sistema_rbac_id,
        )
        return s.get("nombre") if s else None


class ClaseActivoSerializer(serializers.ModelSerializer):
    modelo_detalle_display = serializers.CharField(
        source="get_modelo_detalle_display", read_only=True)
    num_activos = serializers.SerializerMethodField()

    class Meta:
        model = ClaseActivo
        fields = ("id", "codigo", "nombre", "prefijo_id", "color", "orden",
                  "activo", "modelo_detalle", "modelo_detalle_display",
                  "detalle_schema", "num_activos")

    def get_num_activos(self, obj):
        return Activo.objects.filter(clase=obj.codigo).count()

    def validate_codigo(self, value):
        return value.strip().upper()

    def validate_prefijo_id(self, value):
        return value.strip().upper()

    def validate_detalle_schema(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Debe ser un objeto JSON.")
        if "campos" in value and not isinstance(value.get("campos"), list):
            raise serializers.ValidationError("La clave «campos» debe ser una lista.")
        return value


class ActivoListSerializer(serializers.ModelSerializer):
    clase_display = serializers.SerializerMethodField()
    nivel_riesgo_display = serializers.CharField(source="get_nivel_riesgo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    vinculado_riesgos = serializers.SerializerMethodField()
    riesgos_id = serializers.SerializerMethodField()

    class Meta:
        model = Activo
        fields = ("id", "id_activo", "nombre", "clase", "clase_display",
                  "clasificacion_si", "confidencialidad", "integridad",
                  "disponibilidad", "valor", "nivel_riesgo",
                  "nivel_riesgo_display", "estado", "estado_display",
                  "propietario", "procesa_datos_personales",
                  "vinculado_riesgos", "riesgos_id")

    def get_clase_display(self, obj):
        return obj.nombre_clase()

    def _espejo(self, obj):
        mapa = self.context.get("mapa_riesgos")
        if mapa is None:
            return None
        return mapa.get(obj.pk)

    def get_vinculado_riesgos(self, obj):
        espejo = self._espejo(obj)
        if espejo is None and self.context.get("mapa_riesgos") is None:
            return None
        return bool(espejo)

    def get_riesgos_id(self, obj):
        espejo = self._espejo(obj)
        return espejo.get("id") if espejo else None


class ActivoDetailSerializer(serializers.ModelSerializer):
    clase_display = serializers.SerializerMethodField()
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

    def get_clase_display(self, obj):
        return obj.nombre_clase()

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

    def validate(self, attrs):
        rack_fk = attrs.get("rack_fk")
        activo = self.context.get("activo")
        if rack_fk and activo and activo.datacenter_id:
            if rack_fk.datacenter_id != activo.datacenter_id:
                raise serializers.ValidationError({
                    "rack_fk": f"El rack {rack_fk.codigo} pertenece a "
                               f"{rack_fk.datacenter.codigo}, no al DC del activo.",
                })
        ini = attrs.get("unidad_inicio")
        fin = attrs.get("unidad_fin")
        if ini and fin and fin < ini:
            raise serializers.ValidationError(
                {"unidad_fin": "Debe ser ≥ unidad_inicio."})
        return attrs


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
    detalle_extra = serializers.JSONField(required=False)

    class Meta:
        model = Activo
        fields = ("id", "id_activo", "nombre", "descripcion", "clase",
                  "clasificacion_si", "confidencialidad", "integridad",
                  "disponibilidad", "nivel_riesgo", "estado", "fecha_registro",
                  "notas_seguridad", "propietario", "custodio", "area_responsable",
                  "procesa_datos_personales", "rto", "rpo", "ciclo_vida",
                  "documentos_relacionados", "datacenter", "detalle_extra",
                  "infraestructura", "sistema", "equipo", "amenazas_codigos",
                  "controles_codigos", "dependencias_ids")

    def _catalogo_clase(self, codigo):
        return ClaseActivo.objects.filter(codigo=codigo, activo=True).first()

    def validate_clase(self, value):
        if not self._catalogo_clase(value):
            validas = ", ".join(
                ClaseActivo.objects.filter(activo=True).values_list("codigo", flat=True))
            raise serializers.ValidationError(
                f"Clase «{value}» no válida o inactiva. Use: {validas or 'ninguna definida'}.")
        return value

    def validate(self, attrs):
        clase = attrs.get("clase") or getattr(self.instance, "clase", None)
        cat = self._catalogo_clase(clase)
        if not cat:
            return attrs

        tiene_infra = "infraestructura" in attrs and attrs["infraestructura"] is not None
        tiene_sist = "sistema" in attrs and attrs["sistema"] is not None
        tiene_equipo = "equipo" in attrs and attrs["equipo"] is not None
        detalle = attrs.get("detalle_extra")

        esperado = cat.modelo_detalle
        bloques = {
            "infraestructura": tiene_infra,
            "sistema": tiene_sist,
            "equipo": tiene_equipo,
            "generico": bool(detalle),
            "ninguno": False,
        }
        for otro, presente in bloques.items():
            if otro == esperado or not presente:
                continue
            raise serializers.ValidationError({
                otro: f"La clase {clase} no admite este bloque de detalle "
                      f"(esperado: {esperado}).",
            })

        if esperado == "infraestructura" and self.instance and not tiene_infra:
            pass
        elif esperado in ("infraestructura", "sistema", "equipo") and self.instance is None:
            if not bloques.get(esperado):
                raise serializers.ValidationError(
                    f"La clase {clase} requiere el bloque de detalle «{esperado}».")

        if cat.modelo_detalle == "generico" and "detalle_extra" in attrs:
            normalizado, errores = validar_detalle_extra(
                cat.detalle_schema, attrs.get("detalle_extra"))
            if errores:
                raise serializers.ValidationError({"detalle_extra": errores})
            attrs["detalle_extra"] = normalizado

        return attrs

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
            ser = InfraestructuraWriteSerializer(
                data=infra, context={"activo": activo})
            ser.is_valid(raise_exception=True)
            ActivoInfraestructura.objects.create(activo=activo, **ser.validated_data)
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
            ser = InfraestructuraWriteSerializer(
                data=infra, context={"activo": instance})
            ser.is_valid(raise_exception=True)
            ActivoInfraestructura.objects.update_or_create(
                activo=instance, defaults=ser.validated_data)
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
# v3 - Datacenter, Rack, Diagrama, Hoja de vida
# ---------------------------------------------------------------------------
from .models import Datacenter, Diagrama, EventoHojaVida


class RackSerializer(serializers.ModelSerializer):
    datacenter_codigo = serializers.CharField(source="datacenter.codigo", read_only=True)
    ocupacion_u = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rack
        fields = ("id", "datacenter", "datacenter_codigo", "codigo",
                  "capacidad_u", "ubicacion", "ocupacion_u")

    def validate_codigo(self, value):
        return value.strip().upper()


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


# ---------------------------------------------------------------------------
# Cuentas de plataforma (auth.User + PerfilPlataforma)
# ---------------------------------------------------------------------------
from django.contrib.auth.models import User
from .models import PerfilPlataforma
from .permisos import ROL_CONSULTOR, ROL_DINAMIZADOR, ROL_ADMIN, roles_de
from .modulos_plataforma import MODULOS_PLATAFORMA, normalizar_modulos

ROLES_PLATAFORMA = (ROL_CONSULTOR, ROL_DINAMIZADOR, ROL_ADMIN)


class UsuarioPlataformaSerializer(serializers.ModelSerializer):
    rol = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    modulos_acceso = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "nombre_completo", "rol", "area", "modulos_acceso", "is_active",
            "last_login", "date_joined", "is_superuser",
        )
        read_only_fields = fields

    def get_modulos_acceso(self, obj):
        perfil = getattr(obj, "perfil_plataforma", None)
        if perfil:
            return normalizar_modulos(perfil.modulos_acceso or [])
        return []

    def get_rol(self, obj):
        rs = roles_de(obj) & set(ROLES_PLATAFORMA)
        if ROL_ADMIN in rs:
            return ROL_ADMIN
        if ROL_DINAMIZADOR in rs:
            return ROL_DINAMIZADOR
        if ROL_CONSULTOR in rs:
            return ROL_CONSULTOR
        return None

    def get_area(self, obj):
        perfil = getattr(obj, "perfil_plataforma", None)
        return perfil.area if perfil else ""

    def get_nombre_completo(self, obj):
        nombre = obj.get_full_name().strip()
        return nombre or obj.username


class UsuarioPlataformaWriteSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    rol = serializers.ChoiceField(choices=ROLES_PLATAFORMA)
    area = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    modulos_acceso = serializers.ListField(
        child=serializers.ChoiceField(choices=MODULOS_PLATAFORMA),
        required=False,
        allow_empty=True,
    )
    is_active = serializers.BooleanField(default=True)

    def validate_username(self, value):
        qs = User.objects.filter(username__iexact=value)
        instance = self.context.get("instance")
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return value

    def validate(self, attrs):
        view = self.context.get("view")
        instance = self.context.get("instance")
        creando = instance is None
        password = (attrs.get("password") or "").strip()

        if creando and not password:
            raise serializers.ValidationError({"password": "La contraseña es obligatoria al crear."})
        if creando and not attrs.get("rol"):
            raise serializers.ValidationError({"rol": "Seleccione un rol."})
        if password and len(password) < 8:
            raise serializers.ValidationError({"password": "Mínimo 8 caracteres."})

        actor = view.request.user if view else None
        if instance and actor and instance.pk == actor.pk:
            nuevo_rol = attrs.get("rol")
            if nuevo_rol and nuevo_rol != ROL_ADMIN:
                raise serializers.ValidationError(
                    {"rol": "No puede quitarse el rol Administrador a sí mismo."}
                )
            if attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "No puede desactivar su propia cuenta."}
                )

        if instance and attrs.get("rol") is not None and attrs["rol"] != ROL_ADMIN:
            if _es_ultimo_admin(instance):
                raise serializers.ValidationError(
                    {"rol": "No puede retirar el último Administrador de la plataforma."}
                )
        if instance and attrs.get("is_active") is False and _es_ultimo_admin(instance):
            raise serializers.ValidationError(
                {"is_active": "No puede desactivar al último Administrador."}
            )

        modulos = attrs.get("modulos_acceso")
        rol_efectivo = attrs.get("rol") or (
            UsuarioPlataformaSerializer().get_rol(instance) if instance else None
        )
        if creando and rol_efectivo != ROL_ADMIN:
            lista = normalizar_modulos(modulos or [])
            if not lista:
                raise serializers.ValidationError(
                    {"modulos_acceso": "Seleccione al menos un proyecto."}
                )
            attrs["modulos_acceso"] = lista
        elif modulos is not None:
            attrs["modulos_acceso"] = normalizar_modulos(modulos)
            if rol_efectivo != ROL_ADMIN and not attrs["modulos_acceso"]:
                raise serializers.ValidationError(
                    {"modulos_acceso": "Seleccione al menos un proyecto."}
                )

        return attrs


def _es_ultimo_admin(user):
    from .permisos import user_es_admin
    if not user_es_admin(user):
        return False
    admins = User.objects.filter(
        Q(is_superuser=True) | Q(groups__name=ROL_ADMIN),
        is_active=True,
    ).distinct()
    return admins.count() <= 1


def _grupo_por_rol(rol):
    from django.contrib.auth.models import Group
    return Group.objects.get(name=rol)


def _guardar_perfil(user, area=None, modulos_acceso=None):
    perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    campos = []
    if area is not None:
        perfil.area = area or ""
        campos.append("area")
    if modulos_acceso is not None:
        perfil.modulos_acceso = normalizar_modulos(modulos_acceso)
        campos.append("modulos_acceso")
    if campos:
        perfil.save(update_fields=campos)


def crear_usuario_plataforma(validated_data):
    from django.contrib.auth.models import User
    password = validated_data.pop("password")
    rol = validated_data.pop("rol")
    area = validated_data.pop("area", "")
    modulos = validated_data.pop("modulos_acceso", None)
    is_active = validated_data.pop("is_active", True)
    username = validated_data.pop("username")
    user = User.objects.create_user(
        username=username,
        password=password,
        email=validated_data.get("email", ""),
        first_name=validated_data.get("first_name", ""),
        last_name=validated_data.get("last_name", ""),
        is_active=is_active,
    )
    user.groups.set([_grupo_por_rol(rol)])
    if rol == ROL_ADMIN:
        modulos_guardar = list(MODULOS_PLATAFORMA)
    else:
        modulos_guardar = modulos or []
    _guardar_perfil(user, area=area, modulos_acceso=modulos_guardar)
    return user


def actualizar_usuario_plataforma(instance, validated_data):
    password = validated_data.pop("password", None)
    rol = validated_data.pop("rol", None)
    area = validated_data.pop("area", None)
    modulos = validated_data.pop("modulos_acceso", None)
    for campo in ("email", "first_name", "last_name", "is_active"):
        if campo in validated_data:
            setattr(instance, campo, validated_data[campo])
    if password:
        instance.set_password(password)
    instance.save()
    if rol is not None:
        instance.groups.set([_grupo_por_rol(rol)])
    if area is not None or modulos is not None:
        _guardar_perfil(instance, area=area, modulos_acceso=modulos)
    return instance


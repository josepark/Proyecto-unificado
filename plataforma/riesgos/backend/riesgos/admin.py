from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    Activo, PuertoServicio, Vulnerabilidad, RiesgoActivo, RiesgoContextual,
    CampanaRedTeam, PlanTratamientoRiesgos, AccionTratamiento, ControlISO27001,
    Evidencia,
)


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre_original", "content_type", "object_id", "tipo_archivo", "subido_por", "creado_en")
    list_filter = ("tipo_archivo", "content_type")
    search_fields = ("nombre_original", "descripcion")
    readonly_fields = ("tipo_archivo", "tamano_bytes")


@admin.register(ControlISO27001)
class ControlISO27001Admin(SimpleHistoryAdmin):
    list_display = ("codigo", "nombre", "categoria", "aplicable", "estado_implementacion")
    list_filter = ("categoria", "aplicable", "estado_implementacion")
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)


class PuertoServicioInline(admin.TabularInline):
    model = PuertoServicio
    extra = 0


@admin.register(Activo)
class ActivoAdmin(SimpleHistoryAdmin):
    list_display = ("id_activo", "nombre", "tipo", "riesgo_matriz", "clasificacion_si",
                     "cobertura", "afectado_red_team", "valor")
    list_filter = ("riesgo_matriz", "clasificacion_si", "cobertura", "afectado_red_team", "tipo")
    search_fields = ("id_activo", "nombre", "ip_principal")
    inlines = [PuertoServicioInline]


@admin.register(Vulnerabilidad)
class VulnerabilidadAdmin(SimpleHistoryAdmin):
    list_display = ("id_riesgo", "activo", "nombre_vulnerabilidad", "severidad_ov", "cvss",
                     "nivel_riesgo", "estado")
    list_filter = ("severidad_ov", "nivel_riesgo", "estado", "tratamiento")
    search_fields = ("nombre_vulnerabilidad", "cves", "activo__id_activo", "activo__nombre")
    autocomplete_fields = ["activo"]


@admin.register(RiesgoActivo)
class RiesgoActivoAdmin(SimpleHistoryAdmin):
    list_display = ("id_riesgo", "activo", "score", "nivel_riesgo", "tratamiento", "estado",
                     "responsable_sugerido")
    list_filter = ("nivel_riesgo", "tratamiento", "estado")
    search_fields = ("id_riesgo", "activo__id_activo", "activo__nombre")
    autocomplete_fields = ["activo"]


@admin.register(RiesgoContextual)
class RiesgoContextualAdmin(SimpleHistoryAdmin):
    list_display = ("id_riesgo_contextual", "escenario_amenaza", "score", "nivel_riesgo",
                     "estado_actual")
    list_filter = ("nivel_riesgo", "clasificacion_si", "estado_actual")
    search_fields = ("id_riesgo_contextual", "escenario_amenaza")
    filter_horizontal = ("activos_relacionados", "controles_iso_vinculados")


@admin.register(CampanaRedTeam)
class CampanaRedTeamAdmin(SimpleHistoryAdmin):
    list_display = ("nombre", "host_ip", "fecha_inicio", "fecha_fin", "estado_compromiso",
                     "riesgos_criticos", "riesgos_altos")
    search_fields = ("nombre", "host_ip")


class AccionTratamientoInline(admin.TabularInline):
    model = AccionTratamiento
    extra = 0
    fields = ("id_riesgo", "descripcion_riesgo", "fase", "opcion_tratamiento", "estado",
              "porcentaje_avance", "origen_vulnerabilidad", "origen_riesgo_activo", "origen_riesgo_contextual")
    autocomplete_fields = ["origen_vulnerabilidad", "origen_riesgo_activo", "origen_riesgo_contextual"]


@admin.register(PlanTratamientoRiesgos)
class PlanTratamientoRiesgosAdmin(SimpleHistoryAdmin):
    list_display = ("referencia", "titulo", "campana_red_team", "fecha_emision",
                     "porcentaje_avance_global")
    search_fields = ("referencia", "titulo")
    inlines = [AccionTratamientoInline]


@admin.register(AccionTratamiento)
class AccionTratamientoAdmin(SimpleHistoryAdmin):
    list_display = ("plan", "id_riesgo", "score", "nivel_riesgo", "fase", "estado",
                     "porcentaje_avance", "responsable", "origen_vulnerabilidad", "origen_riesgo_activo",
                     "origen_riesgo_contextual")
    list_filter = ("fase", "estado", "nivel_riesgo", "opcion_tratamiento")
    search_fields = ("id_riesgo", "descripcion_riesgo", "plan__referencia")
    autocomplete_fields = ["plan", "origen_vulnerabilidad", "origen_riesgo_activo", "origen_riesgo_contextual"]
    filter_horizontal = ("controles_iso_vinculados",)

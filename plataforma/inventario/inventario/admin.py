from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import (Activo, ActivoInfraestructura, SistemaInformacion,
                     EquipoComputo, Zona, VLAN, AmenazaMITRE, ControlISO,
                     RolMCA, AccesoRol)


class InfraInline(admin.StackedInline):
    model = ActivoInfraestructura
    extra = 0


class AccesoRolInline(admin.TabularInline):
    model = AccesoRol
    extra = 1


class SistemaInline(admin.StackedInline):
    model = SistemaInformacion
    extra = 0


class EquipoInline(admin.StackedInline):
    model = EquipoComputo
    extra = 0


@admin.register(Activo)
class ActivoAdmin(SimpleHistoryAdmin):
    list_display = ("id_activo", "nombre", "clase", "clasificacion_si",
                    "valor", "nivel_riesgo", "estado", "propietario",
                    "procesa_datos_personales")
    list_filter = ("clase", "clasificacion_si", "nivel_riesgo", "estado",
                   "ciclo_vida", "procesa_datos_personales")
    search_fields = ("id_activo", "nombre", "descripcion", "notas_seguridad",
                     "propietario", "custodio")
    filter_horizontal = ("amenazas", "controles", "dependencias")
    inlines = [InfraInline, SistemaInline, EquipoInline]
    history_list_display = ["nivel_riesgo", "estado", "clasificacion_si"]
    fieldsets = (
        ("Identificacion", {"fields": ("id_activo", "nombre", "descripcion", "clase")}),
        ("Valoracion C-I-D", {"fields": ("clasificacion_si", "confidencialidad",
                                          "integridad", "disponibilidad", "valor",
                                          "nivel_riesgo")}),
        ("Gobernanza (ISO 5.9)", {"fields": ("propietario", "custodio",
                                             "area_responsable")}),
        ("Datos personales / Continuidad", {"fields": ("procesa_datos_personales",
                                                       "rto", "rpo")}),
        ("Ciclo de vida y trazabilidad", {"fields": ("ciclo_vida",
                                                     "documentos_relacionados",
                                                     "dependencias")}),
        ("Estado", {"fields": ("estado", "fecha_registro", "notas_seguridad")}),
        ("Amenazas y controles", {"fields": ("amenazas", "controles")}),
    )


@admin.register(SistemaInformacion)
class SistemaAdmin(SimpleHistoryAdmin):
    list_display = ("activo", "estado_operativo", "backend", "frontend",
                    "servidor_virtual", "priorizar_analisis")
    list_filter = ("estado_operativo", "priorizar_analisis")
    inlines = [AccesoRolInline]


@admin.register(ActivoInfraestructura)
class InfraAdmin(SimpleHistoryAdmin):
    list_display = ("activo", "tipo", "modelo", "ip_segmento",
                    "fabricante_proveedor", "fin_soporte_eol", "hallazgos_abiertos")
    search_fields = ("activo__id_activo", "modelo", "ip_segmento")


@admin.register(EquipoComputo)
class EquipoAdmin(SimpleHistoryAdmin):
    list_display = ("activo", "tipo_equipo", "marca", "modelo", "serial",
                    "usuario_asignado", "fin_garantia")
    list_filter = ("tipo_equipo", "cifrado_disco", "unido_a_dominio")
    search_fields = ("activo__id_activo", "marca", "modelo", "serial", "usuario_asignado")


@admin.register(AmenazaMITRE)
class AmenazaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "tacticas")
    list_filter = ("tipo",)
    search_fields = ("codigo", "nombre", "descripcion", "tacticas")


@admin.register(ControlISO)
class ControlAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descripcion")
    search_fields = ("codigo", "descripcion")


admin.site.register([Zona, VLAN, RolMCA])
admin.site.site_header = "SUIIN - Inventario de Activos SGSI (SUIIN-SGSI-INV-001)"
admin.site.site_title = "Inventario SGSI SUIIN"
admin.site.index_title = "Gestion del inventario de activos"


# --- v3: Datacenter, Diagrama, Hoja de vida ---
from .models import Datacenter, Diagrama, EventoHojaVida


class DiagramaInline(admin.TabularInline):
    model = Diagrama
    extra = 0
    fields = ("titulo", "tipo", "archivo", "version")


class HojaVidaInline(admin.TabularInline):
    model = EventoHojaVida
    extra = 0
    fields = ("fecha", "tipo_evento", "titulo", "responsable", "costo", "documento")
    ordering = ("-fecha",)


@admin.register(Datacenter)
class DatacenterAdmin(SimpleHistoryAdmin):
    list_display = ("codigo", "nombre", "tipo", "nivel_tier", "ciudad", "responsable")
    list_filter = ("tipo", "nivel_tier", "ciudad")
    search_fields = ("codigo", "nombre", "ciudad")
    inlines = [DiagramaInline]


@admin.register(Diagrama)
class DiagramaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "datacenter", "version", "fecha")
    list_filter = ("tipo", "datacenter")
    search_fields = ("titulo", "descripcion")
    filter_horizontal = ("activos",)


@admin.register(EventoHojaVida)
class HojaVidaAdmin(admin.ModelAdmin):
    list_display = ("activo", "fecha", "tipo_evento", "titulo", "responsable", "costo")
    list_filter = ("tipo_evento", "fecha")
    search_fields = ("activo__id_activo", "titulo", "descripcion", "responsable")
    date_hierarchy = "fecha"


# Enlazar hoja de vida como inline del activo
ActivoAdmin.inlines = ActivoAdmin.inlines + [HojaVidaInline]

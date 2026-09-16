from django.contrib import admin

from rbac.models import (
    AttackTecnica,
    CategoriaSistema,
    GrupoRol,
    LogAuditoria,
    NivelAcceso,
    Rol,
    Sistema,
    Usuario,
)


@admin.register(GrupoRol)
class GrupoRolAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('codigo', 'nombre')


@admin.register(NivelAcceso)
class NivelAccesoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'orden')
    ordering = ('orden',)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'abreviatura', 'denominacion', 'grupo', 'activo')
    list_filter = ('grupo', 'activo', 'riesgo_attack')
    search_fields = ('codigo', 'abreviatura', 'denominacion')


@admin.register(CategoriaSistema)
class CategoriaSistemaAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)


@admin.register(Sistema)
class SistemaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'clasificacion', 'activo', 'espacio_codigo')
    list_filter = ('categoria', 'clasificacion', 'activo')
    search_fields = ('nombre',)


@admin.register(AttackTecnica)
class AttackTecnicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'tactica', 'es_subtecnica')
    search_fields = ('id', 'nombre')


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rol', 'estado', 'mfa_activo', 'espacio_codigo')
    list_filter = ('estado', 'rol')
    search_fields = ('nombre',)


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'entidad', 'accion', 'responsable')
    list_filter = ('entidad', 'accion')
    search_fields = ('detalle',)

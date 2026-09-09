from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views
from . import views

router = DefaultRouter()
router.register(r"clases-activo", views.ClaseActivoViewSet)
router.register(r"activos", views.ActivoViewSet)
router.register(r"amenazas", views.AmenazaViewSet)
router.register(r"controles", views.ControlViewSet)
router.register(r"datacenters", views.DatacenterViewSet)
router.register(r"racks", views.RackViewSet)
router.register(r"diagramas", views.DiagramaViewSet)
router.register(r"hojavida", views.HojaVidaViewSet)

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("api/bitacora/", views.bitacora_global, name="bitacora"),
    path("api/auth/login/", views.api_login, name="api_login"),
    path("api/sesion/", views.sesion_info_v2, name="sesion"),
    path("api/auth-rbac/", views.auth_check_rbac, name="auth_check_rbac"),
    path("api/token-jwt/", views.token_jwt, name="token_jwt"),
    path("api/alertas/", views.alertas, name="alertas"),
    path("api/riesgos/", views.riesgos, name="riesgos"),
    path("api/riesgos/recalcular/", views.recalcular_riesgos, name="recalcular_riesgos"),
    path("api/cobertura/", views.cobertura_controles, name="cobertura"),
    path("api/dashboard-ejecutivo/", views.dashboard_ejecutivo, name="dashboard_ejecutivo"),
    path("api/reporte-consolidado.pdf", views.reporte_consolidado_pdf, name="reporte_consolidado"),
    path("api/catalogo/sistemas-rbac/", views.catalogo_sistemas_rbac_view, name="catalogo_sistemas_rbac"),
    path("api/accesos/unificado/", views.accesos_unificado, name="accesos_unificado"),
    path("api/auth/jwt-version/<str:username>/", views.jwt_version_usuario, name="jwt_version"),
    path("api/integridad/", views.integridad_lista, name="integridad"),
    path("api/integridad/verificar/", views.integridad_verificar, name="integridad_verificar"),
    path("api/exportar/inventario.xlsx", views.exportar_inventario_xlsx, name="exp_inv"),
    path("api/activos/importar/plantilla.xlsx", views.importar_plantilla_xlsx, name="importar_plantilla"),
    path("api/activos/importar/analizar/", views.importar_activos_analizar, name="importar_analizar"),
    path("api/activos/importar/confirmar/", views.importar_activos_confirmar, name="importar_confirmar"),
    path("api/activos/<int:pk>/hojavida.pdf", views.exportar_hojavida_pdf, name="exp_hv"),
    path("api/activos/<int:pk>/qr.png", views.qr_activo, name="qr"),
    path("api/activos/<int:pk>/etiqueta.pdf", views.etiqueta_activo, name="etiqueta"),
    path("api/etiquetas/lote.pdf", views.etiquetas_lote, name="etiquetas_lote"),
    path("api/", include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"activos", views.ActivoViewSet, basename="activo")
router.register(r"puertos", views.PuertoServicioViewSet, basename="puerto")
router.register(r"vulnerabilidades", views.VulnerabilidadViewSet, basename="vulnerabilidad")
router.register(r"riesgos-activo", views.RiesgoActivoViewSet, basename="riesgoactivo")
router.register(r"riesgos-contextuales", views.RiesgoContextualViewSet, basename="riesgocontextual")
router.register(r"campanas-red-team", views.CampanaRedTeamViewSet, basename="campanaredteam")
router.register(r"planes-tratamiento", views.PlanTratamientoRiesgosViewSet, basename="plantratamiento")
router.register(r"acciones-tratamiento", views.AccionTratamientoViewSet, basename="acciontratamiento")
router.register(r"controles-iso27001", views.ControlISO27001ViewSet, basename="controliso27001")
router.register(r"evidencias", views.EvidenciaViewSet, basename="evidencia")
router.register(r"catalogo", views.CatalogoValorViewSet, basename="catalogovalor")
router.register(r"tecnicas-mitre", views.TecnicaMitreViewSet, basename="tecnicamitre")

urlpatterns = [
    path("dashboard/resumen/", views.dashboard_resumen, name="dashboard-resumen"),
    path("cumplimiento/resumen/", views.cumplimiento_resumen, name="cumplimiento-resumen"),
    path("alertas/resumen/", views.alertas_resumen, name="alertas-resumen"),
    path("importar/excel/", views.importar_excel, name="importar-excel"),
    path("auth/login/", views.auth_login, name="auth-login"),
    path("auth/logout/", views.auth_logout, name="auth-logout"),
    path("auth/me/", views.auth_me, name="auth-me"),
    path("", include(router.urls)),
]

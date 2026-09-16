from django.urls import path

from rbac import views_api

urlpatterns = [
    path('csrf', views_api.CsrfView.as_view()),
    path('catalogos', views_api.CatalogosView.as_view()),
    path('inicio', views_api.InicioView.as_view()),
    path('resumen', views_api.ResumenView.as_view()),
    path('roles', views_api.RolesListView.as_view()),
    path('roles/<int:rid>', views_api.RolDetailView.as_view()),
    path('sistemas', views_api.SistemasListView.as_view()),
    path('sistemas/<int:sid>', views_api.SistemaDetailView.as_view()),
    path('usuarios', views_api.UsuariosListView.as_view()),
    path('usuarios/<int:uid>', views_api.UsuarioDetailView.as_view()),
    path('matriz', views_api.MatrizView.as_view()),
    path('matriz/heatmap', views_api.MatrizHeatmapView.as_view()),
    path('matriz/comparar', views_api.MatrizCompararView.as_view()),
    path('excepciones', views_api.ExcepcionesListView.as_view()),
    path('auditoria', views_api.AuditoriaListView.as_view()),
    path('auditoria/verificar', views_api.AuditoriaVerificarView.as_view()),
    path('export/matriz.csv', views_api.ExportMatrizCsvView.as_view()),
    path('export/accesos_usuarios.csv', views_api.ExportAccesosCsvView.as_view()),
]

"""
URL configuration for suiin_riesgos_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('riesgos.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    # En producción, sirva MEDIA_ROOT desde Nginx/S3 — Django nunca debe servir
    # archivos subidos por usuarios en un despliegue real (ver README).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "SUIIN-SGSI · Gestión de Riesgos"
admin.site.site_title = "SUIIN-SGSI-RIESGOS"
admin.site.index_title = "Consejo Regional Indígena del Cauca (CRIC) — UAIIN / SUIIN"

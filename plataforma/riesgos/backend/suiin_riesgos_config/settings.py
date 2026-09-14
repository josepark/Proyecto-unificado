"""
SUIIN-SGSI-RIESGOS · Configuración Django
Sistema de Gestión de Riesgos de Seguridad de la Información — CRIC / UAIIN / SUIIN

Basado en 'django-admin startproject' (Django 6.0).
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables desde .env si existe (ver .env.example). No falla si el paquete
# no está instalado o el archivo no existe — solo es una comodidad de desarrollo.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# SECURITY WARNING: keep the secret key used in production secret!
# En producción, defínala en el archivo .env (ver .env.example) — NUNCA la deje hardcodeada.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-l(y5b6tjpk+!$j_ee(8g4_cc1k@iz#d!abkff_(di(yir42r4z",  # solo desarrollo
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'simple_history',
    'axes',
    # SUIIN
    'riesgos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',  # SIEMPRE al final (requisito de django-axes)
]

# Endurecimiento del login propio de riesgos (el que usa /auth/login/, distinto de
# la sesión única por JWT — ver riesgos/auth_jwt.py): bloqueo tras intentos
# fallidos, por combinación de usuario + IP, igual que ya protege /login/ del
# Inventario (ver README-DESPLIEGUE.md de la plataforma). Antes de esto, el login
# propio de riesgos no tenía ningún freno contra fuerza bruta.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
# Lista ANIDADA (una sola lista adentro) — significa "bloquear por la
# COMBINACIÓN usuario+IP juntos", que es la semántica que se buscaba. La forma
# plana ['username', 'ip_address'] (sin anidar) significa otra cosa muy
# distinta en django-axes: "bloquear por usuario O por IP, cada uno aparte" —
# con esa forma, una IP compartida (oficina, NAT) puede terminar bloqueada
# para todo el mundo aunque los intentos fallidos hayan sido de cuentas
# distintas. Verificado en el código fuente de axes (axes/conf.py) y
# reproducido en vivo: con la forma plana, un segundo usuario válido desde la
# misma IP del que sí se equivocó también quedaba bloqueado.
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_COOLOFF_TIME = 1  # horas
AXES_RESET_ON_SUCCESS = True

# CORS — la SPA de React corre en un origen distinto (Vite dev server) durante desarrollo.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# Correo — usado por el comando `enviar_alertas_vencimiento`. Por defecto imprime
# los correos a la consola (nada que configurar en desarrollo). Para producción,
# defina DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend y las
# variables DJANGO_EMAIL_HOST / DJANGO_EMAIL_PORT / DJANGO_EMAIL_HOST_USER /
# DJANGO_EMAIL_HOST_PASSWORD / DJANGO_EMAIL_USE_TLS.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "suiin-sgsi@cric.org.co")
# Lista separada por comas de quienes reciben el resumen de vencimientos.
ALERTAS_EMAIL_DESTINATARIOS = [
    correo.strip() for correo in os.environ.get("ALERTAS_EMAIL_DESTINATARIOS", "").split(",")
    if correo.strip()
]

# Plataforma SUIIN (Inventario) — fuente canónica del catálogo de activos.
# Dentro de la red de docker-compose de la plataforma unificada, el nombre del
# servicio resuelve por DNS interno (ver README §"Unificación con la Plataforma
# SUIIN"); en desarrollo local, apunta al runserver del inventario.
INVENTARIO_API_URL = os.environ.get("INVENTARIO_API_URL", "http://localhost:8000/api")

# Plataforma unificada: activos canónicos en Inventario — bloquea POST /api/activos/ aquí.
PLATAFORMA_ACTIVOS_SOLO_INVENTARIO = os.environ.get(
    "PLATAFORMA_ACTIVOS_SOLO_INVENTARIO", "").lower() in ("1", "true", "yes")

# Sesión única de plataforma: el Inventario emite un JWT firmado (ver
# inventario/jwt_plataforma.py); riesgos lo verifica aquí SIN llamar de vuelta
# al inventario en cada petición — solo valida la firma con este mismo
# secreto compartido. JWT_SHARED_SECRET debe ser IDÉNTICO en ambos servicios
# (a diferencia de DJANGO_SECRET_KEY, que sí debe ser distinto por app — ver
# README-DESPLIEGUE.md de la plataforma, sección 11).
# Sin configurar, la verificación de JWT queda deshabilitada y el login por
# token propio de riesgos (TokenAuthentication) sigue funcionando igual que
# siempre — así el módulo también puede correr de forma independiente.
JWT_SHARED_SECRET = os.environ.get("JWT_SHARED_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = os.environ.get("JWT_ISSUER", "suiin-inventario")

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'riesgos.pagination.StandardPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'riesgos.auth_jwt.JWTPlataformaAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'riesgos.auth_jwt.EscrituraSegunRolDePlataforma',
    ],
    # El frontend real manda JSON (Axios), no multipart/form-data. DRF trata "" en
    # form-data como None automáticamente para campos allow_null (semántica de
    # formularios HTML) pero NO hace esa conversión en JSON — así que las pruebas
    # deben usar JSON por defecto o esconderían justo el tipo de bug que existen
    # para atrapar (ver test_api_crud.py::TestCamposVaciosSaneados).
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

ROOT_URLCONF = 'suiin_riesgos_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'suiin_riesgos_config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# Por defecto usa SQLite (cero configuración). Para integrarlo al stack SUIIN Platform
# (docker-compose con PostgreSQL), defina DJANGO_DB_ENGINE=postgresql y las variables
# DJANGO_DB_NAME / DJANGO_DB_USER / DJANGO_DB_PASSWORD / DJANGO_DB_HOST / DJANGO_DB_PORT.
if os.environ.get("DJANGO_DB_ENGINE") == "postgresql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get("DJANGO_DB_NAME", "suiin_riesgos"),
            'USER': os.environ.get("DJANGO_DB_USER", "suiin"),
            'PASSWORD': os.environ.get("DJANGO_DB_PASSWORD", ""),
            'HOST': os.environ.get("DJANGO_DB_HOST", "localhost"),
            'PORT': os.environ.get("DJANGO_DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                # Mismo motivo y mismo ajuste que en el Inventario (ver
                # config/settings.py allá) — riesgos corre con el mismo
                # patrón (gunicorn --workers 3 + SQLite), expuesto al mismo
                # riesgo de "database is locked" bajo ráfagas concurrentes.
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;',
                'timeout': 20,
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Adjuntos de evidencia (Evidencia). En producción sirva MEDIA_ROOT desde Nginx/S3
# en vez del servidor de desarrollo de Django — ver README §"Adjuntos de evidencia".
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Django rechaza uploads más grandes que esto ANTES de que el validador de tamaño
# del modelo (10 MB, ver riesgos/models.py) llegue a ejecutarse — debe ser mayor
# que ese límite, con margen para el resto del payload multipart.
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

# ---------------------------------------------------------------------------
# Guardia contra secretos sin configurar — se niega a arrancar en vez de
# correr insegura en silencio. Mismo mecanismo que en inventario/config/
# settings.py (hallazgo real de un despliegue que corrió con DEBUG=False y
# los valores de ejemplo de .env.example sin reemplazar — ver ese archivo
# para el detalle completo del razonamiento).
def _validar_secretos_configurados():
    marcadores_de_ejemplo = ("defina-", "django-insecure-")
    a_revisar = {"DJANGO_SECRET_KEY (RIESGOS_SECRET_KEY)": SECRET_KEY, "JWT_SHARED_SECRET": JWT_SHARED_SECRET}
    con_placeholder = [
        nombre for nombre, valor in a_revisar.items()
        if valor and any(valor.startswith(m) for m in marcadores_de_ejemplo)
    ]
    if con_placeholder and not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "No se puede arrancar con DJANGO_DEBUG=False mientras estas variables sigan con "
            f"el valor de ejemplo de .env.example: {', '.join(con_placeholder)}. "
            "Genere un valor real y aleatorio para cada una (ej. "
            "`python3 -c \"import secrets; print(secrets.token_urlsafe(50))\"`) y actualice su "
            "archivo .env — ver README-DESPLIEGUE.md."
        )
    if con_placeholder and DEBUG:
        import warnings
        warnings.warn(
            f"⚠ Usando valores de ejemplo de .env.example para: {', '.join(con_placeholder)}. "
            "Esto es aceptable en desarrollo (DEBUG=True) pero NO debe llegar a producción.",
            stacklevel=2,
        )


_validar_secretos_configurados()

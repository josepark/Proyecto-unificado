from django.apps import AppConfig


class RiesgosConfig(AppConfig):
    name = 'riesgos'
    verbose_name = 'Gestión de Riesgos SUIIN'

    def ready(self):
        from . import signals  # noqa: F401

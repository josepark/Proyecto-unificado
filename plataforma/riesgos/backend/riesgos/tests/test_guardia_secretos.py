import warnings

import pytest
from django.core.exceptions import ImproperlyConfigured

from suiin_riesgos_config import settings as s


class TestGuardiaSecretosConfigurados:
    """
    Cubre `_validar_secretos_configurados()` — hallazgo real de un despliegue
    que corrió con DJANGO_DEBUG=False y los valores de ejemplo de .env.example
    sin reemplazar (DJANGO_SECRET_KEY, JWT_SHARED_SECRET literalmente iguales
    al texto de la plantilla). Antes de esto, nada detectaba ese error.
    """

    def test_bloquea_con_placeholder_y_debug_false(self, monkeypatch):
        monkeypatch.setattr(s, "DEBUG", False)
        monkeypatch.setattr(s, "SECRET_KEY", "defina-una-tercera-clave-larga-y-aleatoria-aqui")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "")
        with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
            s._validar_secretos_configurados()

    def test_bloquea_con_clave_insegura_por_defecto_y_debug_false(self, monkeypatch):
        """Cubre también el caso de no definir la variable en absoluto — el
        código cae al default hardcodeado, que empieza igual con
        'django-insecure-'."""
        monkeypatch.setattr(s, "DEBUG", False)
        monkeypatch.setattr(s, "SECRET_KEY", "django-insecure-l(y5b6tjpk+cualquier-cosa")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "")
        with pytest.raises(ImproperlyConfigured):
            s._validar_secretos_configurados()

    def test_bloquea_si_jwt_shared_secret_tambien_es_placeholder(self, monkeypatch):
        monkeypatch.setattr(s, "DEBUG", False)
        monkeypatch.setattr(s, "SECRET_KEY", "un-valor-real-y-largo-generado-de-verdad")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "defina-una-cuarta-clave-larga-y-aleatoria-aqui")
        with pytest.raises(ImproperlyConfigured, match="JWT_SHARED_SECRET"):
            s._validar_secretos_configurados()

    def test_no_bloquea_con_valores_reales_y_debug_false(self, monkeypatch):
        monkeypatch.setattr(s, "DEBUG", False)
        monkeypatch.setattr(s, "SECRET_KEY", "un-valor-real-y-largo-generado-de-verdad-123456")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "otro-valor-real-y-largo-generado-de-verdad-789")
        s._validar_secretos_configurados()  # no debe lanzar nada

    def test_con_placeholder_y_debug_true_solo_advierte_no_bloquea(self, monkeypatch):
        monkeypatch.setattr(s, "DEBUG", True)
        monkeypatch.setattr(s, "SECRET_KEY", "defina-una-tercera-clave-larga-y-aleatoria-aqui")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "")
        with warnings.catch_warnings(record=True) as capturadas:
            warnings.simplefilter("always")
            s._validar_secretos_configurados()  # no debe lanzar ImproperlyConfigured
        assert any("valores de ejemplo" in str(w.message) for w in capturadas)

    def test_jwt_shared_secret_vacio_no_cuenta_como_placeholder(self, monkeypatch):
        """Vacío es el estado válido de 'sesión única no habilitada todavía'
        (ver settings.py) — no debe confundirse con un placeholder sin reemplazar."""
        monkeypatch.setattr(s, "DEBUG", False)
        monkeypatch.setattr(s, "SECRET_KEY", "un-valor-real-y-largo-generado-de-verdad-123456")
        monkeypatch.setattr(s, "JWT_SHARED_SECRET", "")
        s._validar_secretos_configurados()  # no debe lanzar nada

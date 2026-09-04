import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = "/api/auth/login/"


@pytest.fixture
def usuario_con_clave(db):
    u = User.objects.create_user(username="con_clave_test", password="clave-correcta-123")
    return u


def _intentar(client, username, password):
    return client.post(URL, {"username": username, "password": password}, format="json")


class TestBloqueoPorFuerzaBruta:
    """
    Cubre la protección contra fuerza bruta del login propio de riesgos
    (django-axes) — antes de esto, este endpoint no tenía ningún freno, a
    diferencia de /login/ del Inventario. Ver settings.py: AXES_FAILURE_LIMIT
    y la nota sobre por qué AXES_LOCKOUT_PARAMETERS debe ser una lista
    ANIDADA (no plana) para bloquear por la combinación usuario+IP y no por
    IP sola.
    """

    def test_intentos_por_debajo_del_limite_no_bloquean(self, usuario_con_clave):
        client = APIClient()
        for _ in range(4):  # AXES_FAILURE_LIMIT = 5 — cuatro fallos no deben bloquear
            resp = _intentar(client, "con_clave_test", "clave-incorrecta")
            assert resp.status_code == 400
        # El quinto intento, con la clave correcta, debe funcionar — todavía no se alcanzó el límite.
        resp = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp.status_code == 200

    def test_alcanzar_el_limite_bloquea_incluso_la_clave_correcta(self, usuario_con_clave):
        client = APIClient()
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")
        resp = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp.status_code == 400  # bloqueado, no "credenciales inválidas" de verdad

    def test_no_revela_que_esta_bloqueado_vs_credenciales_invalidas(self, usuario_con_clave):
        """Mismo mensaje genérico en ambos casos — no hay que darle a un
        atacante información sobre si el problema es la clave o el bloqueo."""
        client = APIClient()
        resp_normal = _intentar(client, "con_clave_test", "clave-incorrecta")
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")
        resp_bloqueado = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp_normal.data == resp_bloqueado.data

    def test_bloqueo_es_por_usuario_no_por_ip_completa(self, usuario_con_clave):
        """El hallazgo central de esta ronda: con AXES_LOCKOUT_PARAMETERS mal
        configurado (lista plana en vez de anidada), esta prueba fallaría —
        un segundo usuario válido, atacado desde la misma IP de pruebas,
        quedaría bloqueado también. Ver el comentario en settings.py."""
        otro = User.objects.create_user(username="otro_usuario_test", password="otra-clave-456")

        client = APIClient()
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")

        # Mismo cliente de pruebas => misma IP de origen (127.0.0.1/testserver).
        resp = _intentar(client, "otro_usuario_test", "otra-clave-456")
        assert resp.status_code == 200
        del otro

    def test_login_correcto_resetea_el_contador_de_fallos(self, usuario_con_clave):
        client = APIClient()
        for _ in range(3):  # por debajo del límite
            _intentar(client, "con_clave_test", "clave-incorrecta")
        resp_ok = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp_ok.status_code == 200

        # Tras un login exitoso (AXES_RESET_ON_SUCCESS=True), el contador
        # vuelve a cero — otros 4 fallos seguidos no deberían bloquear todavía.
        for _ in range(4):
            resp = _intentar(client, "con_clave_test", "clave-incorrecta")
            assert resp.status_code == 400
        resp_final = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp_final.status_code == 200

    @override_settings(AXES_LOCKOUT_PARAMETERS=["username", "ip_address"])
    def test_configuracion_plana_bloquearia_a_otro_usuario_de_la_misma_ip(self, usuario_con_clave):
        """Prueba de control: reproduce el error real que se encontró y
        corrigió — confirma que la forma PLANA (sin anidar) sí bloquea a un
        usuario distinto desde la misma IP, para que quede evidencia de por
        qué la configuración final usa la forma anidada en su lugar."""
        otro = User.objects.create_user(username="con_config_plana_test", password="otra-clave-789")

        client = APIClient()
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")

        resp = _intentar(client, "con_config_plana_test", "otra-clave-789")
        assert resp.status_code == 400  # bloqueado por IP, aunque las credenciales son correctas
        del otro


class TestComandoDesbloquearLogin:
    """
    Cubre `desbloquear_login` — el comando de diagnóstico contundente que se
    agregó después de que, en un despliegue real, `axes_reset_username`
    reportó éxito sin que el bloqueo desapareciera de verdad (causa exacta no
    confirmada — ver README-DESPLIEGUE.md sección 11.5bis). A diferencia de
    ese comando, este muestra el estado real antes y después con datos de la
    base, no solo un mensaje.
    """

    def test_limpia_el_bloqueo_y_permite_entrar_de_nuevo(self, usuario_con_clave, capsys):
        from django.core.management import call_command

        client = APIClient()
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")
        assert _intentar(client, "con_clave_test", "clave-correcta-123").status_code == 400  # bloqueado

        call_command("desbloquear_login", "con_clave_test")

        resp = _intentar(client, "con_clave_test", "clave-correcta-123")
        assert resp.status_code == 200

    def test_muestra_el_estado_antes_y_despues_con_datos_reales(self, usuario_con_clave, capsys):
        from django.core.management import call_command

        client = APIClient()
        for _ in range(5):
            _intentar(client, "con_clave_test", "clave-incorrecta")

        call_command("desbloquear_login", "con_clave_test")
        salida = capsys.readouterr().out

        assert "ANTES" in salida
        assert "con_clave_test" in salida
        assert "fallos=5" in salida
        assert "Sin filas en AccessAttempt" in salida  # el DESPUÉS

    def test_no_falla_si_el_usuario_no_tiene_ningun_bloqueo(self):
        """Correrlo sobre alguien que nunca falló un login no debe reventar —
        es la primera cosa que alguien probaría si está confundido sobre
        quién/qué está realmente bloqueado."""
        from django.core.management import call_command
        call_command("desbloquear_login", "nadie_ha_intentado_este_usuario")  # no debe lanzar

    def test_flag_todos_limpia_bloqueos_de_otros_usuarios_tambien(self, usuario_con_clave):
        from django.core.management import call_command
        from axes.models import AccessAttempt

        otro = User.objects.create_user(username="otro_bloqueado_test", password="x")
        client_a = APIClient()
        client_b = APIClient()
        for _ in range(5):
            _intentar(client_a, "con_clave_test", "incorrecta")
        for _ in range(5):
            _intentar(client_b, "otro_bloqueado_test", "incorrecta")
        assert AccessAttempt.objects.count() == 2

        call_command("desbloquear_login", "con_clave_test", "--todos")

        assert AccessAttempt.objects.count() == 0
        del otro

    def test_encuentra_bloqueo_guardado_con_mayusculas_distintas(self, usuario_con_clave):
        """El username que axes guarda viene del formulario tal cual se
        escribió — si alguien probó 'Admin' y luego resetea 'admin', debe
        encontrarlo igual."""
        from django.core.management import call_command
        from axes.models import AccessAttempt

        client = APIClient()
        for _ in range(5):
            _intentar(client, "CON_CLAVE_TEST", "incorrecta")  # con mayúsculas
        assert AccessAttempt.objects.filter(username="CON_CLAVE_TEST").exists()

        call_command("desbloquear_login", "con_clave_test")  # reset en minúsculas

        assert AccessAttempt.objects.count() == 0

"""Re-hidrata request.user desde la cookie de sesión cuando el middleware de
auth de Django no lo hizo (p. ej. subpeticiones concurrentes con SQLite)."""
from .sesion_plataforma import http_request, usuario_desde_sesion


class SesionPlataformaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        req = http_request(request)
        if not getattr(req.user, "is_authenticated", False):
            user = usuario_desde_sesion(req)
            if user is not None:
                req.user = user
        return self.get_response(request)

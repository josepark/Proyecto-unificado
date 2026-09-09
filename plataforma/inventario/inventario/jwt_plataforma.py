# -*- coding: utf-8 -*-
"""
Emisión de JWT de plataforma.

El Inventario es la fuente única de identidad y roles del despliegue
unificado (ver permisos.py). Este módulo firma un JWT de corta duración con
esa identidad, para que otros módulos (hoy: SUIIN-SGSI-RIESGOS) puedan
autenticar al mismo usuario sin tener su propio sistema de login ni llamar de
vuelta al Inventario en cada petición — solo verifican la firma localmente
con el mismo secreto compartido (JWT_SHARED_SECRET).

No reemplaza el login por sesión del Inventario (con django-axes protegiendo
intentos fallidos) — lo complementa: una vez hay sesión, se puede pedir un
JWT para usar en los demás módulos.
"""
import datetime

import jwt
from django.conf import settings

from .permisos import roles_de, ROL_DINAMIZADOR, ROL_ADMIN
from .signals import jwt_version_de


class JWTNoConfigurado(Exception):
    """JWT_SHARED_SECRET no está definido — no se pueden emitir tokens."""


def emitir_jwt(user):
    if not settings.JWT_SHARED_SECRET:
        raise JWTNoConfigurado(
            "JWT_SHARED_SECRET no está configurado — defínalo en .env (ver .env.example) "
            "antes de habilitar la sesión única con otros módulos.")

    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "iss": settings.JWT_ISSUER,
        "sub": str(user.pk),
        "username": user.get_username(),
        "roles": sorted(roles_de(user)),
        "ver": jwt_version_de(user),
        "iat": ahora,
        "exp": ahora + datetime.timedelta(minutes=settings.JWT_EXPIRACION_MINUTOS),
    }
    token = jwt.encode(payload, settings.JWT_SHARED_SECRET, algorithm=settings.JWT_ALGORITHM)
    # PyJWT >= 2 ya devuelve str; se normaliza por si acaso corre una versión vieja.
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token, payload["exp"]

# -*- coding: utf-8 -*-
"""
Emisión y renovación de JWT de plataforma (access + refresh).

Access token: corta duración (JWT_EXPIRACION_MINUTOS).
Refresh token: larga duración (JWT_REFRESH_EXPIRACION_DIAS) — solo sirve
para obtener un nuevo par sin volver a pedir contraseña.
"""
import datetime

import jwt
from django.conf import settings
from django.contrib.auth.models import User

from .permisos import roles_de
from .espacio_datos import espacio_datos_de
from .modulos_plataforma import modulos_de
from .signals import jwt_version_de


class JWTNoConfigurado(Exception):
    """JWT_SHARED_SECRET no está definido — no se pueden emitir tokens."""


class RefreshTokenInvalido(Exception):
    """Refresh token ausente, mal formado, expirado o revocado."""


def _payload_base(user):
    espacio = espacio_datos_de(user)
    return {
        "iss": settings.JWT_ISSUER,
        "sub": str(user.pk),
        "username": user.get_username(),
        "roles": sorted(roles_de(user)),
        "modulos": modulos_de(user),
        "espacio_codigo": espacio.codigo if espacio else "",
        "ver": jwt_version_de(user),
    }


def _codificar(payload):
    if not settings.JWT_SHARED_SECRET:
        raise JWTNoConfigurado(
            "JWT_SHARED_SECRET no está configurado — defínalo en .env (ver .env.example) "
            "antes de habilitar la sesión única con otros módulos.")
    token = jwt.encode(payload, settings.JWT_SHARED_SECRET, algorithm=settings.JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def emitir_jwt(user):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = _payload_base(user)
    payload.update({
        "typ": "access",
        "iat": ahora,
        "exp": ahora + datetime.timedelta(minutes=settings.JWT_EXPIRACION_MINUTOS),
    })
    return _codificar(payload), payload["exp"]


def emitir_refresh_jwt(user):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = _payload_base(user)
    payload.update({
        "typ": "refresh",
        "iat": ahora,
        "exp": ahora + datetime.timedelta(days=settings.JWT_REFRESH_EXPIRACION_DIAS),
    })
    return _codificar(payload), payload["exp"]


def emitir_par_jwt(user):
    access, access_exp = emitir_jwt(user)
    refresh, refresh_exp = emitir_refresh_jwt(user)
    return access, access_exp, refresh, refresh_exp


def renovar_desde_refresh(refresh_token):
    if not refresh_token:
        raise RefreshTokenInvalido("Refresh token requerido.")
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SHARED_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise RefreshTokenInvalido("Refresh token inválido o expirado.") from exc

    if payload.get("typ") != "refresh":
        raise RefreshTokenInvalido("No es un refresh token.")

    try:
        user = User.objects.get(pk=int(payload["sub"]))
    except (User.DoesNotExist, ValueError, TypeError) as exc:
        raise RefreshTokenInvalido("Usuario del refresh token no existe.") from exc

    if jwt_version_de(user) != payload.get("ver"):
        raise RefreshTokenInvalido("Refresh token revocado.")

    return emitir_par_jwt(user)

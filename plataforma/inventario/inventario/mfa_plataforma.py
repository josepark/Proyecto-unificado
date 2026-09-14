# -*- coding: utf-8 -*-
"""MFA TOTP en el login de plataforma (Inventario)."""
import base64
import io

import pyotp
import qrcode
from django.contrib.auth.models import User

from .models import PerfilPlataforma


def _perfil(user):
    perfil, _ = PerfilPlataforma.objects.get_or_create(user=user)
    return perfil


def mfa_habilitado(user):
    perfil = _perfil(user)
    return perfil.mfa_habilitado and bool(perfil.mfa_totp_secreto)


def iniciar_configuracion_mfa(user):
    perfil = _perfil(user)
    secreto = pyotp.random_base32()
    perfil.mfa_totp_secreto = secreto
    perfil.mfa_habilitado = False
    perfil.save(update_fields=["mfa_totp_secreto", "mfa_habilitado"])
    uri = pyotp.TOTP(secreto).provisioning_uri(
        name=user.get_username(),
        issuer_name="SUIIN Plataforma",
    )
    buffer = io.BytesIO()
    qrcode.make(uri).save(buffer, format="PNG")
    qr_png_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {"otpauth_uri": uri, "qr_png_b64": qr_png_b64}


def confirmar_configuracion_mfa(user, codigo):
    perfil = _perfil(user)
    if not perfil.mfa_totp_secreto:
        return False, "Configure MFA primero."
    if not _verificar_codigo(perfil.mfa_totp_secreto, codigo):
        return False, "Código incorrecto."
    perfil.mfa_habilitado = True
    perfil.save(update_fields=["mfa_habilitado"])
    return True, "MFA activado."


def desactivar_mfa(user, codigo):
    perfil = _perfil(user)
    if not perfil.mfa_habilitado:
        return True, "MFA ya estaba desactivado."
    if not _verificar_codigo(perfil.mfa_totp_secreto, codigo):
        return False, "Código incorrecto."
    perfil.mfa_totp_secreto = ""
    perfil.mfa_habilitado = False
    perfil.save(update_fields=["mfa_totp_secreto", "mfa_habilitado"])
    return True, "MFA desactivado."


def verificar_mfa_login(user, codigo):
    perfil = _perfil(user)
    if not perfil.mfa_habilitado or not perfil.mfa_totp_secreto:
        return True
    return _verificar_codigo(perfil.mfa_totp_secreto, codigo)


def _verificar_codigo(secreto, codigo):
    codigo = (codigo or "").strip().replace(" ", "")
    if not codigo:
        return False
    return pyotp.TOTP(secreto).verify(codigo, valid_window=1)

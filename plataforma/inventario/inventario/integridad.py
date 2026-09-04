"""
Cadena de integridad del Inventario — mismo esquema que ya usaba RBAC
(rbac/db.py: _hash_registro / audit / verificar_cadena), replicado aquí
para que el Inventario dé la misma garantía verificable sobre su propia
bitácora de cambios (ISO/IEC 27001:2022 — 8.15). Antes, django-simple-
history ya registraba bien quién/cuándo/qué cambió, pero no de forma
verificable: nada impedía editar una fila de esa bitácora directamente en
la base de datos sin dejar rastro. Cada fila de RegistroIntegridad sella
la anterior con SHA-256, igual que en RBAC — cualquier alteración hecha
por fuera de la aplicación rompe la cadena a partir de ese punto.

No reemplaza a django-simple-history (que sigue guardando el detalle
campo por campo de cada cambio, usado en la ficha de cada activo); esto
es una capa de verificación por encima, sobre el mismo evento.
"""
import hashlib

from django.utils import timezone

GENESIS = "GENESIS"


def _hash_registro(anterior, fecha, entidad, accion, detalle, responsable):
    # Mismo formato exacto que rbac/db.py:_hash_registro — no es casualidad,
    # es intencional: cualquiera familiarizado con la verificación de RBAC
    # reconoce de inmediato el mismo esquema aquí.
    base = f"{anterior}|{fecha}|{entidad}|{accion}|{detalle}|{responsable}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def registrar(entidad, accion, detalle, responsable):
    """Agrega una fila a la cadena, encadenada contra la última existente."""
    from .models import RegistroIntegridad
    ultimo = RegistroIntegridad.objects.order_by("-id").first()
    anterior = ultimo.hash if ultimo else GENESIS
    fecha = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    h = _hash_registro(anterior, fecha, entidad, accion, detalle, responsable)
    return RegistroIntegridad.objects.create(
        fecha=fecha, entidad=entidad, accion=accion, detalle=detalle,
        responsable=responsable, hash_anterior=anterior, hash=h)


def verificar_cadena():
    """Recorre RegistroIntegridad y confirma que cada hash es exactamente
    el que resulta de recalcular con el registro anterior. Devuelve
    (True, total_verificado) si está intacta, o (False, id_de_la_primera_
    fila_alterada) si detecta una alteración."""
    from .models import RegistroIntegridad
    anterior = GENESIS
    total = 0
    for r in RegistroIntegridad.objects.order_by("id"):
        esperado = _hash_registro(anterior, r.fecha, r.entidad, r.accion,
                                  r.detalle, r.responsable)
        if r.hash != esperado:
            return False, r.id
        anterior = r.hash
        total += 1
    return True, total

# -*- coding: utf-8 -*-
"""
sincronizar_activos_inventario — Trae el catálogo de activos desde la Plataforma
SUIIN (app "Inventario") y lo sistematiza en riesgos, en vez de mantener un
catálogo de activos duplicado.

El Inventario es ahora la fuente CANÓNICA de la identidad del activo (código,
nombre, tipo, IP, clasificación, valoración C-I-D). Los campos propios del
dominio de riesgos (cobertura de escaneo, observación crítica, afectado por Red
Team, campaña asociada, etc.) siguen viviendo y editándose solo en riesgos.

Correlación entre catálogos:
  - Si el activo de riesgos ya tiene `inventario_id` (de una sincronización
    previa), se usa esa vinculación directamente.
  - Si no, se intenta por `id_activo` exacto (los códigos RED-XXX coinciden
    entre ambos sistemas desde el origen).
  - Si tampoco, se intenta por `nombre` normalizado (case-insensitive) — cubre
    los códigos SI-XX (riesgos, heredados del Excel original) que en el
    Inventario están numerados como SIS-XXX; los nombres sí coinciden
    exactamente (ej. "CENSO", "JUSTICIA PROPIA").
  - Si no hay ningún match, se crea un activo nuevo en riesgos vinculado al
    Inventario — típicamente porque se dio de alta después de la migración
    inicial de la matriz de riesgos.

Al vincular, el `id_activo` de riesgos se actualiza para adoptar el código
canónico del Inventario (ej. "SI-06" -> "SIS-006") — es seguro: ninguna relación
en riesgos usa ese código como clave, todas usan la clave primaria numérica.

Uso:
    python manage.py sincronizar_activos_inventario
    python manage.py sincronizar_activos_inventario --url http://inventario:8000/api
    python manage.py sincronizar_activos_inventario --forzar-sobrescritura
"""
import unicodedata

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from riesgos.inventario_cliente import get as inventario_get
from riesgos.models import Activo
from riesgos.sincronizacion import ProtectorSincronizacion

CLASIFICACION_MAP = {
    "ALTA": "ALTAMENTE_CONFIDENCIAL",
    "CONF": "CONFIDENCIAL",
    "INT": "CONFIDENCIAL",  # "Uso Interno" no tiene equivalente exacto en riesgos
    "PUB": "PUBLICO",
    "": "DESCONOCIDA",
}

CLASE_TIPO_MAP = {
    "INFRA": "Infraestructura de red",
    "SIST": "Sistema de información",
    "EQUI": "Equipo de cómputo",
}


def normalizar(texto):
    """Minúsculas, sin espacios sobrantes, sin tildes — 'PEDAGÓGICO' y 'PEDAGOGICO'
    deben emparejar (tildes inconsistentes entre quien digitó cada catálogo es un
    caso legítimo). Un typo real como 'MOODEL'/'MOODLE' sigue sin coincidir, y así
    debe ser: no es tarea de esta función adivinar errores de tipeo."""
    texto = (texto or "").strip().casefold()
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


class Command(BaseCommand):
    help = "Sincroniza el catálogo de activos desde la Plataforma SUIIN (Inventario)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url", type=str, default=None,
            help="URL base de la API del inventario (por defecto: settings.INVENTARIO_API_URL).")
        parser.add_argument(
            "--forzar-sobrescritura", action="store_true",
            help="Sobrescribe también los activos editados manualmente en riesgos desde la "
                 "última sincronización (por defecto se protegen y se omiten).")
        parser.add_argument(
            "--timeout", type=int, default=15,
            help="Segundos de espera por solicitud HTTP antes de abortar (default: 15).")
        parser.add_argument(
            "--espacio", type=str, default="organizacion",
            help="Código de espacio de datos (debe coincidir con el del inventario).")
        parser.add_argument(
            "--todos-espacios", action="store_true",
            help="Sincroniza cada espacio registrado en el Inventario (organizacion + personales).")

    def handle(self, *args, **options):
        if options.get("todos_espacios"):
            espacios = self._listar_espacios_inventario(options)
            if not espacios:
                self.stderr.write(self.style.ERROR(
                    "No se pudieron listar espacios del inventario."))
                return
            for codigo in espacios:
                self.stdout.write(self.style.NOTICE(f"→ Espacio «{codigo}»"))
                opts = {**options, "espacio": codigo, "todos_espacios": False}
                self._sync_espacio(opts)
            return
        self._sync_espacio(options)

    def _listar_espacios_inventario(self, options):
        base_url = (options.get("url") or settings.INVENTARIO_API_URL).rstrip("/")
        timeout = options.get("timeout", 15)
        url = f"{base_url}/interno/espacios/"
        try:
            resp = inventario_get(url, timeout=timeout)
            if resp.status_code == 404:
                return ["organizacion"]
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                codigos = [e["codigo"] for e in data if e.get("codigo")]
                return codigos or ["organizacion"]
            return ["organizacion"]
        except requests.RequestException:
            return ["organizacion"]

    def _sync_espacio(self, options):
        base_url = (options.get("url") or settings.INVENTARIO_API_URL).rstrip("/")
        timeout = options["timeout"]
        espacio = (options.get("espacio") or "organizacion").strip()
        protector = ProtectorSincronizacion(forzar=options["forzar_sobrescritura"])
        self.espacio_codigo = espacio

        if protector.forzar:
            self.stdout.write(self.style.WARNING(
                "⚠ --forzar-sobrescritura activo: se sobrescribirán también los activos "
                "editados manualmente en riesgos desde la última sincronización."))

        try:
            activos_inventario = self._obtener_todos(base_url, timeout)
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(
                f"No se pudo conectar con el inventario en {base_url}: {e}\n"
                "Verifique que el servicio 'inventario' esté corriendo y que "
                "INVENTARIO_API_URL (o --url) apunte a la dirección correcta."))
            return

        self.stdout.write(f"→ {len(activos_inventario)} activo(s) obtenidos del inventario ({base_url}).")

        vinculados_por_nombre = []
        errores = []

        with transaction.atomic():
            for item in activos_inventario:
                try:
                    vinculo = self._sincronizar_uno(item, base_url, timeout, protector)
                    if vinculo:
                        vinculados_por_nombre.append(vinculo)
                except Exception as e:  # noqa: BLE001 — no se debe abortar todo el lote por un ítem
                    errores.append(f"{item.get('id_activo', '?')}: {e}")

        protector.reportar(self.stdout, self.stderr, self.style)

        if vinculados_por_nombre:
            self.stdout.write(self.style.WARNING(
                f"ℹ {len(vinculados_por_nombre)} activo(s) vinculado(s) por coincidencia de "
                f"nombre (no de código) — revise que la correlación sea correcta:"))
            for linea in vinculados_por_nombre:
                self.stdout.write(f"    · {linea}")

        huerfanos = Activo.objects.filter(
            inventario_id__isnull=True, espacio_codigo=espacio,
        ).count()
        if huerfanos:
            self.stdout.write(self.style.WARNING(
                f"ℹ {huerfanos} activo(s) en riesgos sin vínculo al inventario tras la "
                "sincronización — puede que ya no existan allá, o que su nombre haya "
                "cambiado demasiado para el emparejamiento automático."))

        if errores:
            self.stderr.write(self.style.ERROR(f"⚠ {len(errores)} activo(s) con error, omitidos:"))
            for linea in errores:
                self.stderr.write(f"    · {linea}")

    def _obtener_todos(self, base_url, timeout):
        """Pagina /api/activos/ hasta agotar los resultados."""
        activos = []
        url = f"{base_url}/activos/"
        params = {"page_size": 100}
        while url:
            resp = inventario_get(url, espacio_codigo=self.espacio_codigo, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            # DRF pagination o, si el endpoint no pagina, una lista directa.
            activos.extend(data["results"] if isinstance(data, dict) and "results" in data else data)
            url = data.get("next") if isinstance(data, dict) else None
            params = None  # 'next' ya trae los query params codificados
        return activos

    def _obtener_detalle(self, base_url, inventario_id, timeout):
        resp = inventario_get(
            f"{base_url}/activos/{inventario_id}/",
            espacio_codigo=self.espacio_codigo,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _sincronizar_uno(self, item, base_url, timeout, protector):
        inv_id = item["id"]
        id_activo = item["id_activo"]
        nombre = item["nombre"]
        clase = item.get("clase", "")
        clasificacion = CLASIFICACION_MAP.get(item.get("clasificacion_si") or "", "DESCONOCIDA")
        valor = item.get("valor")

        ip_principal = None
        vlan = None
        if clase == "INFRA":
            detalle = self._obtener_detalle(base_url, inv_id, timeout)
            infra = (detalle or {}).get("infraestructura") or {}
            ip_principal = infra.get("ip_segmento") or None
            vlan = infra.get("vlan") or None

        defaults = dict(
            inventario_id=inv_id,
            id_activo=id_activo,
            nombre=nombre,
            tipo=CLASE_TIPO_MAP.get(clase, clase or ""),
            valor=valor if valor is not None else 0,
            clasificacion_si=clasificacion,
            espacio_codigo=self.espacio_codigo,
        )
        if ip_principal:
            defaults["ip_principal"] = ip_principal
        if vlan:
            defaults["vlan"] = vlan

        esp = self.espacio_codigo
        # 1) Ya vinculado de una sincronización anterior.
        existente = Activo.objects.filter(inventario_id=inv_id, espacio_codigo=esp).first()
        vinculo_por_nombre = None

        # 2) Coincide el código exacto (típico de RED-XXX).
        if not existente:
            existente = Activo.objects.filter(
                id_activo=id_activo, inventario_id__isnull=True, espacio_codigo=esp,
            ).first()

        # 3) Coincide el nombre, normalizado (típico de SI-XX <-> SIS-XXX).
        if not existente:
            candidatos_exactos = [
                a for a in Activo.objects.filter(inventario_id__isnull=True, espacio_codigo=esp)
                if normalizar(a.nombre) == normalizar(nombre)
            ]
            if len(candidatos_exactos) == 1:
                existente = candidatos_exactos[0]
                vinculo_por_nombre = f"{existente.id_activo} ({existente.nombre}) → {id_activo}"

        # 4) Última red de seguridad: uno de los nombres contiene literalmente al
        # otro (ej. "KEYCLOAK" dentro de "KEYCLOAK (IAM/SSO)"). Deliberadamente NO
        # se intenta nada más difuso que esto (sin distancia de edición/fuzzy
        # matching): un typo real como "MOODEL"/"MOODLE" no debe auto-corregirse
        # en silencio — mejor crear un duplicado detectable y reportado que fusionar
        # mal dos activos distintos. Solo aplica si hay un único candidato posible.
        if not existente:
            nom_norm = normalizar(nombre)
            candidatos_parciales = [
                a for a in Activo.objects.filter(inventario_id__isnull=True, espacio_codigo=esp)
                if nom_norm and normalizar(a.nombre)
                and (normalizar(a.nombre) in nom_norm or nom_norm in normalizar(a.nombre))
            ]
            if len(candidatos_parciales) == 1:
                existente = candidatos_parciales[0]
                vinculo_por_nombre = (
                    f"{existente.id_activo} ({existente.nombre}) → {id_activo} ({nombre}) "
                    f"[coincidencia PARCIAL — revisar con más atención]")

        if existente:
            # El vínculo (inventario_id) se establece siempre, incluso si el resto de
            # los campos queda protegido — de lo contrario, un activo editado antes de
            # la primera sincronización nunca llegaría a vincularse (ver docstring del
            # módulo). Actualizar solo inventario_id no pisa ninguna edición manual:
            # ese campo no es visible ni editable desde el formulario de la app.
            if existente.inventario_id != inv_id:
                Activo.objects.filter(pk=existente.pk).update(inventario_id=inv_id)
            protector.guardar_protegiendo(Activo, {"pk": existente.pk}, defaults, descripcion=id_activo)
        else:
            protector.guardar_protegiendo(Activo, {"inventario_id": inv_id}, defaults, descripcion=id_activo)

        return vinculo_por_nombre

# -*- coding: utf-8 -*-
"""
sincronizar_tecnicas_mitre — Trae el catálogo MITRE ATT&CK desde
/api/amenazas/ del Inventario y lo sistematiza en riesgos.

A diferencia de sincronizar_activos_inventario, este NO usa el mecanismo de
protección contra ediciones manuales — es catálogo de referencia externo
(viene de MITRE, vía el Inventario), no algo que el analista edite campo a
campo desde riesgos, así que un upsert simple y directo es correcto aquí.

Uso:
    python manage.py sincronizar_tecnicas_mitre
    python manage.py sincronizar_tecnicas_mitre --url http://inventario:8000/api
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from riesgos.models import TecnicaMitre


class Command(BaseCommand):
    help = "Sincroniza el catálogo MITRE ATT&CK desde /api/amenazas/ del Inventario."

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, default=None,
                             help="URL base de la API del inventario (por defecto: settings.INVENTARIO_API_URL).")
        parser.add_argument("--timeout", type=int, default=15)

    def handle(self, *args, **options):
        base_url = (options.get("url") or settings.INVENTARIO_API_URL).rstrip("/")
        timeout = options["timeout"]

        try:
            tecnicas = self._obtener_todas(base_url, timeout)
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(
                f"No se pudo conectar con el inventario en {base_url}: {e}\n"
                "Verifique que el servicio 'inventario' esté corriendo y que "
                "INVENTARIO_API_URL (o --url) apunte a la dirección correcta."))
            return

        self.stdout.write(f"→ {len(tecnicas)} técnica(s)/táctica(s) obtenidas del inventario ({base_url}).")

        creados, actualizados = 0, 0
        for item in tecnicas:
            _, creado = TecnicaMitre.objects.update_or_create(
                codigo=item["codigo"],
                defaults=dict(
                    nombre=item.get("nombre") or "",
                    tipo=item.get("tipo") or "",
                    tacticas=item.get("tacticas") or "",
                    codigo_padre=item.get("codigo_padre") or "",
                    url=item.get("url") or "",
                ),
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sincronización completada: {creados} creado(s), {actualizados} actualizado(s)."))

    def _obtener_todas(self, base_url, timeout):
        tecnicas = []
        url = f"{base_url}/amenazas/"
        params = {"page_size": 200}
        while url:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            tecnicas.extend(data["results"] if isinstance(data, dict) and "results" in data else data)
            url = data.get("next") if isinstance(data, dict) else None
            params = None
        return tecnicas

"""
migrar_racks_legacy — Vincula texto legacy (rack / unidad_rack) al catálogo Rack.

Antes de Ola 2, la ubicación física se guardaba como texto libre. Este comando
empareja esas filas con registros Rack del mismo centro de datos y rellena
rack_fk + unidad_inicio/fin cuando puede inferirlos.

    python manage.py migrar_racks_legacy
    python manage.py migrar_racks_legacy --dry-run
    python manage.py migrar_racks_legacy --crear-faltantes
"""
from django.core.management.base import BaseCommand

from inventario.models import ActivoInfraestructura, Rack
from inventario.rack_utils import (
    emparejar_rack_en_datacenter,
    normalizar_codigo_rack,
    parse_unidad_rack,
)


class Command(BaseCommand):
    help = "Migra rack/unidad_rack (texto) hacia rack_fk + U inicio/fin del catálogo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo informa qué haría, sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--crear-faltantes", action="store_true",
            help="Crea un Rack con el código normalizado si no existe en el DC del activo.",
        )

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        crear = opts["crear_faltantes"]
        migrados = sin_dc = sin_rack = sin_match = u_parse = 0

        qs = (ActivoInfraestructura.objects
              .select_related("activo", "activo__datacenter", "rack_fk")
              .filter(rack_fk__isnull=True)
              .exclude(rack=""))

        for inf in qs:
            activo = inf.activo
            if not activo.datacenter_id:
                sin_dc += 1
                self.stdout.write(f"  SKIP {activo.id_activo}: sin centro de datos")
                continue

            codigo = normalizar_codigo_rack(inf.rack)
            if not codigo:
                sin_rack += 1
                continue

            racks_dc = Rack.objects.filter(datacenter_id=activo.datacenter_id)
            rack = emparejar_rack_en_datacenter(racks_dc, inf.rack)

            if rack is None and crear:
                rack = Rack(
                    datacenter_id=activo.datacenter_id,
                    codigo=codigo,
                    capacidad_u=42,
                )
                if not dry:
                    rack.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"  + Rack creado {activo.datacenter.codigo}/{codigo} "
                        f"para {activo.id_activo}"))

            if rack is None:
                sin_match += 1
                self.stdout.write(
                    f"  ? {activo.id_activo}: «{inf.rack}» sin match en "
                    f"{activo.datacenter.codigo} (use --crear-faltantes)")
                continue

            u_ini, u_fin = parse_unidad_rack(inf.unidad_rack)
            if u_ini:
                u_parse += 1

            if dry:
                self.stdout.write(
                    f"  → {activo.id_activo}: {inf.rack!r} → {rack.codigo}"
                    + (f" U{u_ini}-U{u_fin}" if u_ini else ""))
                migrados += 1
                continue

            inf.rack_fk = rack
            if u_ini:
                inf.unidad_inicio = u_ini
                inf.unidad_fin = u_fin
            inf.save()
            migrados += 1

        resumen = (
            f"Migración racks legacy: {migrados} vinculados"
            + (f", {u_parse} con U parseadas" if u_parse else "")
            + (f", {sin_match} sin match" if sin_match else "")
            + (f", {sin_dc} sin DC" if sin_dc else "")
        )
        if dry:
            self.stdout.write(self.style.WARNING(f"[dry-run] {resumen}"))
        else:
            self.stdout.write(self.style.SUCCESS(resumen))

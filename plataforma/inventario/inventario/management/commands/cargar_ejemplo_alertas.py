"""Enriquece activos de infraestructura con datos de ciclo de vida para
que el tablero de alertas muestre casos reales (no destructivo)."""
from datetime import date
from django.core.management.base import BaseCommand
from inventario.models import Activo, ActivoInfraestructura


class Command(BaseCommand):
    help = "Carga fechas de EOL/garantia/escaneo de ejemplo para el tablero de alertas"

    def handle(self, *args, **o):
        # (id_activo): (eol, garantia, ultimo_escaneo, hallazgos)
        datos = {
            "RED-021": (date(2024, 12, 31), date(2024, 6, 30), date(2025, 9, 5), 8),   # DVR EOL vencido
            "RED-022": (date(2025, 3, 31), date(2024, 8, 15), None, 4),                # DVR EOL vencido
            "RED-001": (date(2026, 9, 30), date(2026, 8, 30), date(2026, 1, 10), 0),   # modem EOL proximo
            "RED-004": (date(2027, 5, 1), date(2026, 10, 15), date(2025, 12, 1), 2),   # switch garantia proxima
            "RED-019": (date(2028, 1, 1), date(2027, 1, 1), date(2025, 8, 20), 3),     # Oracle escaneo viejo
            "RED-012": (date(2029, 3, 15), date(2027, 3, 15), date(2026, 6, 1), 1),    # Proxmox ok
        }
        n = 0
        for cod, (eol, gar, scan, hall) in datos.items():
            try:
                inf = ActivoInfraestructura.objects.get(activo__id_activo=cod)
            except ActivoInfraestructura.DoesNotExist:
                continue
            # solo completar si esta vacio (no sobrescribir)
            if inf.fin_soporte_eol is None:
                inf.fin_soporte_eol = eol
            if inf.fin_garantia is None:
                inf.fin_garantia = gar
            if inf.fecha_ultimo_escaneo is None and scan:
                inf.fecha_ultimo_escaneo = scan
            if inf.hallazgos_abiertos is None:
                inf.hallazgos_abiertos = hall
            inf.save()
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Ciclo de vida de ejemplo cargado en {n} activos."))

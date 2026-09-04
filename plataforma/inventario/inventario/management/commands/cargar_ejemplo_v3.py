"""Carga datos de ejemplo v3: datacenters, ubicaciones, hoja de vida y diagrama."""
from datetime import date
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from inventario.models import (Activo, ActivoInfraestructura, Datacenter,
                               Diagrama, EventoHojaVida)


class Command(BaseCommand):
    help = "Carga datos de ejemplo para las funciones v3"

    def handle(self, *args, **o):
        # 1. Centros de datos (coordenadas reales de las ciudades)
        popayan, _ = Datacenter.objects.update_or_create(
            codigo="DC-POPAYAN", defaults=dict(
                nombre="Centro de Datos Principal SUIIN - CRIC",
                tipo=Datacenter.Tipo.PRINCIPAL, nivel_tier=Datacenter.Tier.T2,
                direccion="Sede CRIC", ciudad="Popayan", departamento="Cauca",
                pais="Colombia", latitud=2.4448, longitud=-76.6147,
                responsable="Coordinacion SUIIN",
                descripcion="Datacenter principal. Aloja el clúster Proxmox, "
                            "Oracle DB Appliance y almacenamiento SAN. Roadmap a Tier III."))
        bogota, _ = Datacenter.objects.update_or_create(
            codigo="DC-BOGOTA", defaults=dict(
                nombre="Mini-datacenter de respaldo Bogota",
                tipo=Datacenter.Tipo.MINI, nivel_tier=Datacenter.Tier.T3,
                direccion="Por definir", ciudad="Bogota", departamento="Cundinamarca",
                pais="Colombia", latitud=4.7110, longitud=-74.0721,
                responsable="Coordinacion SUIIN",
                descripcion="Mini-datacenter propuesto para respaldo y continuidad (DRP)."))

        # 2. Asignar activos de infraestructura al datacenter de Popayan + rack/U
        rack_map = {
            "RED-012": ("Rack 2", "U20-U21"), "RED-013": ("Rack 2", "U18-U19"),
            "RED-014": ("Rack 1", "U16-U17"), "RED-019": ("Rack 1", "U10-U13"),
            "RED-020": ("Rack 1", "U6-U9"),   "RED-003": ("Rack 2", "U40"),
        }
        n = 0
        for a in Activo.objects.filter(clase="INFRA"):
            a.datacenter = popayan
            a.save()
            n += 1
            if a.id_activo in rack_map and hasattr(a, "infraestructura"):
                inf = a.infraestructura
                inf.rack, inf.unidad_rack = rack_map[a.id_activo]
                inf.save()
        # Sistemas tambien residen en Popayan
        for a in Activo.objects.filter(clase="SIST"):
            a.datacenter = popayan
            a.save()

        # 3. Hoja de vida de ejemplo para el servidor Proxmox principal
        r740 = Activo.objects.get(id_activo="RED-012")
        eventos = [
            (date(2024, 3, 15), "ALTA", "Puesta en marcha del servidor Proxmox R740",
             "Instalacion y configuracion inicial del nodo de virtualizacion principal.",
             "Equipo SUIIN", None),
            (date(2025, 6, 10), "MPRE", "Mantenimiento preventivo semestral",
             "Limpieza fisica, verificacion de ventiladores y actualizacion de Proxmox VE.",
             "Equipo SUIIN", 350000),
            (date(2025, 11, 2), "ACTU", "Actualizacion de firmware iDRAC y BIOS",
             "Aplicacion de parches de seguridad Dell tras hallazgos OpenVAS.",
             "Equipo SUIIN", None),
            (date(2026, 1, 20), "CONF", "Habilitacion de MFA para acceso administrativo",
             "Se activo autenticacion multifactor conforme a POL-SI-009.",
             "Dinamizador SI", None),
        ]
        EventoHojaVida.objects.filter(activo=r740).delete()
        for f, t, tit, desc, resp, costo in eventos:
            EventoHojaVida.objects.create(
                activo=r740, fecha=f, tipo_evento=t, titulo=tit,
                descripcion=desc, responsable=resp, costo=costo,
                registrado_por="carga_ejemplo")

        # Un incidente en el DVR Hikvision (por los CVE conocidos)
        dvr = Activo.objects.get(id_activo="RED-021")
        EventoHojaVida.objects.filter(activo=dvr).delete()
        EventoHojaVida.objects.create(
            activo=dvr, fecha=date(2025, 9, 5), tipo_evento="INCI",
            titulo="Revision por CVE criticos de firmware Hikvision",
            descripcion="Verificacion de firmware y cambio de credenciales por defecto. "
                        "Se deshabilito acceso a internet y se segmento en VLAN CCTV.",
            responsable="Equipo SUIIN", registrado_por="carga_ejemplo")

        # 4. Diagrama de topologia de ejemplo (SVG generado)
        svg = (b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">'
               b'<rect width="640" height="360" fill="#0d2b23"/>'
               b'<text x="320" y="40" fill="#c9a94e" font-size="20" font-family="Arial" '
               b'text-anchor="middle" font-weight="bold">Topologia SUIIN - CRIC (ejemplo)</text>'
               b'<rect x="260" y="80" width="120" height="40" rx="6" fill="#3fa87f"/>'
               b'<text x="320" y="105" fill="#fff" font-size="13" font-family="Arial" '
               b'text-anchor="middle">pfSense FW</text>'
               b'<rect x="120" y="200" width="120" height="40" rx="6" fill="#1f6b52"/>'
               b'<text x="180" y="225" fill="#fff" font-size="12" font-family="Arial" '
               b'text-anchor="middle">Proxmox R740</text>'
               b'<rect x="400" y="200" width="120" height="40" rx="6" fill="#1f6b52"/>'
               b'<text x="460" y="225" fill="#fff" font-size="12" font-family="Arial" '
               b'text-anchor="middle">Oracle DB</text>'
               b'<line x1="320" y1="120" x2="180" y2="200" stroke="#3fa87f" stroke-width="2"/>'
               b'<line x1="320" y1="120" x2="460" y2="200" stroke="#3fa87f" stroke-width="2"/>'
               b'</svg>')
        d, created = Diagrama.objects.get_or_create(
            titulo="Topologia de red SUIIN (ejemplo)", datacenter=popayan,
            defaults=dict(tipo="TOPO", descripcion="Diagrama de ejemplo de la topologia principal.",
                          fecha=date(2026, 1, 15), version="1.0"))
        if created or not d.archivo:
            d.archivo.save("topologia_ejemplo.svg", ContentFile(svg), save=True)
            d.activos.set(Activo.objects.filter(id_activo__in=["RED-003", "RED-012", "RED-019"]))

        self.stdout.write(self.style.SUCCESS(
            f"Ejemplo v3 cargado: 2 datacenters, {n} activos ubicados, "
            f"{EventoHojaVida.objects.count()} eventos de hoja de vida, "
            f"{Diagrama.objects.count()} diagrama(s)."))

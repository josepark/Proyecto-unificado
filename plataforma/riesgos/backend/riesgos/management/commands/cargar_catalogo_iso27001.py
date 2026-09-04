# -*- coding: utf-8 -*-
"""
cargar_catalogo_iso27001 — Siembra el catálogo de los 93 controles del Anexo A de
ISO/IEC 27001:2022 (taxonomía fija del estándar; no depende de ningún archivo Excel).

Uso:
    python manage.py cargar_catalogo_iso27001

Idempotente (update_or_create por código) — se puede correr de nuevo sin duplicar.
Los títulos son la nomenclatura estándar de la cláusula Anexo A, tal como se
publican en toda documentación de SoA / auditoría ISMS — no se reproduce el texto
normativo (los requisitos completos) del estándar, solo el título de cada control.
"""
from django.core.management.base import BaseCommand
from riesgos.models import ControlISO27001

# (código, categoría, nombre)
CONTROLES = [
    # A.5 — Organizacionales (37)
    ("5.1", "ORGANIZACIONAL", "Políticas de seguridad de la información"),
    ("5.2", "ORGANIZACIONAL", "Roles y responsabilidades de seguridad de la información"),
    ("5.3", "ORGANIZACIONAL", "Segregación de funciones"),
    ("5.4", "ORGANIZACIONAL", "Responsabilidades de la dirección"),
    ("5.5", "ORGANIZACIONAL", "Contacto con las autoridades"),
    ("5.6", "ORGANIZACIONAL", "Contacto con grupos de interés especial"),
    ("5.7", "ORGANIZACIONAL", "Inteligencia de amenazas"),
    ("5.8", "ORGANIZACIONAL", "Seguridad de la información en la gestión de proyectos"),
    ("5.9", "ORGANIZACIONAL", "Inventario de información y otros activos asociados"),
    ("5.10", "ORGANIZACIONAL", "Uso aceptable de la información y otros activos asociados"),
    ("5.11", "ORGANIZACIONAL", "Devolución de activos"),
    ("5.12", "ORGANIZACIONAL", "Clasificación de la información"),
    ("5.13", "ORGANIZACIONAL", "Etiquetado de la información"),
    ("5.14", "ORGANIZACIONAL", "Transferencia de información"),
    ("5.15", "ORGANIZACIONAL", "Control de acceso"),
    ("5.16", "ORGANIZACIONAL", "Gestión de identidad"),
    ("5.17", "ORGANIZACIONAL", "Información de autenticación"),
    ("5.18", "ORGANIZACIONAL", "Derechos de acceso"),
    ("5.19", "ORGANIZACIONAL", "Seguridad de la información en las relaciones con proveedores"),
    ("5.20", "ORGANIZACIONAL", "Tratamiento de la seguridad de la información en acuerdos con proveedores"),
    ("5.21", "ORGANIZACIONAL", "Gestión de la seguridad de la información en la cadena de suministro TIC"),
    ("5.22", "ORGANIZACIONAL", "Seguimiento, revisión y gestión de cambios de servicios de proveedores"),
    ("5.23", "ORGANIZACIONAL", "Seguridad de la información para el uso de servicios en la nube"),
    ("5.24", "ORGANIZACIONAL", "Planificación y preparación de la gestión de incidentes de seguridad"),
    ("5.25", "ORGANIZACIONAL", "Evaluación y decisión sobre eventos de seguridad de la información"),
    ("5.26", "ORGANIZACIONAL", "Respuesta a incidentes de seguridad de la información"),
    ("5.27", "ORGANIZACIONAL", "Aprendizaje de los incidentes de seguridad de la información"),
    ("5.28", "ORGANIZACIONAL", "Recopilación de evidencia"),
    ("5.29", "ORGANIZACIONAL", "Seguridad de la información durante la disrupción"),
    ("5.30", "ORGANIZACIONAL", "Preparación TIC para la continuidad del negocio"),
    ("5.31", "ORGANIZACIONAL", "Requisitos legales, estatutarios, reglamentarios y contractuales"),
    ("5.32", "ORGANIZACIONAL", "Derechos de propiedad intelectual"),
    ("5.33", "ORGANIZACIONAL", "Protección de registros"),
    ("5.34", "ORGANIZACIONAL", "Privacidad y protección de datos personales"),
    ("5.35", "ORGANIZACIONAL", "Revisión independiente de la seguridad de la información"),
    ("5.36", "ORGANIZACIONAL", "Cumplimiento de políticas, normas y estándares de seguridad de la información"),
    ("5.37", "ORGANIZACIONAL", "Procedimientos operativos documentados"),
    # A.6 — Personas (8)
    ("6.1", "PERSONAS", "Selección de personal"),
    ("6.2", "PERSONAS", "Términos y condiciones de empleo"),
    ("6.3", "PERSONAS", "Concienciación, educación y capacitación en seguridad de la información"),
    ("6.4", "PERSONAS", "Proceso disciplinario"),
    ("6.5", "PERSONAS", "Responsabilidades tras la terminación o cambio de empleo"),
    ("6.6", "PERSONAS", "Acuerdos de confidencialidad o no divulgación"),
    ("6.7", "PERSONAS", "Trabajo remoto"),
    ("6.8", "PERSONAS", "Reporte de eventos de seguridad de la información"),
    # A.7 — Físicos (14)
    ("7.1", "FISICO", "Perímetros de seguridad física"),
    ("7.2", "FISICO", "Controles de entrada física"),
    ("7.3", "FISICO", "Seguridad de oficinas, despachos y recursos"),
    ("7.4", "FISICO", "Monitoreo de seguridad física"),
    ("7.5", "FISICO", "Protección contra amenazas físicas y ambientales"),
    ("7.6", "FISICO", "Trabajo en áreas seguras"),
    ("7.7", "FISICO", "Escritorio y pantalla limpios"),
    ("7.8", "FISICO", "Emplazamiento y protección de equipos"),
    ("7.9", "FISICO", "Seguridad de activos fuera de las instalaciones"),
    ("7.10", "FISICO", "Medios de almacenamiento"),
    ("7.11", "FISICO", "Servicios de suministro"),
    ("7.12", "FISICO", "Seguridad del cableado"),
    ("7.13", "FISICO", "Mantenimiento de equipos"),
    ("7.14", "FISICO", "Disposición segura o reutilización de equipos"),
    # A.8 — Tecnológicos (34)
    ("8.1", "TECNOLOGICO", "Dispositivos móviles de usuario final"),
    ("8.2", "TECNOLOGICO", "Derechos de acceso privilegiado"),
    ("8.3", "TECNOLOGICO", "Restricción de acceso a la información"),
    ("8.4", "TECNOLOGICO", "Acceso al código fuente"),
    ("8.5", "TECNOLOGICO", "Autenticación segura"),
    ("8.6", "TECNOLOGICO", "Gestión de capacidad"),
    ("8.7", "TECNOLOGICO", "Protección contra malware"),
    ("8.8", "TECNOLOGICO", "Gestión de vulnerabilidades técnicas"),
    ("8.9", "TECNOLOGICO", "Gestión de la configuración"),
    ("8.10", "TECNOLOGICO", "Eliminación de información"),
    ("8.11", "TECNOLOGICO", "Enmascaramiento de datos"),
    ("8.12", "TECNOLOGICO", "Prevención de fuga de datos"),
    ("8.13", "TECNOLOGICO", "Copias de seguridad de la información"),
    ("8.14", "TECNOLOGICO", "Redundancia de instalaciones de procesamiento de información"),
    ("8.15", "TECNOLOGICO", "Registro de eventos (logging)"),
    ("8.16", "TECNOLOGICO", "Actividades de monitoreo"),
    ("8.17", "TECNOLOGICO", "Sincronización de relojes"),
    ("8.18", "TECNOLOGICO", "Uso de programas utilitarios privilegiados"),
    ("8.19", "TECNOLOGICO", "Instalación de software en sistemas operativos"),
    ("8.20", "TECNOLOGICO", "Seguridad de redes"),
    ("8.21", "TECNOLOGICO", "Seguridad de los servicios de red"),
    ("8.22", "TECNOLOGICO", "Segregación de redes"),
    ("8.23", "TECNOLOGICO", "Filtrado web"),
    ("8.24", "TECNOLOGICO", "Uso de criptografía"),
    ("8.25", "TECNOLOGICO", "Ciclo de vida de desarrollo seguro"),
    ("8.26", "TECNOLOGICO", "Requisitos de seguridad de las aplicaciones"),
    ("8.27", "TECNOLOGICO", "Principios de arquitectura y ingeniería de sistemas seguros"),
    ("8.28", "TECNOLOGICO", "Codificación segura"),
    ("8.29", "TECNOLOGICO", "Pruebas de seguridad en el desarrollo y aceptación"),
    ("8.30", "TECNOLOGICO", "Desarrollo externalizado"),
    ("8.31", "TECNOLOGICO", "Separación de entornos de desarrollo, prueba y producción"),
    ("8.32", "TECNOLOGICO", "Gestión de cambios"),
    ("8.33", "TECNOLOGICO", "Información de prueba"),
    ("8.34", "TECNOLOGICO", "Protección de los sistemas de información durante las pruebas de auditoría"),
]


class Command(BaseCommand):
    help = "Siembra el catálogo fijo de 93 controles del Anexo A de ISO/IEC 27001:2022."

    def handle(self, *args, **options):
        creados, actualizados = 0, 0
        for codigo, categoria, nombre in CONTROLES:
            obj, created = ControlISO27001.objects.update_or_create(
                codigo=codigo, defaults={"categoria": categoria, "nombre": nombre}
            )
            creados += created
            actualizados += not created
        total = ControlISO27001.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo ISO 27001: {creados} creados, {actualizados} ya existían. Total: {total}/93."))
        if total != 93:
            self.stderr.write(self.style.WARNING(
                "El total no es 93 — puede haber controles creados manualmente antes de este comando."))

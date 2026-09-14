"""
SUIIN-SGSI-RIESGOS · Sistema de Gestión de Riesgos de Seguridad de la Información
Consejo Regional Indígena del Cauca (CRIC) / UAIIN — SUIIN

Este módulo sistematiza dos fuentes documentales:
  1. SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx  (10 hojas: activos, vulnerabilidades OpenVAS,
     inventario Nmap, cobertura, consolidado, correlación SI/servidor, Red Team, riesgo por activo,
     riesgo detallado por hallazgo, riesgos contextuales organizacionales RC-01..RC-07)
  2. SUIIN_SGSI_CENSO_PlanTratamiento_de_Riesgos.xlsx (Plan de Tratamiento de Riesgos — PTR)

Las hojas 04, 05 y 06 del análisis original son VISTAS derivadas (sin cobertura, consolidado
crítico, correlación SI-vs-servidor) — no se modelan como tablas propias porque se pueden
reconstruir con consultas sobre Activo/Vulnerabilidad. Las hojas "Matriz PTR", "Plan de Acción"
y "Seguimiento" del PTR describen el MISMO conjunto de riesgos R-01..R-12 en tres momentos de su
ciclo de vida, por lo que se consolidan en un solo modelo con seguimiento de estado (AccionTratamiento).
"""
import os
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from simple_history.models import HistoricalRecords


class TimeStampedModel(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    # Última vez que el comando `importar_matrices` escribió este registro (None si
    # nunca vino de un Excel — ej. creado desde la app). Comparado contra
    # `actualizado_en`, permite detectar si alguien editó el registro DESPUÉS de la
    # última importación, para que una reimportación no borre ese trabajo en
    # silencio. Ver `fue_editado_tras_importacion()` y el comando de importación.
    importado_en = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True

    def fue_editado_tras_importacion(self):
        """True si el registro se modificó (vía app/admin) después de la última
        vez que el importador de Excel lo escribió — o si nunca vino de un Excel."""
        if self.importado_en is None:
            return self.pk is not None  # ya existía y no tiene origen de import: no tocar
        if self.actualizado_en is None:
            return False
        # Pequeño margen (1s) por precisión de reloj entre escrituras en la misma transacción.
        return (self.actualizado_en - self.importado_en).total_seconds() > 1


class ControlISO27001(TimeStampedModel):
    """
    Catálogo de los 93 controles del Anexo A de ISO/IEC 27001:2022, organizados en
    las 4 categorías del estándar. Se siembra una sola vez con
    `python manage.py cargar_catalogo_iso27001` (no depende de ningún Excel — es
    la taxonomía fija del estándar). `aplicable` y `estado_implementacion` son lo
    que Jose ajusta según la Declaración de Aplicabilidad (SoA) real de SUIIN/CRIC.
    """
    CATEGORIA_CHOICES = [
        ("ORGANIZACIONAL", "Organizacional (5.x)"),
        ("PERSONAS", "Personas (6.x)"),
        ("FISICO", "Físico (7.x)"),
        ("TECNOLOGICO", "Tecnológico (8.x)"),
    ]
    ESTADO_IMPLEMENTACION_CHOICES = [
        ("NO_IMPLEMENTADO", "No implementado"),
        ("PARCIAL", "Implementación parcial"),
        ("IMPLEMENTADO", "Implementado"),
        ("NO_APLICA", "No aplica"),
    ]

    codigo = models.CharField(max_length=10, unique=True, help_text="Ej. 5.1, 8.16")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    nombre = models.CharField(max_length=255)
    aplicable = models.BooleanField(default=True, help_text="Según la Declaración de Aplicabilidad (SoA)")
    justificacion_aplicabilidad = models.TextField(
        blank=True, help_text="Por qué aplica o no aplica a SUIIN/CRIC")
    estado_implementacion = models.CharField(
        max_length=20, choices=ESTADO_IMPLEMENTACION_CHOICES, default="NO_IMPLEMENTADO")
    politica_referencia = models.CharField(
        max_length=100, blank=True, help_text="Ej. POL-SI-012 (referencia libre al catálogo de políticas)")
    observaciones = models.TextField(blank=True)

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Control ISO 27001 (Anexo A)"
        verbose_name_plural = "Controles ISO 27001 (Anexo A)"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    @property
    def numero_orden(self):
        """Para ordenar 5.2 antes de 5.10 (orden alfabético natural falla con estos códigos)."""
        try:
            return tuple(int(p) for p in self.codigo.split("."))
        except ValueError:
            return (99,)


NIVEL_RIESGO_CHOICES = [
    ("CRITICO", "Crítico"),
    ("ALTO", "Alto"),
    ("MEDIO", "Medio"),
    ("BAJO", "Bajo"),
    ("SIN_DATO", "—"),
]

ESPACIO_ORGANIZACION = "organizacion"

CLASIFICACION_SI_CHOICES = [
    ("ALTAMENTE_CONFIDENCIAL", "Altamente Confidencial"),
    ("CONFIDENCIAL", "Confidencial"),
    ("PUBLICO", "Público"),
    ("DESCONOCIDA", "Desconocida"),
]

COBERTURA_CHOICES = [
    ("COMPLETA", "Completa (Nmap+OV)"),
    ("PARCIAL", "Parcial (solo Nmap)"),
    ("SIN_COBERTURA", "Sin cobertura"),
]

ESTADO_COMPROMISO_CHOICES = [
    ("COMPROMETIDO", "Comprometido"),
    ("NO_COMPROMETIDO", "No comprometido"),
    ("NO_EVALUADO", "No evaluado"),
]


def calcular_nivel(score: int) -> str:
    """Escala ISO/IEC 27005 usada en la matriz original: Score = Prob(1-5) x Impacto(1-5)."""
    if score is None:
        return "SIN_DATO"
    if score >= 20:
        return "CRITICO"
    if score >= 12:
        return "ALTO"
    if score >= 6:
        return "MEDIO"
    if score >= 1:
        return "BAJO"
    return "SIN_DATO"


ESTADOS_CERRADOS = ("CERRADO", "FALSO_POSITIVO", "ACEPTADO")


def _dias_restantes(fecha):
    """Días restantes hasta la fecha (negativo si ya venció). None si no hay fecha."""
    if fecha is None:
        return None
    import datetime as _dt
    return (fecha - _dt.date.today()).days


class CampanaRedTeam(TimeStampedModel):
    """Hoja 07_Red_Team_Detalle — una campaña de Red Team por host objetivo."""
    espacio_codigo = models.CharField(
        max_length=60, default=ESPACIO_ORGANIZACION, db_index=True,
        help_text="Espacio de datos del usuario (aislamiento multi-tenant ligero).",
    )
    nombre = models.CharField(max_length=100, help_text="Ej. SUIIN-CENSO")
    host_ip = models.GenericIPAddressField(protocol="IPv4")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado_compromiso = models.CharField(max_length=20, choices=ESTADO_COMPROMISO_CHOICES,
                                          default="NO_EVALUADO")
    estado_ufw = models.CharField(max_length=255, blank=True,
                                   help_text="Ej. DESHABILITADO (ataque exitoso)")
    uptime_sin_reinicio = models.CharField(max_length=255, blank=True)
    agentes_implantados = models.TextField(blank=True)
    servidores_c2 = models.TextField(blank=True)
    datos_exfiltrados = models.TextField(blank=True)
    riesgo_maximo_correlacionado = models.CharField(max_length=255, blank=True)
    riesgos_criticos = models.PositiveIntegerField(
        default=0, help_text="Foto AL MOMENTO DE LA CAMPAÑA — no se actualiza sola después. "
                              "Ver riesgos_actuales_por_nivel para el conteo en vivo.")
    riesgos_altos = models.PositiveIntegerField(default=0)
    riesgos_medios = models.PositiveIntegerField(default=0)
    riesgos_bajos = models.PositiveIntegerField(default=0)
    puertos_no_documentados = models.TextField(blank=True)
    tecnicas_mitre_count = models.PositiveIntegerField(null=True, blank=True)
    tecnicas_mitre_detalle = models.TextField(blank=True)

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Campaña Red Team"
        verbose_name_plural = "Campañas Red Team"
        ordering = ["fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["espacio_codigo", "nombre"],
                name="uniq_campana_espacio_nombre",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.host_ip})"

    @property
    def riesgos_actuales_por_nivel(self):
        """
        Conteo EN VIVO de vulnerabilidades + riesgos por activo de nivel definido,
        entre los activos vinculados a esta campaña — a diferencia de
        riesgos_criticos/altos/medios/bajos (que son la foto congelada del momento
        de la campaña, importada una sola vez del Excel y nunca más actualizada).
        Puede diferir mucho de esos campos si ha pasado tiempo desde la campaña y
        se han registrado hallazgos nuevos, o cerrado los existentes.
        """
        activos = self.activos.all()
        niveles = list(
            Vulnerabilidad.objects.filter(activo__in=activos)
            .exclude(nivel_riesgo="SIN_DATO").values_list("nivel_riesgo", flat=True)
        ) + list(
            RiesgoActivo.objects.filter(activo__in=activos)
            .exclude(nivel_riesgo="SIN_DATO").values_list("nivel_riesgo", flat=True)
        )
        conteo = {"CRITICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0}
        for n in niveles:
            if n in conteo:
                conteo[n] += 1
        return conteo


class Activo(TimeStampedModel):
    """Hoja 01_Resumen_Triple (+ campos de 04_Activos_Sin_Cobertura)."""
    espacio_codigo = models.CharField(
        max_length=60, default=ESPACIO_ORGANIZACION, db_index=True,
        help_text="Espacio de datos del usuario (aislamiento multi-tenant ligero).",
    )
    id_activo = models.CharField(max_length=20, help_text="Ej. RED-012, SI-06")
    inventario_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="PK del activo correspondiente en la Plataforma SUIIN (Inventario) — "
                   "null si aún no está vinculado. Ver comando sincronizar_activos_inventario.")
    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=150, blank=True)
    ip_principal = models.CharField(max_length=100, blank=True,
                                     help_text="Puede ser IP única, lista o segmento CIDR")
    valor = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        help_text="Valor del activo, escala 1-12 (Matriz SUIIN-SGSI-INV-001)")
    riesgo_matriz = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES, default="SIN_DATO")
    clasificacion_si = models.CharField(max_length=30, choices=CLASIFICACION_SI_CHOICES,
                                         default="DESCONOCIDA")
    vlan = models.CharField(max_length=50, blank=True)

    # Cobertura de escaneo
    en_nmap = models.BooleanField(default=False)
    puertos_abiertos_resumen = models.CharField(max_length=100, blank=True, help_text="Ej. '5 puertos'")
    cobertura = models.CharField(max_length=15, choices=COBERTURA_CHOICES, default="SIN_COBERTURA")
    observacion_critica = models.TextField(blank=True)

    # Red Team
    afectado_red_team = models.BooleanField(default=False)
    campana_red_team = models.ForeignKey(CampanaRedTeam, null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name="activos")
    estado_ufw_activo = models.CharField(max_length=255, blank=True)
    exfiltracion_confirmada = models.TextField(blank=True)
    accion_inmediata_red_team = models.TextField(blank=True)

    # Contexto adicional (hoja 04)
    mitre_attck = models.CharField(max_length=255, blank=True)
    accion_recomendada = models.TextField(blank=True)
    estado_operativo = models.CharField(max_length=50, blank=True,
                                         help_text="Ej. 'No operación' (hoja 06_SI_vs_Vulns_Servidor)")

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["id_activo"]
        constraints = [
            models.UniqueConstraint(
                fields=["espacio_codigo", "id_activo"],
                name="uniq_activo_espacio_id",
            ),
            models.UniqueConstraint(
                fields=["espacio_codigo", "inventario_id"],
                name="uniq_activo_espacio_inventario",
                condition=models.Q(inventario_id__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.id_activo} — {self.nombre}"

    @property
    def total_vulnerabilidades(self):
        return self.vulnerabilidades.count()

    @property
    def vulnerabilidades_criticas(self):
        return self.vulnerabilidades.filter(severidad_ov="CRITICAL").count()


class PuertoServicio(TimeStampedModel):
    """Hoja 03_Inventario_Nmap_por_Activo — puertos/servicios detectados por Nmap."""
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="puertos")
    ip = models.CharField(max_length=100, blank=True)
    sistema_operativo = models.CharField(max_length=150, blank=True)
    puerto = models.PositiveIntegerField(null=True, blank=True)
    protocolo = models.CharField(max_length=10, blank=True)
    servicio = models.CharField(max_length=150, blank=True)
    producto_version = models.CharField(max_length=255, blank=True)
    observacion = models.CharField(max_length=255, blank=True)
    hallazgo_red_team = models.TextField(blank=True)

    class Meta:
        verbose_name = "Puerto / Servicio"
        verbose_name_plural = "Puertos / Servicios"
        ordering = ["activo", "puerto"]

    def __str__(self):
        return f"{self.activo.id_activo}:{self.puerto}/{self.protocolo} ({self.servicio})"


SEVERIDAD_OV_CHOICES = [
    ("CRITICAL", "Critical"),
    ("HIGH", "High"),
    ("MEDIUM", "Medium"),
    ("LOW", "Low"),
    ("LOG", "Log"),
]

TRATAMIENTO_CHOICES = [
    ("MITIGAR_INMEDIATO", "Mitigar (inmediato)"),
    ("MITIGAR_URGENTE", "Mitigar (urgente)"),
    ("MITIGAR_PLANIFICADO", "Mitigar (planificado)"),
    ("ACEPTAR", "Aceptar"),
    ("TRANSFERIR", "Transferir"),
    ("ELIMINAR", "Eliminar"),
]

ESTADO_TRATAMIENTO_CHOICES = [
    ("PENDIENTE", "Pendiente"),
    ("EN_PROGRESO", "En progreso"),
    ("CERRADO", "Cerrado"),
    ("FALSO_POSITIVO", "Falso positivo"),
    ("ACEPTADO", "Aceptado"),
]


class Vulnerabilidad(TimeStampedModel):
    """
    Fusiona la hoja 02_Vulns_por_Activo (hallazgo técnico OpenVAS) con la hoja
    09_Matriz_Riesgo_Detalle (mismo hallazgo + score de riesgo + tratamiento),
    que en el Excel original son la misma fila duplicada en dos vistas.
    """
    id_riesgo = models.CharField(max_length=20, blank=True, help_text="Ej. RH-003")
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="vulnerabilidades")
    ip = models.CharField(max_length=100, blank=True)

    # Hallazgo técnico (OpenVAS)
    severidad_ov = models.CharField(max_length=10, choices=SEVERIDAD_OV_CHOICES, blank=True)
    cvss = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    nombre_vulnerabilidad = models.CharField(max_length=500)
    cves = models.CharField(max_length=500, blank=True, help_text="Lista separada por comas")
    descripcion_tecnica = models.TextField(blank=True)
    solucion_recomendada = models.TextField(blank=True)

    # Riesgo (ISO/IEC 27005 Prob x Impacto)
    probabilidad = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    impacto = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    score = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    nivel_riesgo = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES,
                                     default="SIN_DATO", editable=False)

    # Correlación / tratamiento
    evidencia_red_team = models.TextField(blank=True, default="Sin evidencia directa de explotación")
    explotado_confirmado_rt = models.CharField(max_length=255, blank=True, default="—")
    tratamiento = models.CharField(max_length=25, choices=TRATAMIENTO_CHOICES, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_TRATAMIENTO_CHOICES, default="PENDIENTE")

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Vulnerabilidad"
        verbose_name_plural = "Vulnerabilidades"
        ordering = ["-score", "activo"]
        indexes = [
            models.Index(fields=["severidad_ov"]),
            models.Index(fields=["nivel_riesgo"]),
        ]

    def save(self, *args, **kwargs):
        if self.probabilidad and self.impacto:
            self.score = self.probabilidad * self.impacto
            self.nivel_riesgo = calcular_nivel(self.score)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_riesgo or '—'} · {self.activo.id_activo} · {self.nombre_vulnerabilidad[:60]}"


class RiesgoActivo(TimeStampedModel):
    """Hoja 08_Matriz_Riesgo_por_Activo — riesgo agregado a nivel de activo (no por hallazgo)."""
    id_riesgo = models.CharField(max_length=20, unique=True, help_text="Ej. RA-005")
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="riesgos_agregados")
    clasificacion = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES, default="SIN_DATO")
    probabilidad = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    impacto = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    score = models.PositiveSmallIntegerField(editable=False)
    nivel_riesgo = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES, editable=False)
    tratamiento = models.CharField(max_length=25, choices=TRATAMIENTO_CHOICES, blank=True)
    responsable_sugerido = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_TRATAMIENTO_CHOICES, default="PENDIENTE")
    fecha_objetivo = models.DateField(null=True, blank=True)
    justificacion = models.TextField(blank=True)
    controles_accion = models.TextField(blank=True)

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Riesgo por Activo"
        verbose_name_plural = "Riesgos por Activo"
        ordering = ["-score"]

    def save(self, *args, **kwargs):
        self.score = self.probabilidad * self.impacto
        self.nivel_riesgo = calcular_nivel(self.score)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_riesgo} · {self.activo.id_activo} · {self.get_nivel_riesgo_display()}"

    @property
    def dias_para_vencer(self):
        return _dias_restantes(self.fecha_objetivo)

    @property
    def esta_vencido(self):
        dias = self.dias_para_vencer
        return dias is not None and dias < 0 and self.estado not in ESTADOS_CERRADOS

    @property
    def por_vencer(self):
        """Vence en los próximos 7 días y no está cerrado."""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 7 and self.estado not in ESTADOS_CERRADOS


class RiesgoContextual(TimeStampedModel):
    """
    Hoja 10_Matriz de riesgos de segurid — riesgos RC-01..RC-07 del contexto organizacional
    (ISO 27001 cláusula 4.1/4.2). No detectables por escáneres técnicos; escala propia 1-5.
    """
    espacio_codigo = models.CharField(
        max_length=60, default=ESPACIO_ORGANIZACION, db_index=True,
    )
    id_riesgo_contextual = models.CharField(max_length=10, help_text="Ej. RC-03")
    escenario_amenaza = models.CharField(max_length=500)
    actor_amenaza = models.TextField(blank=True)
    activos_afectados_texto = models.TextField(blank=True)
    activos_relacionados = models.ManyToManyField(Activo, blank=True, related_name="riesgos_contextuales")
    clasificacion_si = models.CharField(max_length=30, choices=CLASIFICACION_SI_CHOICES,
                                         default="DESCONOCIDA")
    datos_especificos_riesgo = models.TextField(blank=True)
    probabilidad = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    impacto = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    score = models.PositiveSmallIntegerField(editable=False)
    nivel_riesgo = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES, editable=False)
    marco_referencia = models.TextField(blank=True, help_text="ISO 27001 / DNUDPI / Convenio 169 OIT, etc.")
    descripcion_escenario = models.TextField(blank=True)
    impacto_cia_misional = models.TextField(blank=True)
    controles_iso = models.TextField(blank=True, help_text="Texto libre heredado del Excel original")
    controles_iso_vinculados = models.ManyToManyField(
        ControlISO27001, blank=True, related_name="riesgos_contextuales",
        help_text="Vínculo estructurado al catálogo de controles (usar en vez del texto libre para nuevos registros)")
    accion_mitigacion = models.TextField(blank=True)
    plazo = models.CharField(
        max_length=255, blank=True,
        help_text="Texto libre heredado del Excel — puede contener varios subplazos relativos "
                   "(ej. '0–30 días protocolo, 0–15 días lámina vidrio'). Use fecha_limite para "
                   "el plazo más urgente de los mencionados, si quiere que entre en las alertas.")
    fecha_limite = models.DateField(
        null=True, blank=True,
        help_text="Fecha límite absoluta (opcional) del ítem más urgente de 'plazo'. Habilita "
                   "las alertas de vencimiento para este riesgo contextual.")
    responsable = models.CharField(max_length=255, blank=True)
    ley_marco_legal = models.TextField(blank=True)
    estado_actual = models.CharField(
        max_length=50, blank=True,
        help_text="Texto libre heredado del Excel original (ej. 'SIN CONTROL') — use 'estado' "
                   "para el campo estructurado que alimenta las alertas de vencimiento.")
    estado = models.CharField(max_length=20, choices=ESTADO_TRATAMIENTO_CHOICES, default="PENDIENTE")
    observaciones_correlacion = models.TextField(blank=True)

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Riesgo Contextual"
        verbose_name_plural = "Riesgos Contextuales"
        ordering = ["id_riesgo_contextual"]
        constraints = [
            models.UniqueConstraint(
                fields=["espacio_codigo", "id_riesgo_contextual"],
                name="uniq_rc_espacio_codigo",
            ),
        ]

    def save(self, *args, **kwargs):
        self.score = self.probabilidad * self.impacto
        self.nivel_riesgo = calcular_nivel(self.score)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_riesgo_contextual} · {self.escenario_amenaza[:60]}"

    @property
    def dias_para_vencer(self):
        return _dias_restantes(self.fecha_limite)

    @property
    def esta_vencido(self):
        dias = self.dias_para_vencer
        return dias is not None and dias < 0 and self.estado not in ESTADOS_CERRADOS

    @property
    def por_vencer(self):
        """Vence en los próximos 7 días y no está cerrado."""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 7 and self.estado not in ESTADOS_CERRADOS


ESTADO_PLAN_CHOICES = [
    ("ACTIVO", "Activo"),
    ("ARCHIVADO", "Archivado"),
    ("CERRADO", "Cerrado"),
]


class PlanTratamientoRiesgos(TimeStampedModel):
    """
    Portada del PTR (Plan de Tratamiento de Riesgos). Un PTR se emite por host/campaña
    comprometida (ej. SUIIN-SGSI-PTR-001 para CENSO), siguiendo la codificación institucional.
    """
    espacio_codigo = models.CharField(
        max_length=60, default=ESPACIO_ORGANIZACION, db_index=True,
    )
    referencia = models.CharField(max_length=50, help_text="Ej. SUIIN-SGSI-PTR-001 v1.0")
    titulo = models.CharField(max_length=255)
    campana_red_team = models.ForeignKey(CampanaRedTeam, on_delete=models.PROTECT,
                                          related_name="planes_tratamiento")
    clasificacion_documento = models.CharField(max_length=100,
                                                default="CONFIDENCIAL — Uso Interno Restringido")
    fecha_emision = models.DateField()
    periodo_campana_inicio = models.DateField(null=True, blank=True)
    periodo_campana_fin = models.DateField(null=True, blank=True)
    herramientas = models.CharField(max_length=500, blank=True,
                                     help_text="Ej. MITRE CALDERA · OpenVAS · OWASP ZAP · Nuclei · NMAP")
    estado_plan = models.CharField(max_length=20, choices=ESTADO_PLAN_CHOICES, default="ACTIVO",
                                   help_text="Planes archivados o cerrados quedan fuera del selector "
                                             "operativo pero conservan historial y evidencia.")

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Plan de Tratamiento de Riesgos"
        verbose_name_plural = "Planes de Tratamiento de Riesgos"
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(
                fields=["espacio_codigo", "referencia"],
                name="uniq_ptr_espacio_referencia",
            ),
        ]

    def __str__(self):
        return f"{self.referencia} — {self.titulo}"

    @property
    def porcentaje_avance_global(self):
        acciones = self.acciones.all()
        if not acciones:
            return 0
        # ESTADOS_CERRADOS (definido arriba, mismo criterio que usan las alertas de
        # vencimiento) — antes solo contaba CERRADO/FALSO_POSITIVO y dejaba fuera
        # ACEPTADO, así que un riesgo formalmente aceptado (una disposición válida,
        # no "todavía pendiente") no sumaba al avance del plan.
        cerradas = acciones.filter(estado__in=ESTADOS_CERRADOS).count()
        return round((cerradas / acciones.count()) * 100)


FASE_CHOICES = [
    ("FASE_1", "Fase 1 — Contención inmediata"),
    ("FASE_2", "Fase 2 — Erradicación"),
    ("FASE_3", "Fase 3 — Recuperación"),
    ("FASE_4", "Fase 4 — Lecciones aprendidas"),
]

OPCION_TRATAMIENTO_CHOICES = [
    ("MITIGAR", "Mitigar"),
    ("MITIGAR_ELIMINAR", "Mitigar / Eliminar"),
    ("ACEPTAR", "Aceptar"),
    ("TRANSFERIR", "Transferir"),
    ("ELIMINAR", "Eliminar"),
]


class AccionTratamiento(TimeStampedModel):
    """
    Consolida las hojas 'Matriz PTR', 'Plan de Acción' y 'Seguimiento' del archivo PTR,
    que en el Excel original describen el MISMO riesgo R-XX en tres momentos (definición,
    ejecución, seguimiento). Aquí es una sola fila con estado de ciclo de vida completo.
    """
    plan = models.ForeignKey(PlanTratamientoRiesgos, on_delete=models.CASCADE, related_name="acciones")
    id_riesgo = models.CharField(max_length=10, help_text="Ej. R-04")
    descripcion_riesgo = models.TextField()

    # Trazabilidad: de qué hallazgo de la matriz nació esta acción (si nació de uno).
    # Ambos son opcionales y mutuamente excluyentes en la práctica — una acción puede
    # también crearse "desde cero" sin origen (ej. import de Excel legado, o un hallazgo
    # cualitativo que no corresponde a una fila puntual de la matriz).
    origen_vulnerabilidad = models.ForeignKey(
        Vulnerabilidad, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="acciones_generadas",
        help_text="Vulnerabilidad de la matriz que originó esta acción, si aplica")
    origen_riesgo_activo = models.ForeignKey(
        RiesgoActivo, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="acciones_generadas",
        help_text="Riesgo por activo de la matriz que originó esta acción, si aplica")
    origen_riesgo_contextual = models.ForeignKey(
        RiesgoContextual, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="acciones_generadas",
        help_text="Riesgo contextual (amenaza interna, legal, físico) que originó esta acción, "
                   "si aplica — antes solo Vulnerabilidad y RiesgoActivo tenían este vínculo; "
                   "los 7 riesgos contextuales quedaban fuera del ciclo hallazgo→acción→cierre "
                   "trazado, sin forma de saber qué acción atendía cuál riesgo contextual.")

    probabilidad = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    impacto = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    score = models.PositiveSmallIntegerField(editable=False)
    nivel_riesgo = models.CharField(max_length=15, choices=NIVEL_RIESGO_CHOICES, editable=False)
    fuente = models.CharField(max_length=255, blank=True, help_text="Ej. CALDERA – Thief")
    tecnica_mitre_cwe = models.CharField(max_length=255, blank=True)

    acciones_tratamiento = models.TextField(help_text="Pasos técnicos a ejecutar")
    kpi_criterio_cierre = models.TextField(blank=True)
    opcion_tratamiento = models.CharField(max_length=20, choices=OPCION_TRATAMIENTO_CHOICES,
                                           default="MITIGAR")
    responsable = models.CharField(max_length=150, default="Administrador")
    fase = models.CharField(max_length=10, choices=FASE_CHOICES, default="FASE_1")
    plazo = models.CharField(max_length=100, blank=True, help_text="Ej. '0–4 h', '24–48 h'")
    herramienta_comando = models.TextField(blank=True)
    control_iso27001 = models.CharField(max_length=255, blank=True, help_text="Texto libre heredado del Excel original")
    controles_iso_vinculados = models.ManyToManyField(
        ControlISO27001, blank=True, related_name="acciones_tratamiento",
        help_text="Vínculo estructurado al catálogo de controles (usar en vez del texto libre para nuevos registros)")

    estado = models.CharField(max_length=20, choices=ESTADO_TRATAMIENTO_CHOICES, default="PENDIENTE")
    fecha_limite_texto = models.CharField(max_length=100, blank=True,
                                           help_text="Ej. '0–4 h post-incidente' (plazo relativo, no fecha absoluta)")
    fecha_limite = models.DateField(
        null=True, blank=True,
        help_text="Fecha límite absoluta (opcional). Para acciones importadas del PTR original "
                   "el plazo suele ser relativo — use fecha_limite_texto en ese caso; para acciones "
                   "nuevas creadas desde la app, prefiera esta fecha real para habilitar alertas.")
    fecha_cierre_real = models.DateField(null=True, blank=True)
    porcentaje_avance = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    historial = HistoricalRecords()

    class Meta:
        verbose_name = "Acción de Tratamiento"
        verbose_name_plural = "Acciones de Tratamiento"
        ordering = ["plan", "fase", "id_riesgo"]
        unique_together = [("plan", "id_riesgo")]

    def save(self, *args, **kwargs):
        self.score = self.probabilidad * self.impacto
        self.nivel_riesgo = calcular_nivel(self.score)
        if self.estado in ("CERRADO", "FALSO_POSITIVO"):
            self.porcentaje_avance = 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plan.referencia} · {self.id_riesgo} · {self.get_estado_display()}"

    @property
    def dias_para_vencer(self):
        return _dias_restantes(self.fecha_limite)

    @property
    def esta_vencida(self):
        dias = self.dias_para_vencer
        return dias is not None and dias < 0 and self.estado not in ESTADOS_CERRADOS

    @property
    def por_vencer(self):
        """Vence en los próximos 7 días y no está cerrada."""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 7 and self.estado not in ESTADOS_CERRADOS


# ---------------------------------------------------------------------------
# Evidencia — adjuntos genéricos
# ---------------------------------------------------------------------------
def ruta_evidencia(instance, filename):
    """evidencias/<modelo>/<id>/<archivo>. Django ya evita colisiones de nombre
    dentro de la misma carpeta (agrega un sufijo aleatorio si hace falta)."""
    modelo = instance.content_type.model if instance.content_type_id else "sin-modelo"
    return f"evidencias/{modelo}/{instance.object_id or 'nuevo'}/{filename}"


EXTENSIONES_PERMITIDAS = {
    ".jpg": "IMAGEN", ".jpeg": "IMAGEN", ".png": "IMAGEN", ".gif": "IMAGEN", ".webp": "IMAGEN",
    ".pdf": "PDF",
    ".doc": "DOCUMENTO", ".docx": "DOCUMENTO", ".xls": "DOCUMENTO", ".xlsx": "DOCUMENTO",
}
TAMANO_MAXIMO_MB = 10


def validar_extension_evidencia(archivo):
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS))
        raise ValidationError(f"Tipo de archivo no permitido ({ext or 'sin extensión'}). Use: {permitidas}.")


def validar_tamano_evidencia(archivo):
    limite = TAMANO_MAXIMO_MB * 1024 * 1024
    if archivo.size > limite:
        raise ValidationError(f"El archivo pesa {archivo.size / 1024 / 1024:.1f} MB — el máximo es {TAMANO_MAXIMO_MB} MB.")


# Modelos que pueden recibir evidencia adjunta — whitelist explícita para no
# permitir adjuntar archivos a cualquier tabla del sistema (ej. usuarios, tokens).
MODELOS_CON_EVIDENCIA = [
    "activo", "vulnerabilidad", "riesgoactivo", "riesgocontextual",
    "acciontratamiento", "plantratamientoriesgos",
]


TIPO_ARCHIVO_CHOICES = [
    ("IMAGEN", "Imagen"), ("PDF", "PDF"), ("DOCUMENTO", "Documento"), ("OTRO", "Otro"),
]


class Evidencia(TimeStampedModel):
    """
    Adjunto genérico (foto, PDF, acta, reporte de escaneo) vinculado a cualquiera
    de los modelos en MODELOS_CON_EVIDENCIA, vía GenericForeignKey — evita repetir
    una tabla de archivos por cada entidad. Es lo que un auditor ISO 27001 suele
    pedir ver junto al riesgo o la acción de tratamiento: la prueba concreta.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    archivo = models.FileField(
        upload_to=ruta_evidencia,
        validators=[validar_extension_evidencia, validar_tamano_evidencia],
    )
    nombre_original = models.CharField(max_length=255, blank=True)
    tipo_archivo = models.CharField(max_length=15, blank=True, editable=False, choices=TIPO_ARCHIVO_CHOICES)
    tamano_bytes = models.PositiveIntegerField(default=0, editable=False)
    descripcion = models.CharField(max_length=500, blank=True, help_text="Qué muestra esta evidencia")
    subido_por = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="evidencias_subidas")

    class Meta:
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def save(self, *args, **kwargs):
        if self.archivo:
            ext = os.path.splitext(self.archivo.name)[1].lower()
            self.tipo_archivo = EXTENSIONES_PERMITIDAS.get(ext, "OTRO")
            if not self.nombre_original:
                self.nombre_original = os.path.basename(self.archivo.name)
            try:
                self.tamano_bytes = self.archivo.size
            except (ValueError, OSError):
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_original} → {self.content_type.model} #{self.object_id}"


# ---------------------------------------------------------------------------
# CatalogoValor — listas de valores parametrizables por el propio analista
# ---------------------------------------------------------------------------
CATEGORIA_CATALOGO_CHOICES = [
    ("TIPO_ACTIVO", "Tipo de activo"),
    ("RESPONSABLE_RIESGO", "Responsable sugerido (riesgo por activo)"),
    ("RESPONSABLE_ACCION", "Responsable (acción de tratamiento)"),
    ("FUENTE_HALLAZGO", "Fuente del hallazgo (acción de tratamiento)"),
    ("PLAZO_ACCION", "Plazo (acción de tratamiento)"),
    ("SOLUCION_VULN", "Solución recomendada (vulnerabilidad)"),
]


class CatalogoValor(TimeStampedModel):
    """
    Listas de valores reutilizables para los campos de texto libre más
    repetitivos del sistema (ej. 'Tipo de activo', 'Responsable sugerido') —
    a diferencia de un `choices=` fijo en el modelo, el propio analista puede
    agregar/desactivar valores desde la app sin necesitar un cambio de código.

    Los campos que consumen esto (Activo.tipo, RiesgoActivo.responsable_sugerido,
    etc.) SIGUEN siendo CharField de texto libre — el catálogo solo alimenta el
    combo del formulario con sugerencias; nunca bloquea escribir un valor nuevo
    que todavía no esté en la lista (ese valor nuevo se agrega solo al catálogo
    para la próxima vez, ver EvidenciaViewSet/CatalogoValorViewSet).

    No se modeló como campos de choices=() fijos a propósito: los valores
    reales (ej. "Líder de Módulo / Desarrollo", "24–48 h") son específicos de
    la operación de CRIC/SUIIN, no un catálogo universal que tenga sentido
    versionar en el código fuente del sistema.
    """
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CATALOGO_CHOICES)
    valor = models.TextField(help_text="Corto para catálogos como 'Tipo de activo'; puede ser un "
                                        "párrafo largo para 'Solución recomendada' (texto de OpenVAS).")
    activo = models.BooleanField(
        default=True, help_text="Los valores desactivados dejan de sugerirse en el "
                                 "formulario, pero los registros que ya los usan no cambian.")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Valor de catálogo"
        verbose_name_plural = "Valores de catálogo"
        unique_together = ["categoria", "valor"]
        ordering = ["categoria", "orden", "valor"]

    def __str__(self):
        return f"{self.get_categoria_display()}: {self.valor}"


# ---------------------------------------------------------------------------
# TecnicaMitre — espejo local del catálogo MITRE ATT&CK del Inventario
# ---------------------------------------------------------------------------
TIPO_TECNICA_MITRE_CHOICES = [
    ("TA", "Táctica"), ("TE", "Técnica"), ("ST", "Subtécnica"),
]


class TecnicaMitre(TimeStampedModel):
    """
    Espejo local, de solo lectura desde la perspectiva de riesgos, del
    catálogo MITRE ATT&CK que ya mantiene el Inventario (`AmenazaMITRE`,
    712 entradas reales: 15 tácticas, 222 técnicas, 475 subtécnicas). Se
    sincroniza con `sincronizar_tecnicas_mitre` — mismo espíritu que
    sincronizar_activos_inventario, pero sin el mecanismo de protección contra
    ediciones manuales: es catálogo de referencia externo (viene de MITRE, vía
    el Inventario), no algo que el analista edite campo a campo aquí.

    Los campos que lo consumen (Activo.mitre_attck,
    AccionTratamiento.tecnica_mitre_cwe) SIGUEN siendo texto libre — este
    catálogo solo alimenta el buscador/selector del formulario, con el mismo
    principio que CatalogoValor: sugiere, nunca bloquea escribir algo que no
    esté acá (ej. un código CWE, que es un catálogo distinto por completo).
    """
    codigo = models.CharField(max_length=20, unique=True, help_text="Ej. T1190, TA0001, T1055.001")
    nombre = models.CharField(max_length=255, blank=True)
    tipo = models.CharField(max_length=2, choices=TIPO_TECNICA_MITRE_CHOICES, blank=True)
    tacticas = models.CharField(max_length=300, blank=True)
    codigo_padre = models.CharField(max_length=20, blank=True)
    url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Técnica MITRE ATT&CK"
        verbose_name_plural = "Técnicas MITRE ATT&CK"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}" if self.nombre else self.codigo

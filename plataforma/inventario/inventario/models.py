"""
Modelo de datos - Sistema de Inventario de Activos SGSI SUIIN
Documento base: SUIIN-SGSI-INV-001
Alineado a ISO/IEC 27001:2022 y ISO/IEC 27002:2022 (Camino del SUIIN)

v2 - Incorpora gestion CRUD, bitacora de cambios (django-simple-history)
     y campos ampliados de gobernanza, ciclo de vida, vulnerabilidades,
     continuidad y trazabilidad documental.
"""
from django.db import models
from simple_history.models import HistoricalRecords


class Zona(models.Model):
    nombre = models.CharField(max_length=120, unique=True)

    class Meta:
        verbose_name = "Zona de red"
        verbose_name_plural = "Zonas de red"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class VLAN(models.Model):
    etiqueta = models.CharField(max_length=60, unique=True)

    class Meta:
        verbose_name = "VLAN"
        verbose_name_plural = "VLANs"
        ordering = ["etiqueta"]

    def __str__(self):
        return self.etiqueta


class AmenazaMITRE(models.Model):
    class Tipo(models.TextChoices):
        TACTICA = "TA", "Tactica"
        TECNICA = "TE", "Tecnica"
        SUBTECNICA = "ST", "Subtecnica"

    codigo = models.CharField(max_length=20, unique=True, help_text="Ej: T1486, TA0040")
    nombre = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=2, choices=Tipo.choices, blank=True)
    tacticas = models.CharField("Tacticas asociadas", max_length=300, blank=True)
    plataformas = models.CharField(max_length=300, blank=True)
    codigo_padre = models.CharField("Tecnica padre", max_length=20, blank=True)
    url = models.URLField(blank=True)
    version = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Amenaza MITRE ATT&CK"
        verbose_name_plural = "Amenazas MITRE ATT&CK"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} {self.nombre or self.descripcion[:40]}".strip()


class ControlISO(models.Model):
    codigo = models.CharField(max_length=30, unique=True, help_text="Ej: 8.13, POL-SI-009")
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Control ISO / Politica"
        verbose_name_plural = "Controles ISO / Politicas"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} {self.descripcion}".strip()


class RolMCA(models.Model):
    sigla = models.CharField(max_length=10, unique=True, help_text="Ej: CM, DOS, DBA")
    nombre = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Rol MCA"
        verbose_name_plural = "Roles MCA"
        ordering = ["sigla"]

    def __str__(self):
        return self.sigla


class ClaseActivo(models.Model):
    """Catálogo configurable de clases de activo (INFRA, SIST, EQUI, …)."""

    class ModeloDetalle(models.TextChoices):
        INFRAESTRUCTURA = "infraestructura", "Infraestructura de red"
        SISTEMA = "sistema", "Sistema de información"
        EQUIPO = "equipo", "Equipo de cómputo"
        GENERICO = "generico", "Campos libres (JSON)"
        NINGUNO = "ninguno", "Solo campos comunes"

    codigo = models.CharField(max_length=6, unique=True, help_text="Ej: INFRA, SERV")
    nombre = models.CharField(max_length=120)
    prefijo_id = models.CharField(max_length=6, help_text="Prefijo del ID (RED, SIS, PC…)")
    color = models.CharField(max_length=7, default="#6b7280")
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)
    modelo_detalle = models.CharField(
        max_length=20, choices=ModeloDetalle.choices, default=ModeloDetalle.NINGUNO)
    detalle_schema = models.JSONField(
        blank=True, default=dict,
        help_text="Esquema opcional de campos para clases genéricas.")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Clase de activo"
        verbose_name_plural = "Clases de activo"
        ordering = ["orden", "codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class Activo(models.Model):
    class Clasificacion(models.TextChoices):
        ALTAMENTE = "ALTA", "Altamente Confidencial"
        CONFIDENCIAL = "CONF", "Confidencial"
        INTERNO = "INT", "Uso Interno"
        PUBLICO = "PUB", "Publico"

    class NivelCID(models.IntegerChoices):
        NA = 0, "0 - N/A"
        BAJO = 1, "1 - Bajo"
        MEDIO = 2, "2 - Medio"
        ALTO = 3, "3 - Alto"
        CRITICO = 4, "4 - Critico"

    class NivelRiesgo(models.TextChoices):
        CRITICO = "CRIT", "Critico"
        ALTO = "ALTO", "Alto"
        MEDIO = "MED", "Medio"
        BAJO = "BAJO", "Bajo"
        SIN = "SIN", "Sin valorar"

    class Estado(models.TextChoices):
        ACTIVO = "ACT", "Activo"
        IMPLEMENTACION = "IMP", "En implementacion"
        INACTIVO = "INA", "Inactivo / No operacion"
        RETIRADO = "RET", "Retirado"

    class CicloVida(models.TextChoices):
        PLANEADO = "PLAN", "Planeado"
        PRODUCCION = "PROD", "En produccion"
        MANTENIMIENTO = "MANT", "En mantenimiento"
        RETIRADO = "RETI", "Retirado / Baja"

    id_activo = models.CharField("ID Activo", max_length=30, unique=True, blank=True)
    nombre = models.CharField("Nombre del activo", max_length=255)
    descripcion = models.TextField("Descripcion / Funcion", blank=True)
    clase = models.CharField(max_length=6, help_text="Código de ClaseActivo (catálogo dinámico)")

    clasificacion_si = models.CharField("Clasificacion SI", max_length=5,
                                        choices=Clasificacion.choices, blank=True)
    confidencialidad = models.IntegerField(choices=NivelCID.choices, null=True, blank=True)
    integridad = models.IntegerField(choices=NivelCID.choices, null=True, blank=True)
    disponibilidad = models.IntegerField(choices=NivelCID.choices, null=True, blank=True)
    valor = models.IntegerField("Valor (C+I+D)", null=True, blank=True)
    probabilidad = models.IntegerField(
        "Probabilidad de amenaza (1-5)", null=True, blank=True,
        help_text="1=Muy baja ... 5=Muy alta. Usada por el motor de riesgos.")
    nivel_riesgo = models.CharField(max_length=5, choices=NivelRiesgo.choices,
                                    default=NivelRiesgo.SIN, blank=True)

    estado = models.CharField(max_length=4, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_registro = models.DateField(null=True, blank=True)
    notas_seguridad = models.TextField("Notas de seguridad", blank=True)

    # --- v3: Ubicacion en centro de datos ---
    datacenter = models.ForeignKey(
        "Datacenter", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activos", verbose_name="Centro de datos")

    # --- v2: Gobernanza (ISO/IEC 27001 A.5.9) ---
    propietario = models.CharField("Propietario del activo", max_length=150, blank=True)
    custodio = models.CharField("Custodio / responsable operativo", max_length=150, blank=True)
    area_responsable = models.CharField("Area responsable", max_length=150, blank=True)

    # --- v2: Datos personales (Ley 1581/2012) ---
    procesa_datos_personales = models.BooleanField(
        "Procesa datos personales (Ley 1581/2012)", default=False)

    # --- v2: Continuidad (BCP/DRP) ---
    rto = models.CharField("RTO (objetivo de tiempo de recuperacion)", max_length=40, blank=True)
    rpo = models.CharField("RPO (objetivo de punto de recuperacion)", max_length=40, blank=True)

    # --- v2: Ciclo de vida ---
    ciclo_vida = models.CharField(max_length=4, choices=CicloVida.choices,
                                  default=CicloVida.PRODUCCION, blank=True)

    # --- v2: Trazabilidad documental y dependencias ---
    documentos_relacionados = models.TextField(
        "Documentos SGSI relacionados", blank=True,
        help_text="Codigos/enlaces: PTR-00X, ARD-00X, POL-SI-XXX, etc.")
    dependencias = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="dependientes",
        verbose_name="Depende de (activos)",
        help_text="Activos de los que este activo depende para operar.")

    detalle_extra = models.JSONField(
        "Detalle adicional (clases genéricas)", blank=True, default=dict)

    amenazas = models.ManyToManyField(AmenazaMITRE, blank=True, related_name="activos")
    controles = models.ManyToManyField(ControlISO, blank=True, related_name="activos")

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    # Bitacora de cambios (quien / cuando / que campo)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ["id_activo"]

    # Prefijo legacy retirado (Ola 2) — solo ClaseActivo.prefijo_id.

    def nombre_clase(self):
        """Etiqueta legible desde el catálogo dinámico."""
        cat = ClaseActivo.objects.filter(codigo=self.clase).first()
        if cat:
            return cat.nombre
        return self.clase

    def get_clase_display(self):
        """Compatibilidad DRF/admin — delega al catálogo dinámico."""
        return self.nombre_clase()

    @classmethod
    def siguiente_codigo(cls, clase):
        """Calcula el proximo codigo secuencial (ej. RED-023) para la clase."""
        import re
        cat = ClaseActivo.objects.filter(codigo=clase, activo=True).first()
        if not cat:
            raise ValueError(f"No hay ClaseActivo activa con código «{clase}».")
        pref = cat.prefijo_id
        maximo = 0
        for c in cls.objects.filter(id_activo__startswith=pref + "-").values_list("id_activo", flat=True):
            m = re.search(r"-(\d+)$", c)
            if m:
                maximo = max(maximo, int(m.group(1)))
        return f"{pref}-{maximo + 1:03d}"

    def impacto(self):
        """Nivel de impacto 1-5 derivado de la valoracion C+I+D (0-12)."""
        if self.valor is None:
            return None
        v = self.valor
        if v <= 2:
            return 1
        if v <= 4:
            return 2
        if v <= 7:
            return 3
        if v <= 10:
            return 4
        return 5

    def probabilidad_efectiva(self):
        """Probabilidad 1-5: la registrada, o una estimacion segun exposicion."""
        if self.probabilidad:
            return self.probabilidad
        # Estimacion por hallazgos abiertos si es infraestructura
        inf = getattr(self, "infraestructura", None)
        if inf and inf.hallazgos_abiertos is not None:
            h = inf.hallazgos_abiertos
            return 5 if h > 5 else 4 if h > 0 else 2
        return 3  # valor neutro por defecto

    def riesgo_valor(self):
        """Riesgo inherente 1-25 = probabilidad x impacto."""
        imp = self.impacto()
        if imp is None:
            return None
        return self.probabilidad_efectiva() * imp

    def riesgo_nivel_calculado(self):
        """Convierte el riesgo 1-25 en nivel (BAJO/MED/ALTO/CRIT)."""
        r = self.riesgo_valor()
        if r is None:
            return "SIN"
        if r <= 5:
            return "BAJO"
        if r <= 10:
            return "MED"
        if r <= 15:
            return "ALTO"
        return "CRIT"

    def save(self, *args, **kwargs):
        # Autogenerar el ID segun la clase si no se especifico (por orden de creacion)
        if not self.id_activo:
            self.id_activo = Activo.siguiente_codigo(self.clase)
        comps = [self.confidencialidad, self.integridad, self.disponibilidad]
        if all(c is not None for c in comps):
            self.valor = sum(comps)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_activo} - {self.nombre}"


class ActivoInfraestructura(models.Model):
    activo = models.OneToOneField(Activo, on_delete=models.CASCADE,
                                  related_name="infraestructura", primary_key=True)
    tipo = models.CharField(max_length=60, blank=True)
    subtipo = models.CharField("Subtipo / Categoria", max_length=120, blank=True)
    zona = models.ForeignKey(Zona, on_delete=models.SET_NULL, null=True, blank=True)
    ip_segmento = models.CharField("IP / Segmento", max_length=120, blank=True)
    vlan = models.ForeignKey(VLAN, on_delete=models.SET_NULL, null=True, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    serial_placa = models.CharField("Serial / Placa", max_length=120, blank=True)

    # --- v2: Ciclo de vida del hardware ---
    fabricante_proveedor = models.CharField("Fabricante / Proveedor", max_length=150, blank=True)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    fin_garantia = models.DateField("Fin de garantia", null=True, blank=True)
    fin_soporte_eol = models.DateField("Fin de soporte (EOL)", null=True, blank=True)

    # --- v2: Gestion de vulnerabilidades ---
    version_so_firmware = models.CharField("Version SO / Firmware", max_length=120, blank=True)
    fecha_ultimo_escaneo = models.DateField("Fecha ultimo escaneo (OpenVAS)", null=True, blank=True)
    hallazgos_abiertos = models.IntegerField("Hallazgos de vulnerabilidad abiertos",
                                             null=True, blank=True)

    # --- v3: Ubicacion fisica granular en el rack ---
    rack_fk = models.ForeignKey(
        "Rack", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="equipos", verbose_name="Rack (catálogo)")
    unidad_inicio = models.PositiveSmallIntegerField("U inicio", null=True, blank=True)
    unidad_fin = models.PositiveSmallIntegerField("U fin", null=True, blank=True)
    rack = models.CharField("Rack (texto legacy)", max_length=40, blank=True)
    unidad_rack = models.CharField("Unidad de rack (U)", max_length=20, blank=True,
                                   help_text="Ej: U12-U14")

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Activo de infraestructura"
        verbose_name_plural = "Activos de infraestructura"

    def save(self, *args, **kwargs):
        if self.rack_fk_id:
            self.rack = self.rack_fk.codigo
            if self.unidad_inicio and self.unidad_fin:
                self.unidad_rack = f"U{self.unidad_inicio}-U{self.unidad_fin}"
            elif self.unidad_inicio:
                self.unidad_rack = f"U{self.unidad_inicio}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[INFRA] {self.activo.id_activo}"


class EquipoComputo(models.Model):
    """Equipo de cómputo de usuario final (escritorio, portátil, tablet).
    Complementa a ActivoInfraestructura (que cubre red/servidores/rack) con
    los datos propios de un equipo asignado a una persona: custodia,
    postura de seguridad del endpoint (ISO/IEC 27002:2022 — 8.1) y
    ciclo de vida de garantía."""

    class TipoEquipo(models.TextChoices):
        ESCRITORIO = "ESC", "Equipo de escritorio"
        PORTATIL = "PORT", "Portatil / Laptop"
        TODO_EN_UNO = "AIO", "Todo en uno (All-in-one)"
        TABLET = "TAB", "Tablet"
        OTRO = "OTRO", "Otro"

    activo = models.OneToOneField(Activo, on_delete=models.CASCADE,
                                  related_name="equipo", primary_key=True)
    tipo_equipo = models.CharField(max_length=4, choices=TipoEquipo.choices,
                                   default=TipoEquipo.ESCRITORIO)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    serial = models.CharField("Numero de serie", max_length=120, blank=True)
    mac_address = models.CharField("Direccion MAC", max_length=60, blank=True)

    # --- Custodia y ubicacion (ISO/IEC 27001 A.5.9 / A.7.9) ---
    usuario_asignado = models.CharField("Usuario asignado", max_length=150, blank=True)
    ubicacion_fisica = models.CharField("Ubicacion fisica / sede", max_length=150, blank=True)

    # --- Especificaciones ---
    sistema_operativo = models.CharField(max_length=100, blank=True)
    ram_gb = models.PositiveIntegerField("RAM (GB)", null=True, blank=True)
    almacenamiento = models.CharField("Almacenamiento", max_length=100, blank=True,
                                      help_text="Ej: 512GB SSD")

    # --- Postura de seguridad del endpoint (ISO/IEC 27002:2022 - 8.1, 8.7) ---
    antivirus_edr = models.CharField("Antivirus / EDR instalado", max_length=120, blank=True)
    cifrado_disco = models.BooleanField("Disco cifrado (BitLocker/LUKS)", default=False)
    unido_a_dominio = models.BooleanField("Unido al dominio / SSO corporativo", default=False)
    ultima_actualizacion_so = models.DateField("Ultima actualizacion del SO", null=True, blank=True)

    # --- Ciclo de vida del hardware ---
    fecha_adquisicion = models.DateField(null=True, blank=True)
    fin_garantia = models.DateField("Fin de garantia", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Equipo de computo"
        verbose_name_plural = "Equipos de computo"

    def __str__(self):
        return f"[EQUIPO] {self.activo.id_activo}"


class SistemaInformacion(models.Model):
    class EstadoOperativo(models.TextChoices):
        OPERACION = "OP", "En operacion"
        IMPLEMENTACION = "IMP", "En implementacion"
        NO_OPERACION = "NO", "No operacion"
        SIN_DATO = "SD", "Sin dato"

    class Prioridad(models.TextChoices):
        ALTA = "ALTA", "Alta - Inmediata"
        MEDIA = "MED", "Media - Proxima fase"
        BAJA = "BAJA", "Baja - Pendiente"
        SIN = "SIN", "Sin priorizar"

    activo = models.OneToOneField(Activo, on_delete=models.CASCADE,
                                  related_name="sistema", primary_key=True)
    estado_operativo = models.CharField(max_length=4, choices=EstadoOperativo.choices,
                                        default=EstadoOperativo.SIN_DATO)
    backend = models.CharField("Backend (Framework)", max_length=120, blank=True)
    frontend = models.CharField(max_length=120, blank=True)
    schema_bd = models.CharField("Schema BD", max_length=120, blank=True)
    api_rest_nativa = models.BooleanField(null=True, blank=True)
    integracion_gateway = models.CharField(max_length=120, blank=True)
    estado_documentacion = models.CharField(max_length=255, blank=True)
    sistema_mca_equivalente = models.CharField("Sistema MCA equivalente", max_length=120, blank=True)
    sistema_rbac_id = models.PositiveIntegerField(
        "ID sistema en Matriz RBAC", null=True, blank=True,
        help_text="Vínculo explícito al catálogo RBAC (prioritario sobre el nombre).")
    roles = models.ManyToManyField(RolMCA, blank=True, through="AccesoRol", related_name="sistemas")
    servidor_virtual = models.CharField(max_length=40, blank=True)
    url = models.CharField(max_length=255, blank=True)
    priorizar_analisis = models.CharField(max_length=5, choices=Prioridad.choices,
                                          default=Prioridad.SIN)

    gw_validacion_jwt = models.BooleanField(null=True, blank=True)
    gw_sso = models.BooleanField(null=True, blank=True)
    gw_cors = models.BooleanField(null=True, blank=True)
    gw_inyeccion_roles = models.BooleanField(null=True, blank=True)
    gw_refresh_token = models.BooleanField(null=True, blank=True)
    gw_balanceo_carga = models.BooleanField(null=True, blank=True)

    # --- v2: version de software ---
    version = models.CharField("Version del sistema", max_length=60, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Sistema de informacion"
        verbose_name_plural = "Sistemas de informacion"

    def __str__(self):
        return f"[SIST] {self.activo.id_activo}"


class AccesoRol(models.Model):
    class Nivel(models.TextChoices):
        COMPLETO = "C", "Completo"
        MODIFICACION = "M", "Modificacion"
        LECTURA = "L", "Lectura"

    sistema = models.ForeignKey(SistemaInformacion, on_delete=models.CASCADE)
    rol = models.ForeignKey(RolMCA, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=1, choices=Nivel.choices)

    class Meta:
        verbose_name = "Acceso por rol (MCA)"
        verbose_name_plural = "Accesos por rol (MCA)"
        unique_together = ("sistema", "rol")

    def __str__(self):
        return f"{self.sistema.activo.id_activo} - {self.rol.sigla}({self.nivel})"


# ---------------------------------------------------------------------------
# v3 - CENTRO DE DATOS, DIAGRAMAS Y HOJA DE VIDA
# ---------------------------------------------------------------------------
class Datacenter(models.Model):
    """Centro de datos / sede donde se alojan los activos."""

    class Tipo(models.TextChoices):
        PRINCIPAL = "PRIN", "Datacenter principal"
        MINI = "MINI", "Mini-datacenter"
        RESPALDO = "DR", "Sitio de respaldo (DR)"
        NUBE = "CLOUD", "Nube / Colocation"

    class Tier(models.TextChoices):
        NA = "NA", "No clasificado"
        T1 = "T1", "Tier I"
        T2 = "T2", "Tier II"
        T3 = "T3", "Tier III"
        T4 = "T4", "Tier IV"

    codigo = models.CharField(max_length=30, unique=True, help_text="Ej: DC-POPAYAN")
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=6, choices=Tipo.choices, default=Tipo.PRINCIPAL)
    nivel_tier = models.CharField(max_length=3, choices=Tier.choices, default=Tier.NA)

    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=60, blank=True, default="Colombia")
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    responsable = models.CharField(max_length=150, blank=True)
    descripcion = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Centro de datos"
        verbose_name_plural = "Centros de datos"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Rack(models.Model):
    """Rack físico dentro de un centro de datos (Ola 2)."""
    datacenter = models.ForeignKey(
        "Datacenter", on_delete=models.CASCADE, related_name="racks")
    codigo = models.CharField(max_length=40, help_text="Ej: A01, RACK-NORTE-03")
    capacidad_u = models.PositiveSmallIntegerField(default=42)
    ubicacion = models.CharField(
        "Ubicación en sala", max_length=120, blank=True,
        help_text="Ej: Fila 2, pasillo B")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Rack"
        verbose_name_plural = "Racks"
        ordering = ["datacenter__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["datacenter", "codigo"], name="uniq_rack_por_datacenter"),
        ]

    def __str__(self):
        return f"{self.datacenter.codigo}/{self.codigo}"

    @property
    def ocupacion_u(self):
        qs = ActivoInfraestructura.objects.filter(rack_fk=self)
        total = 0
        for inf in qs.only("unidad_inicio", "unidad_fin"):
            if inf.unidad_inicio and inf.unidad_fin:
                total += max(0, inf.unidad_fin - inf.unidad_inicio + 1)
            elif inf.unidad_inicio:
                total += 1
        return total


class Diagrama(models.Model):
    """Diagrama, topologia o plano asociado a un datacenter y/o a activos."""

    class Tipo(models.TextChoices):
        TOPOLOGIA = "TOPO", "Topologia de red"
        RACK = "RACK", "Diagrama de rack"
        ARQUITECTURA = "ARQ", "Arquitectura"
        FLUJO = "FLUJO", "Diagrama de flujo"
        PLANO = "PLANO", "Plano fisico"
        OTRO = "OTRO", "Otro"

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=6, choices=Tipo.choices, default=Tipo.TOPOLOGIA)
    archivo = models.FileField(upload_to="diagramas/")
    descripcion = models.TextField(blank=True)
    fecha = models.DateField(null=True, blank=True)
    version = models.CharField(max_length=20, blank=True)

    datacenter = models.ForeignKey(
        Datacenter, on_delete=models.CASCADE, null=True, blank=True,
        related_name="diagramas")
    activos = models.ManyToManyField(
        Activo, blank=True, related_name="diagramas")

    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Diagrama / Topologia"
        verbose_name_plural = "Diagramas / Topologias"
        ordering = ["-creado"]

    def __str__(self):
        return self.titulo


class EventoHojaVida(models.Model):
    """
    Registro operativo (hoja de vida) de un activo: mantenimientos,
    actualizaciones, traslados, incidentes, altas y bajas.
    """

    class TipoEvento(models.TextChoices):
        ALTA = "ALTA", "Alta / Puesta en marcha"
        MANT_PREV = "MPRE", "Mantenimiento preventivo"
        MANT_CORR = "MCOR", "Mantenimiento correctivo"
        ACTUALIZACION = "ACTU", "Actualizacion (firmware/software)"
        TRASLADO = "TRAS", "Traslado / Reubicacion"
        INCIDENTE = "INCI", "Incidente de seguridad"
        CONFIG = "CONF", "Cambio de configuracion"
        GARANTIA = "GARA", "Gestion de garantia / RMA"
        BAJA = "BAJA", "Baja / Retiro"
        OTRO = "OTRO", "Otro"

    activo = models.ForeignKey(
        Activo, on_delete=models.CASCADE, related_name="hoja_vida")
    fecha = models.DateField()
    tipo_evento = models.CharField(max_length=4, choices=TipoEvento.choices)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    responsable = models.CharField(max_length=150, blank=True)
    costo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True,
                                help_text="Costo asociado (COP), opcional")
    documento = models.FileField(upload_to="hoja_vida/", null=True, blank=True,
                                 help_text="Acta, factura o reporte, opcional")

    creado = models.DateTimeField(auto_now_add=True)
    registrado_por = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "Evento de hoja de vida"
        verbose_name_plural = "Hoja de vida (eventos)"
        ordering = ["-fecha", "-creado"]

    def __str__(self):
        return f"{self.activo.id_activo} - {self.get_tipo_evento_display()} ({self.fecha})"


class RegistroAcceso(models.Model):
    """Auditoria de accesos y acciones (complementa la bitacora de cambios)."""

    class Accion(models.TextChoices):
        LOGIN = "LOGIN", "Inicio de sesion"
        LOGOUT = "LOGOUT", "Cierre de sesion"
        CREAR = "CREAR", "Creacion"
        EDITAR = "EDITAR", "Edicion"
        ELIMINAR = "ELIMINAR", "Eliminacion"
        EXPORTAR = "EXPORT", "Exportacion / descarga"

    usuario = models.CharField(max_length=150, blank=True)
    accion = models.CharField(max_length=10, choices=Accion.choices)
    recurso = models.CharField(max_length=120, blank=True)
    detalle = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de acceso"
        verbose_name_plural = "Registros de acceso (auditoria)"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.usuario} {self.accion}"


class RegistroIntegridad(models.Model):
    """Bitácora encadenada por hash SHA-256 — misma garantía verificable
    que ya tenía RBAC (ver inventario/integridad.py). Una fila por cada
    versión histórica que django-simple-history crea de Activo y sus
    modelos de detalle 1:1 (infraestructura, sistema, equipo) y de
    Datacenter; se llena sola vía señal (ver signals.py), nunca a mano."""

    fecha = models.CharField(max_length=25)  # 'AAAA-MM-DD HH:MM:SS' — mismo
    # formato de texto exacto que ya usa RBAC (rbac/db.py), no DateTimeField:
    # el hash se calcula sobre esta cadena tal cual, y un DateTimeField
    # podría re-serializarse distinto al leerlo de vuelta (zona horaria,
    # microsegundos), lo que rompería la verificación sin que nada haya
    # sido alterado en realidad.
    entidad = models.CharField(max_length=40)
    accion = models.CharField(max_length=20)
    detalle = models.TextField()
    responsable = models.CharField(max_length=150)
    hash_anterior = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        verbose_name = "Registro de integridad"
        verbose_name_plural = "Registros de integridad (bitácora encadenada)"
        ordering = ["id"]

    def __str__(self):
        return f"{self.fecha} {self.entidad} {self.accion}"


class PerfilPlataforma(models.Model):
    """Metadatos de plataforma por usuario — versión de JWT para invalidar
    tokens emitidos antes de un cambio de rol (Ola 1, revocación JWT)."""
    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="perfil_plataforma")
    jwt_version = models.PositiveIntegerField(default=1)
    area = models.CharField(
        "Área organizacional",
        max_length=120,
        blank=True,
        help_text="Dependencia o área del CRIC/SUIIN a la que pertenece el usuario.",
    )

    class Meta:
        verbose_name = "Perfil de plataforma"
        verbose_name_plural = "Perfiles de plataforma"

    def __str__(self):
        return f"{self.user.get_username()} (JWT v{self.jwt_version})"

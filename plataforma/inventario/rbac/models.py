from django.db import models


class GrupoRol(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'grupo_rol'
        verbose_name = 'Grupo de rol'
        verbose_name_plural = 'Grupos de rol'

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'


class NivelAcceso(models.Model):
    codigo = models.CharField(max_length=5, primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField()
    orden = models.IntegerField()

    class Meta:
        db_table = 'nivel_acceso'
        ordering = ['orden']

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'


class Rol(models.Model):
    RIESGO_CHOICES = [
        ('Alto', 'Alto'),
        ('Medio', 'Medio'),
        ('Bajo', 'Bajo'),
    ]

    codigo = models.CharField(max_length=10, unique=True)
    abreviatura = models.CharField(max_length=20, unique=True)
    denominacion = models.CharField(max_length=200)
    grupo = models.ForeignKey(GrupoRol, on_delete=models.PROTECT, db_column='grupo_id')
    cosecha = models.CharField(max_length=20, blank=True, null=True)
    en_det7 = models.BooleanField(default=True)
    funcion = models.TextField(blank=True, null=True)
    mfa_requerido = models.CharField(max_length=50)
    riesgo_attack = models.CharField(max_length=10, choices=RIESGO_CHOICES)
    revision_periodica = models.CharField(max_length=20)
    ultima_revision = models.CharField(max_length=20, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'rol'

    def __str__(self):
        return self.abreviatura


class CategoriaSistema(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'categoria_sistema'

    def __str__(self):
        return self.nombre


class Sistema(models.Model):
    CLASIFICACION_CHOICES = [
        ('Altamente Confidencial', 'Altamente Confidencial'),
        ('Confidencial', 'Confidencial'),
        ('Interna', 'Interna'),
        ('Pública', 'Pública'),
    ]

    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaSistema, on_delete=models.PROTECT, db_column='categoria_id')
    clasificacion = models.CharField(max_length=30, choices=CLASIFICACION_CHOICES)
    tecnicas_attack = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    espacio_codigo = models.CharField(max_length=50, default='organizacion')

    class Meta:
        db_table = 'sistema'
        constraints = [
            models.UniqueConstraint(
                fields=['espacio_codigo', 'nombre'],
                name='sistema_espacio_nombre_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['espacio_codigo'], name='idx_sistema_espacio'),
        ]

    def __str__(self):
        return self.nombre


class AttackTecnica(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=300)
    tactica = models.CharField(max_length=100, blank=True, null=True)
    es_subtecnica = models.BooleanField(default=False)
    padre = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'attack_tecnica'

    def __str__(self):
        return self.id


class MatrizAcceso(models.Model):
    pk = models.CompositePrimaryKey('rol_id', 'sistema_id')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='rol_id')
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, db_column='sistema_id')
    nivel = models.ForeignKey(
        NivelAcceso,
        on_delete=models.PROTECT,
        db_column='nivel_codigo',
        to_field='codigo',
    )

    class Meta:
        db_table = 'matriz_acceso'
        indexes = [
            models.Index(fields=['sistema'], name='idx_matriz_sistema'),
        ]


class Usuario(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Temporal', 'Temporal'),
        ('Suspendido', 'Suspendido'),
        ('Revocado', 'Revocado'),
    ]

    nombre = models.CharField(max_length=200)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column='rol_id')
    mfa_activo = models.CharField(max_length=50, default='No')
    nda = models.CharField(max_length=20, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Activo')
    fecha_inicio = models.CharField(max_length=30, blank=True, null=True)
    fecha_fin = models.CharField(max_length=30, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    espacio_codigo = models.CharField(max_length=50, default='organizacion')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'usuario'
        indexes = [
            models.Index(fields=['espacio_codigo'], name='idx_usuario_espacio'),
            models.Index(fields=['rol'], name='idx_usuario_rol'),
            models.Index(fields=['estado'], name='idx_usuario_estado'),
        ]

    def __str__(self):
        return self.nombre


class AccesoExcepcion(models.Model):
    pk = models.CompositePrimaryKey('usuario_id', 'sistema_id')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='usuario_id')
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, db_column='sistema_id')
    nivel = models.ForeignKey(
        NivelAcceso,
        on_delete=models.PROTECT,
        db_column='nivel_codigo',
        to_field='codigo',
    )
    motivo = models.TextField()
    fecha_fin = models.CharField(max_length=30, blank=True, null=True)
    espacio_codigo = models.CharField(max_length=50, default='organizacion')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'acceso_excepcion'
        indexes = [
            models.Index(fields=['sistema'], name='idx_excepcion_sistema'),
        ]


class LogAuditoria(models.Model):
    fecha = models.CharField(max_length=30)
    entidad = models.CharField(max_length=50)
    accion = models.CharField(max_length=20)
    detalle = models.TextField()
    responsable = models.CharField(max_length=100, default='sistema')
    hash_cadena = models.CharField(max_length=64, db_column='hash')

    class Meta:
        db_table = 'log_auditoria'
        indexes = [
            models.Index(fields=['fecha'], name='idx_log_fecha'),
        ]

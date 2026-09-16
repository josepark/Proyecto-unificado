"""Catálogos estáticos del esquema RBAC (SUIIN-SGSI-MCA-001)."""

ESTADOS_USUARIO = ('Activo', 'Temporal', 'Suspendido', 'Revocado')
RIESGOS_ATTACK = ('Alto', 'Medio', 'Bajo')
CLASIFICACIONES = (
    'Altamente Confidencial', 'Confidencial', 'Interna', 'Pública',
)
DIAS_ALERTA_VENCIMIENTO = 7

GRUPOS = [
    ('GOB', 'Gobierno'), ('ASE', 'Asesoría'), ('LID', 'Liderazgo'),
    ('PRO', 'Profesional'), ('CON', 'Conocimiento'), ('TEC', 'Tecnología'),
    ('COL', 'Colaboración'), ('OPE', 'Operativo'),
    ('TI', 'TI Privilegiado'), ('EXT', 'Externo'),
]

NIVELES = [
    ('A', 'Admin', 'Acceso completo + configuración del sistema + gestión de cuentas. '
     'Exclusivo para roles TI autorizados. MFA obligatorio. Revisión trimestral.', 1),
    ('C', 'Completo', 'Crear, Leer, Actualizar y Eliminar (CRUD). '
     'Acceso operativo total al sistema o módulo asignado.', 2),
    ('M', 'Modificar', 'Leer y Actualizar. Sin creación ni eliminación de registros principales.', 3),
    ('L', 'Lectura', 'Solo consulta (Read Only). Sin modificación de ningún dato.', 4),
    ('T', 'Temporal', 'Acceso limitado por tiempo con NDA vigente. Solo proveedores o '
     'auditores autorizados. Fecha inicio/fin obligatoria.', 5),
    ('—', 'Sin acceso', 'El rol no tiene ningún nivel de acceso a este sistema o módulo.', 6),
]

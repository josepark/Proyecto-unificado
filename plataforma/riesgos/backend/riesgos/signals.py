"""
Recalcula Activo.riesgo_matriz automáticamente cada vez que cambia una Vulnerabilidad
o un RiesgoActivo asociado. Antes (solo import desde Excel) este campo era un valor
congelado; con edición en vivo desde el frontend necesita mantenerse consistente,
o el dashboard terminaría mostrando un nivel de riesgo desactualizado.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Activo, Vulnerabilidad, RiesgoActivo

NIVEL_PESO = {"CRITICO": 4, "ALTO": 3, "MEDIO": 2, "BAJO": 1, "SIN_DATO": 0}
PESO_NIVEL = {v: k for k, v in NIVEL_PESO.items()}


def recalcular_riesgo_activo(activo: Activo):
    niveles = list(
        activo.vulnerabilidades.exclude(nivel_riesgo="SIN_DATO").values_list("nivel_riesgo", flat=True)
    ) + list(
        activo.riesgos_agregados.values_list("nivel_riesgo", flat=True)
    )
    if not niveles:
        return  # sin hallazgos registrados aún: se conserva el valor actual (ej. importado)

    peso_max = max(NIVEL_PESO.get(n, 0) for n in niveles)
    nuevo_nivel = PESO_NIVEL[peso_max]
    if activo.riesgo_matriz != nuevo_nivel:
        Activo.objects.filter(pk=activo.pk).update(riesgo_matriz=nuevo_nivel)


@receiver(post_save, sender=Vulnerabilidad)
@receiver(post_delete, sender=Vulnerabilidad)
def _on_vulnerabilidad_cambio(sender, instance, **kwargs):
    recalcular_riesgo_activo(instance.activo)


@receiver(post_save, sender=RiesgoActivo)
@receiver(post_delete, sender=RiesgoActivo)
def _on_riesgo_activo_cambio(sender, instance, **kwargs):
    recalcular_riesgo_activo(instance.activo)

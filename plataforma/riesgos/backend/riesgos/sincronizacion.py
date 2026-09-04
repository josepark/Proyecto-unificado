# -*- coding: utf-8 -*-
"""
Mecanismo reutilizable de "sincronizar sin pisar ediciones manuales", usado por
cualquier comando que trae datos desde una fuente externa (Excel, o la API de
otro servicio como el Inventario de la Plataforma SUIIN) hacia la base de datos
de riesgos.

Se extrajo de `importar_matrices.py` para que `sincronizar_activos_inventario.py`
lo reutilice sin duplicar la lógica — ambos comandos comparten exactamente el
mismo criterio de qué registros están "protegidos" (ver
`TimeStampedModel.fue_editado_tras_importacion()` en riesgos/models.py).
"""
from django.utils import timezone


class ProtectorSincronizacion:
    """
    Uso:
        protector = ProtectorSincronizacion(forzar=False)
        obj, protegido = protector.guardar_protegiendo(
            Activo, filtro={"id_activo": "RED-012"}, defaults={...}, descripcion="RED-012")
        ...
        protector.reportar(self.stdout, self.stderr, self.style)
    """

    def __init__(self, forzar=False):
        self.forzar = forzar
        self.stats = {"creados": 0, "actualizados": 0, "protegidos": []}

    def guardar_protegiendo(self, modelo, filtro, defaults, descripcion):
        """
        Crea el registro si no existe. Si ya existe, lo actualiza SOLO si no fue
        editado manualmente desde la última sincronización (o si forzar=True).
        Devuelve (instancia, fue_protegido).
        """
        existente = modelo.objects.filter(**filtro).first()
        ahora = timezone.now()

        if existente is None:
            # Se fusionan como un solo dict (defaults tiene prioridad en caso de
            # solapamiento) — pasarlos como dos `**` separados falla si comparten
            # una llave (ej. el comando de sincronización de activos necesita
            # 'inventario_id' tanto en filtro, para la búsqueda, como en
            # defaults, para que también quede guardado al crear).
            campos = {k: v for k, v in filtro.items() if k != "pk"}
            campos.update(defaults)
            obj = modelo(**campos)
            obj.importado_en = ahora
            obj.save()
            self.stats["creados"] += 1
            return obj, False

        if not self.forzar and existente.fue_editado_tras_importacion():
            self.stats["protegidos"].append(f"{modelo.__name__} {descripcion}")
            return existente, True

        for campo, valor in defaults.items():
            setattr(existente, campo, valor)
        existente.importado_en = ahora
        existente.save()
        self.stats["actualizados"] += 1
        return existente, False

    def reportar(self, stdout, stderr, style):
        stdout.write(style.SUCCESS(
            f"Sincronización completada: {self.stats['creados']} creado(s), "
            f"{self.stats['actualizados']} actualizado(s)."))
        if self.stats["protegidos"]:
            stderr.write(style.WARNING(
                f"⚠ {len(self.stats['protegidos'])} registro(s) protegido(s) — editados "
                f"manualmente desde la última sincronización, NO se sobrescribieron:"))
            for descripcion in self.stats["protegidos"]:
                stdout.write(f"    · {descripcion}")
            stdout.write(
                "  Use --forzar-sobrescritura si de verdad quiere que la fuente externa "
                "gane sobre esas ediciones (se perderán).")

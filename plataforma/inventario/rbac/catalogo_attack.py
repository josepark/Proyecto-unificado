"""Sincroniza el catálogo MITRE ATT&CK desde static/attack_tecnicas.json."""
import json

from rbac.models import AttackTecnica
from rbac.paths import ATTACK_TECNICAS_JSON


def cargar_json():
    with ATTACK_TECNICAS_JSON.open(encoding='utf-8') as f:
        return json.load(f)


def sincronizar(using='rbac'):
    """Repuebla attack_tecnica desde el JSON del servicio Flask. Idempotente."""
    tecnicas = cargar_json()
    AttackTecnica.objects.using(using).all().delete()
    AttackTecnica.objects.using(using).bulk_create([
        AttackTecnica(
            id=t['id'],
            nombre=t['nombre'],
            tactica=t.get('tactica', '') or None,
            es_subtecnica=bool(t.get('es_subtecnica')),
            padre=t.get('padre') or None,
        )
        for t in tecnicas
    ])
    return len(tecnicas)

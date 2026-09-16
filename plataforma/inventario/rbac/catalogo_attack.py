"""Sincroniza el catálogo MITRE ATT&CK desde static/attack_tecnicas.json o Inventario."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from rbac.models import AttackTecnica
from rbac.paths import ATTACK_TECNICAS_JSON


def cargar_json():
    with ATTACK_TECNICAS_JSON.open(encoding='utf-8') as f:
        return json.load(f)


def _get_json(url, jwt_secret=''):
    headers = {}
    if jwt_secret:
        headers['X-Plataforma-Secret'] = jwt_secret
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_desde_inventario(inventario_url=None, jwt_secret=None):
    """Descarga técnicas MITRE desde /api/interno/catalogo-mitre/ del Inventario."""
    base = (inventario_url or os.environ.get('INVENTARIO_URL', 'http://127.0.0.1:8000')).rstrip('/')
    secret = jwt_secret if jwt_secret is not None else os.environ.get('JWT_SHARED_SECRET', '')
    tecnicas = []
    url = f'{base}/api/interno/catalogo-mitre/?page_size=2000&ordering=codigo'
    while url:
        data = _get_json(url, secret)
        resultados = data.get('results', data) if isinstance(data, dict) else data
        for a in resultados:
            if a['tipo'] not in ('TE', 'ST'):
                continue
            tecnicas.append({
                'id': a['codigo'],
                'nombre': a['nombre'],
                'tactica': a.get('tacticas') or '',
                'es_subtecnica': a['tipo'] == 'ST',
                'padre': a.get('codigo_padre') or None,
            })
        url = data.get('next') if isinstance(data, dict) else None
    if not tecnicas:
        raise ValueError('El Inventario no devolvió técnicas — ¿ejecutó importar_mitre?')
    tecnicas.sort(key=lambda t: t['id'])
    return tecnicas


def guardar_json(tecnicas):
    ATTACK_TECNICAS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with ATTACK_TECNICAS_JSON.open('w', encoding='utf-8') as f:
        json.dump(tecnicas, f, ensure_ascii=False, separators=(',', ':'))


def sincronizar(using='rbac', tecnicas=None):
    """Repuebla attack_tecnica. Idempotente."""
    if tecnicas is None:
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


def sincronizar_desde_inventario(using='rbac', inventario_url=None, jwt_secret=None, guardar=True):
    """Regenera attack_tecnicas.json (si existe la ruta) y repuebla attack_tecnica."""
    tecnicas = fetch_desde_inventario(inventario_url=inventario_url, jwt_secret=jwt_secret)
    if guardar:
        try:
            guardar_json(tecnicas)
        except OSError:
            pass
    return sincronizar(using=using, tecnicas=tecnicas)

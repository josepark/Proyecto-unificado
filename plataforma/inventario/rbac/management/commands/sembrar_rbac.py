"""Carga inicial de la base RBAC Django (SUIIN-SGSI-MCA-001 v2.0)."""
import hashlib
import json
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from rbac import catalogo_attack
from rbac.constants import GRUPOS, NIVELES
from rbac.models import (
    GrupoRol,
    LogAuditoria,
    MatrizAcceso,
    NivelAcceso,
    Rol,
    Sistema,
    CategoriaSistema,
    Usuario,
)
from rbac.paths import RBAC_DATA_JSON


class Command(BaseCommand):
    help = (
        'Crea o repuebla la base RBAC Django desde rbac/rbac_data.json '
        '(matriz demo MCA-001 v2.0 + catálogo MITRE ATT&CK).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Elimina los datos RBAC existentes antes de sembrar',
        )

    def handle(self, *args, **options):
        if not RBAC_DATA_JSON.is_file():
            raise CommandError(f'No se encontró {RBAC_DATA_JSON}')

        using = 'rbac'
        if options['forzar']:
            self._vaciar(using)

        if Rol.objects.using(using).exists():
            raise CommandError(
                'La base RBAC ya tiene datos. Use --forzar para repoblar desde cero.'
            )

        with open(RBAC_DATA_JSON, encoding='utf-8') as f:
            data = json.load(f)

        with transaction.atomic(using=using):
            stats = self._sembrar(data, using)

        n_attack = catalogo_attack.sincronizar(using=using)
        self.stdout.write(self.style.SUCCESS(
            f'RBAC sembrado en alias "{using}": '
            f'{stats["roles"]} roles, {stats["sistemas"]} sistemas, '
            f'{stats["accesos"]} accesos, {stats["usuarios"]} usuarios, '
            f'{n_attack} técnicas ATT&CK'
        ))

    def _vaciar(self, using):
        LogAuditoria.objects.using(using).all().delete()
        Usuario.objects.using(using).all().delete()
        MatrizAcceso.objects.using(using).all().delete()
        Sistema.objects.using(using).all().delete()
        CategoriaSistema.objects.using(using).all().delete()
        Rol.objects.using(using).all().delete()
        NivelAcceso.objects.using(using).all().delete()
        GrupoRol.objects.using(using).all().delete()

    def _sembrar(self, data, using):
        for codigo, nombre in GRUPOS:
            GrupoRol.objects.using(using).create(codigo=codigo, nombre=nombre)

        for codigo, nombre, descripcion, orden in NIVELES:
            NivelAcceso.objects.using(using).create(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                orden=orden,
            )

        gid = {
            g.nombre: g.pk
            for g in GrupoRol.objects.using(using).all()
        }

        rid = {}
        for r in data['roles']:
            rol = Rol.objects.using(using).create(
                codigo=r['codigo'],
                abreviatura=r['abrev'],
                denominacion=r['denominacion'],
                grupo_id=gid[r['grupo']],
                cosecha=r.get('cosecha') or None,
                en_det7=bool(r.get('en_det7', True)),
                funcion=r.get('funcion') or None,
                mfa_requerido=r['mfa'],
                riesgo_attack=r['riesgo'],
                revision_periodica=r['revision'],
                observaciones=r.get('nota') or None,
            )
            rid[r['codigo']] = rol.pk

        cat_id = {}
        sid = {}
        for s in data['sistemas']:
            categoria = s['categoria']
            if categoria not in cat_id:
                cat = CategoriaSistema.objects.using(using).create(nombre=categoria)
                cat_id[categoria] = cat.pk
            sistema = Sistema.objects.using(using).create(
                nombre=s['nombre'],
                categoria_id=cat_id[categoria],
                clasificacion=s['clasificacion'],
                tecnicas_attack=s.get('attck') or None,
            )
            sid[s['nombre']] = sistema.pk

        accesos = []
        for m in data['matriz']:
            accesos.append(MatrizAcceso(
                rol_id=rid[m['rol_codigo']],
                sistema_id=sid[m['sistema']],
                nivel_id=m['nivel'],
            ))
        MatrizAcceso.objects.using(using).bulk_create(accesos)

        for u in data['usuarios']:
            estado_raw = u['estado']
            if 'REVOCADO' in estado_raw.upper():
                estado = 'Revocado'
            elif estado_raw.startswith('Temporal'):
                estado = 'Temporal'
            else:
                estado = 'Activo'
            notas = u['estado'] if estado != 'Activo' or '—' in u['estado'] else ''
            Usuario.objects.using(using).create(
                nombre=u['nombre'],
                rol_id=rid[u['rol_codigo']],
                mfa_activo=u['mfa_activo'],
                nda=u.get('nda') or None,
                estado=estado,
                notas=notas or None,
            )

        n_accesos = MatrizAcceso.objects.using(using).exclude(nivel_id='—').count()
        fecha = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        detalle = (
            'Carga inicial desde SUIIN-SGSI-MCA-001 v2.0: '
            f'{len(rid)} roles, {len(sid)} sistemas, '
            f'{len(data["matriz"])} celdas de matriz, '
            f'{len(data["usuarios"])} usuarios.'
        )
        hash_cadena = hashlib.sha256(
            f'GENESIS|{fecha}|sistema|ALTA|{detalle}|sistema'.encode()
        ).hexdigest()
        LogAuditoria.objects.using(using).create(
            fecha=fecha,
            entidad='sistema',
            accion='ALTA',
            detalle=detalle,
            responsable='sistema',
            hash_cadena=hash_cadena,
        )

        return {
            'roles': len(rid),
            'sistemas': len(sid),
            'accesos': n_accesos,
            'usuarios': len(data['usuarios']),
        }

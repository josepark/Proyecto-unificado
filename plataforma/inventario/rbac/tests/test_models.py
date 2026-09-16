from django.test import TestCase

from rbac.constants import GRUPOS, NIVELES
from rbac.models import GrupoRol, MatrizAcceso, NivelAcceso, Rol


class RbacModelsTest(TestCase):
    databases = {'default', 'rbac'}

    def test_grupo_rol_se_persiste_en_alias_rbac(self):
        g = GrupoRol.objects.using('rbac').create(codigo='GOB', nombre='Gobierno')
        self.assertEqual(GrupoRol.objects.using('rbac').get(pk=g.pk).codigo, 'GOB')
        self.assertEqual(GrupoRol.objects.get(pk=g.pk).codigo, 'GOB')

    def test_nivel_sin_acceso_codigo_especial(self):
        NivelAcceso.objects.using('rbac').create(
            codigo='—',
            nombre='Sin acceso',
            descripcion='Sin acceso al sistema',
            orden=6,
        )
        self.assertTrue(
            NivelAcceso.objects.using('rbac').filter(codigo='—').exists()
        )

    def test_constants_cubren_catalogo_base(self):
        self.assertEqual(len(GRUPOS), 10)
        self.assertEqual(len(NIVELES), 6)
        codigos = {c for c, *_ in NIVELES}
        self.assertIn('A', codigos)
        self.assertIn('—', codigos)

    def test_matriz_acceso_clave_compuesta(self):
        for codigo, nombre in GRUPOS[:1]:
            GrupoRol.objects.using('rbac').create(codigo=codigo, nombre=nombre)
        for codigo, nombre, desc, orden in NIVELES[:2]:
            NivelAcceso.objects.using('rbac').create(
                codigo=codigo, nombre=nombre, descripcion=desc, orden=orden,
            )
        grupo = GrupoRol.objects.using('rbac').get(codigo='GOB')
        rol = Rol.objects.using('rbac').create(
            codigo='001',
            abreviatura='CM',
            denominacion='Consejería Mayor',
            grupo=grupo,
            mfa_requerido='Sí — obligatorio',
            riesgo_attack='Alto',
            revision_periodica='Trimestral',
        )
        from rbac.models import CategoriaSistema, Sistema

        cat = CategoriaSistema.objects.using('rbac').create(nombre='SISTEMAS')
        sistema = Sistema.objects.using('rbac').create(
            nombre='ERP',
            categoria=cat,
            clasificacion='Confidencial',
        )
        MatrizAcceso.objects.using('rbac').create(
            rol=rol,
            sistema=sistema,
            nivel_id='A',
        )
        self.assertEqual(MatrizAcceso.objects.using('rbac').count(), 1)

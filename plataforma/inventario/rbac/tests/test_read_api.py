from django.test import TestCase, Client

from rbac.management.commands.sembrar_rbac import Command as SembrarRbac


class RbacReadApiTest(TestCase):
    databases = {'default', 'rbac'}

    @classmethod
    def setUpTestData(cls):
        SembrarRbac().handle(forzar=True)

    def setUp(self):
        self.client = Client()

    def test_resumen_devuelve_kpis(self):
        r = self.client.get('/rbac/api/resumen')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['roles_total'], 25)
        self.assertEqual(data['sistemas_total'], 29)
        self.assertIn('mfa_pct', data)

    def test_inicio_devuelve_tablero(self):
        r = self.client.get('/rbac/api/inicio')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['stats']['roles'], 25)
        self.assertIn('proximos_vencimientos', data)
        self.assertIn('log', data)

    def test_catalogos_incluye_niveles(self):
        r = self.client.get('/rbac/api/catalogos')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['niveles_acceso']), 6)

    def test_roles_lista_filtra_por_q(self):
        r = self.client.get('/rbac/api/roles', {'q': 'CM'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(row['abreviatura'] == 'CM' for row in r.json()))

    def test_matriz_tiene_celdas(self):
        r = self.client.get('/rbac/api/matriz')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(len(data['roles']), 0)
        self.assertGreater(len(data['celdas']), 0)

    def test_rol_inexistente_404(self):
        r = self.client.get('/rbac/api/roles/99999')
        self.assertEqual(r.status_code, 404)

    def test_auditoria_verificar_integra(self):
        r = self.client.get('/rbac/api/auditoria/verificar')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['integra'])

    def test_export_matriz_csv(self):
        r = self.client.get('/rbac/api/export/matriz.csv')
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        self.assertTrue(r.content.startswith(b'\xef\xbb\xbfSistema'))

    def test_matriz_comparar_requiere_params(self):
        r = self.client.get('/rbac/api/matriz/comparar')
        self.assertEqual(r.status_code, 400)

    def test_sistemas_lista(self):
        r = self.client.get('/rbac/api/sistemas')
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertGreater(len(data), 0)
        self.assertIn('n_roles', data[0])
        self.assertIn('categoria', data[0])

    def test_excepciones_lista(self):
        r = self.client.get('/rbac/api/excepciones')
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertIn('filas', data)
        self.assertIn('total_vigentes', data)

    def test_auditoria_lista(self):
        r = self.client.get('/rbac/api/auditoria')
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertIn('registros', data)
        self.assertIn('total', data)
        self.assertGreaterEqual(data['total'], len(data['registros']))

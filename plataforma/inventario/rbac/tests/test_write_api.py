from django.test import Client, TestCase

from rbac.management.commands.sembrar_rbac import Command as SembrarRbac


class RbacWriteApiTest(TestCase):
    databases = {'default', 'rbac'}

    @classmethod
    def setUpTestData(cls):
        SembrarRbac().handle(forzar=True)

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def _csrf(self):
        r = self.client.get('/rbac/api/csrf')
        token = r.json()['csrf_token']
        return {'HTTP_X_CSRF_TOKEN': token}

    def test_editar_celda_matriz(self):
        r = self.client.put(
            '/rbac/api/matriz',
            {'rol_id': 1, 'sistema_id': 1, 'nivel': 'L'},
            content_type='application/json',
            **self._csrf(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['nuevo'], 'L')

    def test_crear_y_eliminar_usuario(self):
        rol = self.client.get('/rbac/api/roles', {'q': 'CM'}).json()[0]
        crear = self.client.post(
            '/rbac/api/usuarios',
            {
                'nombre': 'Prueba API Django',
                'rol_id': rol['id'],
                'estado': 'Activo',
                'mfa_activo': 'No',
            },
            content_type='application/json',
            **self._csrf(),
        )
        self.assertEqual(crear.status_code, 201)
        uid = crear.json()['id']
        eliminar = self.client.delete(
            f'/rbac/api/usuarios/{uid}',
            **self._csrf(),
        )
        self.assertEqual(eliminar.status_code, 200)
        self.assertTrue(eliminar.json()['eliminado'])

    def test_sin_csrf_rechaza_post(self):
        r = self.client.post(
            '/rbac/api/roles',
            {'codigo': '999', 'abreviatura': 'TST', 'denominacion': 'Test'},
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 403)

    def test_certificar_rol(self):
        rol = self.client.get('/rbac/api/roles', {'q': 'CM'}).json()[0]
        r = self.client.post(
            f"/rbac/api/roles/{rol['id']}/certificar",
            {'nota': 'Revisión de prueba'},
            content_type='application/json',
            **self._csrf(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['certificado'])

    def test_importar_matriz_analizar_vacio(self):
        r = self.client.post(
            '/rbac/api/matriz/importar/analizar',
            **self._csrf(),
        )
        self.assertEqual(r.status_code, 400)

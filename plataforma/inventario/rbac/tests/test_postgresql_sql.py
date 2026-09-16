from unittest.mock import patch

from django.test import SimpleTestCase

from rbac.sql_compat import sql_activo, sql_revision_vencida, date_col, hoy_mas_dias


class RbacPostgresqlSqlCompatTest(SimpleTestCase):
    @patch('rbac.sql_compat.vendor', return_value='postgresql')
    def test_sql_activo_postgresql(self, _mock):
        self.assertEqual(sql_activo('r.activo'), 'r.activo IS TRUE')
        self.assertEqual(sql_activo('s.activo'), 's.activo IS TRUE')

    @patch('rbac.sql_compat.vendor', return_value='sqlite')
    def test_sql_activo_sqlite(self, _mock):
        self.assertEqual(sql_activo('r.activo'), 'r.activo=1')

    @patch('rbac.sql_compat.vendor', return_value='postgresql')
    def test_revision_vencida_usa_nullif(self, _mock):
        sql = sql_revision_vencida('r')
        self.assertIn('NULLIF(TRIM(r.ultima_revision)', sql)
        self.assertIn('INTERVAL', sql)

    @patch('rbac.sql_compat.vendor', return_value='postgresql')
    def test_date_col_nullif(self, _mock):
        self.assertEqual(date_col('u.fecha_fin'), "NULLIF(TRIM(u.fecha_fin), '')::date")

    @patch('rbac.sql_compat.vendor', return_value='postgresql')
    def test_hoy_mas_dias_entero(self, _mock):
        self.assertEqual(hoy_mas_dias(30), '(CURRENT_DATE + 30)')

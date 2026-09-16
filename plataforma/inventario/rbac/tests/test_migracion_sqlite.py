import os
import sqlite3
import stat
import tempfile
from pathlib import Path

from django.test import TestCase

from rbac.management.commands.sembrar_rbac import Command as SembrarRbac
from rbac.migracion_sqlite import MigracionError, migrar, origen_sqlite_usable, verificar_origen


class MigrarRbacSqliteTest(TestCase):
    databases = {'default', 'rbac'}

    def _crear_sqlite_minimo(self, path: Path):
        """SQLite mínimo compatible con el esquema Flask."""
        con = sqlite3.connect(path)
        con.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE grupo_rol (id INTEGER PRIMARY KEY, codigo TEXT, nombre TEXT);
            CREATE TABLE nivel_acceso (codigo TEXT PRIMARY KEY, nombre TEXT, descripcion TEXT, orden INTEGER);
            CREATE TABLE categoria_sistema (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE);
            CREATE TABLE attack_tecnica (id TEXT PRIMARY KEY, nombre TEXT, tactica TEXT,
                es_subtecnica INTEGER, padre TEXT);
            CREATE TABLE rol (id INTEGER PRIMARY KEY, codigo TEXT, abreviatura TEXT,
                denominacion TEXT, grupo_id INTEGER, cosecha TEXT, en_det7 INTEGER,
                funcion TEXT, mfa_requerido TEXT, riesgo_attack TEXT, revision_periodica TEXT,
                ultima_revision TEXT, observaciones TEXT, activo INTEGER);
            CREATE TABLE sistema (id INTEGER PRIMARY KEY, nombre TEXT, categoria_id INTEGER,
                clasificacion TEXT, tecnicas_attack TEXT, activo INTEGER,
                espacio_codigo TEXT DEFAULT 'organizacion');
            CREATE TABLE matriz_acceso (rol_id INTEGER, sistema_id INTEGER, nivel_codigo TEXT,
                PRIMARY KEY (rol_id, sistema_id));
            CREATE TABLE usuario (id INTEGER PRIMARY KEY, nombre TEXT, rol_id INTEGER,
                mfa_activo TEXT, nda TEXT, estado TEXT, fecha_inicio TEXT, fecha_fin TEXT,
                notas TEXT, espacio_codigo TEXT DEFAULT 'organizacion',
                creado TEXT, actualizado TEXT);
            CREATE TABLE acceso_excepcion (usuario_id INTEGER, sistema_id INTEGER,
                nivel_codigo TEXT, motivo TEXT, fecha_fin TEXT,
                espacio_codigo TEXT DEFAULT 'organizacion', creado TEXT,
                PRIMARY KEY (usuario_id, sistema_id));
            CREATE TABLE log_auditoria (id INTEGER PRIMARY KEY, fecha TEXT, entidad TEXT,
                accion TEXT, detalle TEXT, responsable TEXT, hash TEXT);
            INSERT INTO grupo_rol VALUES (1,'GOB','Gobierno');
            INSERT INTO nivel_acceso VALUES ('A','Admin','x',1),('—','Sin','x',6);
            INSERT INTO categoria_sistema VALUES (1,'SISTEMAS');
            INSERT INTO rol VALUES (1,'001','CM','Rol test',1,'01',1,'','Sí','Alto','Trimestral',NULL,'',1);
            INSERT INTO sistema VALUES (1,'ERP',1,'Confidencial',NULL,1,'organizacion');
            INSERT INTO matriz_acceso VALUES (1,1,'A');
            INSERT INTO usuario VALUES (1,'Ana',1,'No',NULL,'Activo',NULL,NULL,'','organizacion',
                '2024-06-01 10:00:00','2024-06-01 10:00:00');
            INSERT INTO log_auditoria VALUES (1,'2024-06-01 10:00:00','sistema','ALTA','seed','sistema','abc');
        """)
        con.commit()
        con.close()

    def test_migrar_desde_sqlite_temporal(self):
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / 'rbac.db'
            self._crear_sqlite_minimo(origen)
            verificar_origen(origen)
            resultado = migrar(origen=origen, forzar=True)
            self.assertEqual(resultado['destino']['rol'], 1)
            self.assertEqual(resultado['destino']['usuario'], 1)
            self.assertEqual(resultado['destino']['matriz_acceso'], 1)

    def test_rechaza_destino_con_datos_sin_forzar(self):
        SembrarRbac().handle(forzar=True)
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / 'rbac.db'
            self._crear_sqlite_minimo(origen)
            with self.assertRaises(MigracionError):
                migrar(origen=origen, forzar=False)

    def test_origen_inexistente(self):
        with self.assertRaises(MigracionError):
            verificar_origen(Path('/tmp/no-existe-rbac.db'))

    def test_origen_solo_lectura_como_volumen_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            origen = Path(tmp) / 'rbac.db'
            self._crear_sqlite_minimo(origen)
            os.chmod(origen, stat.S_IRUSR)
            self.assertTrue(origen_sqlite_usable(origen))
            resultado = migrar(origen=origen, forzar=True)
            self.assertEqual(resultado['destino']['rol'], 1)

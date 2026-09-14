BEGIN;
--
-- Create model AmenazaMITRE
--
CREATE TABLE "inventario_amenazamitre" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "codigo" varchar(20) NOT NULL UNIQUE, "descripcion" varchar(200) NOT NULL);
--
-- Create model ControlISO
--
CREATE TABLE "inventario_controliso" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "codigo" varchar(30) NOT NULL UNIQUE, "descripcion" varchar(200) NOT NULL);
--
-- Create model RolMCA
--
CREATE TABLE "inventario_rolmca" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "sigla" varchar(10) NOT NULL UNIQUE, "nombre" varchar(120) NOT NULL);
--
-- Create model VLAN
--
CREATE TABLE "inventario_vlan" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "etiqueta" varchar(60) NOT NULL UNIQUE);
--
-- Create model Zona
--
CREATE TABLE "inventario_zona" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nombre" varchar(120) NOT NULL UNIQUE);
--
-- Create model Activo
--
CREATE TABLE "inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL);
CREATE TABLE "inventario_activo_amenazas" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "activo_id" bigint NOT NULL REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "amenazamitre_id" bigint NOT NULL REFERENCES "inventario_amenazamitre" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "inventario_activo_controles" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "activo_id" bigint NOT NULL REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "controliso_id" bigint NOT NULL REFERENCES "inventario_controliso" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model AccesoRol
--
CREATE TABLE "inventario_accesorol" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nivel" varchar(1) NOT NULL, "rol_id" bigint NOT NULL REFERENCES "inventario_rolmca" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model ActivoInfraestructura
--
CREATE TABLE "inventario_activoinfraestructura" ("activo_id" bigint NOT NULL PRIMARY KEY REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "tipo" varchar(60) NOT NULL, "subtipo" varchar(120) NOT NULL, "ip_segmento" varchar(120) NOT NULL, "modelo" varchar(120) NOT NULL, "serial_placa" varchar(120) NOT NULL, "vlan_id" bigint NULL REFERENCES "inventario_vlan" ("id") DEFERRABLE INITIALLY DEFERRED, "zona_id" bigint NULL REFERENCES "inventario_zona" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model SistemaInformacion
--
CREATE TABLE "inventario_sistemainformacion" ("activo_id" bigint NOT NULL PRIMARY KEY REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "estado_operativo" varchar(4) NOT NULL, "backend" varchar(120) NOT NULL, "frontend" varchar(120) NOT NULL, "schema_bd" varchar(120) NOT NULL, "api_rest_nativa" bool NULL, "integracion_gateway" varchar(120) NOT NULL, "estado_documentacion" varchar(255) NOT NULL, "sistema_mca_equivalente" varchar(120) NOT NULL, "servidor_virtual" varchar(40) NOT NULL, "url" varchar(255) NOT NULL, "priorizar_analisis" varchar(5) NOT NULL, "gw_validacion_jwt" bool NULL, "gw_sso" bool NULL, "gw_cors" bool NULL, "gw_inyeccion_roles" bool NULL, "gw_refresh_token" bool NULL, "gw_balanceo_carga" bool NULL);
--
-- Add field sistema to accesorol
--
CREATE TABLE "new__inventario_accesorol" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nivel" varchar(1) NOT NULL, "rol_id" bigint NOT NULL REFERENCES "inventario_rolmca" ("id") DEFERRABLE INITIALLY DEFERRED, "sistema_id" bigint NOT NULL REFERENCES "inventario_sistemainformacion" ("activo_id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__inventario_accesorol" ("id", "nivel", "rol_id", "sistema_id") SELECT "id", "nivel", "rol_id", NULL FROM "inventario_accesorol";
DROP TABLE "inventario_accesorol";
ALTER TABLE "new__inventario_accesorol" RENAME TO "inventario_accesorol";
CREATE UNIQUE INDEX "inventario_activo_amenazas_activo_id_amenazamitre_id_99479fa4_uniq" ON "inventario_activo_amenazas" ("activo_id", "amenazamitre_id");
CREATE INDEX "inventario_activo_amenazas_activo_id_287b30bd" ON "inventario_activo_amenazas" ("activo_id");
CREATE INDEX "inventario_activo_amenazas_amenazamitre_id_3bb47b3e" ON "inventario_activo_amenazas" ("amenazamitre_id");
CREATE UNIQUE INDEX "inventario_activo_controles_activo_id_controliso_id_85d17cc3_uniq" ON "inventario_activo_controles" ("activo_id", "controliso_id");
CREATE INDEX "inventario_activo_controles_activo_id_803c9ea7" ON "inventario_activo_controles" ("activo_id");
CREATE INDEX "inventario_activo_controles_controliso_id_26122aa3" ON "inventario_activo_controles" ("controliso_id");
CREATE INDEX "inventario_activoinfraestructura_vlan_id_84138b9c" ON "inventario_activoinfraestructura" ("vlan_id");
CREATE INDEX "inventario_activoinfraestructura_zona_id_9c431343" ON "inventario_activoinfraestructura" ("zona_id");
CREATE INDEX "inventario_accesorol_rol_id_558f0f6e" ON "inventario_accesorol" ("rol_id");
CREATE INDEX "inventario_accesorol_sistema_id_d8d2d723" ON "inventario_accesorol" ("sistema_id");
--
-- Alter unique_together for accesorol (1 constraint(s))
--
CREATE UNIQUE INDEX "inventario_accesorol_sistema_id_rol_id_b6424d47_uniq" ON "inventario_accesorol" ("sistema_id", "rol_id");
COMMIT;

BEGIN;
--
-- Add field area_responsable to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "area_responsable" varchar(150) NOT NULL, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field ciclo_vida to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", 'PROD' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field custodio to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field dependencias to activo
--
CREATE TABLE "inventario_activo_dependencias" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "from_activo_id" bigint NOT NULL REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "to_activo_id" bigint NOT NULL REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Add field documentos_relacionados to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL, "documentos_relacionados" text NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
CREATE UNIQUE INDEX "inventario_activo_dependencias_from_activo_id_to_activo_id_a53e019c_uniq" ON "inventario_activo_dependencias" ("from_activo_id", "to_activo_id");
CREATE INDEX "inventario_activo_dependencias_from_activo_id_6f047ea2" ON "inventario_activo_dependencias" ("from_activo_id");
CREATE INDEX "inventario_activo_dependencias_to_activo_id_b00f8a36" ON "inventario_activo_dependencias" ("to_activo_id");
--
-- Add field procesa_datos_personales to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL, "documentos_relacionados" text NOT NULL, "procesa_datos_personales" bool NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", 0 FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field propietario to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL, "documentos_relacionados" text NOT NULL, "procesa_datos_personales" bool NOT NULL, "propietario" varchar(150) NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", "propietario") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field rpo to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL, "documentos_relacionados" text NOT NULL, "procesa_datos_personales" bool NOT NULL, "propietario" varchar(150) NOT NULL, "rpo" varchar(40) NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", "propietario", "rpo") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", "propietario", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field rto to activo
--
CREATE TABLE "new__inventario_activo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id_activo" varchar(30) NOT NULL UNIQUE, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "area_responsable" varchar(150) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "custodio" varchar(150) NOT NULL, "documentos_relacionados" text NOT NULL, "procesa_datos_personales" bool NOT NULL, "propietario" varchar(150) NOT NULL, "rpo" varchar(40) NOT NULL, "rto" varchar(40) NOT NULL);
INSERT INTO "new__inventario_activo" ("id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", "propietario", "rpo", "rto") SELECT "id", "id_activo", "nombre", "descripcion", "clase", "clasificacion_si", "confidencialidad", "integridad", "disponibilidad", "valor", "nivel_riesgo", "estado", "fecha_registro", "notas_seguridad", "creado", "actualizado", "area_responsable", "ciclo_vida", "custodio", "documentos_relacionados", "procesa_datos_personales", "propietario", "rpo", '' FROM "inventario_activo";
DROP TABLE "inventario_activo";
ALTER TABLE "new__inventario_activo" RENAME TO "inventario_activo";
--
-- Add field fabricante_proveedor to activoinfraestructura
--
CREATE TABLE "new__inventario_activoinfraestructura" ("activo_id" bigint NOT NULL PRIMARY KEY REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "tipo" varchar(60) NOT NULL, "subtipo" varchar(120) NOT NULL, "ip_segmento" varchar(120) NOT NULL, "modelo" varchar(120) NOT NULL, "serial_placa" varchar(120) NOT NULL, "vlan_id" bigint NULL REFERENCES "inventario_vlan" ("id") DEFERRABLE INITIALLY DEFERRED, "zona_id" bigint NULL REFERENCES "inventario_zona" ("id") DEFERRABLE INITIALLY DEFERRED, "fabricante_proveedor" varchar(150) NOT NULL);
INSERT INTO "new__inventario_activoinfraestructura" ("activo_id", "tipo", "subtipo", "ip_segmento", "modelo", "serial_placa", "vlan_id", "zona_id", "fabricante_proveedor") SELECT "activo_id", "tipo", "subtipo", "ip_segmento", "modelo", "serial_placa", "vlan_id", "zona_id", '' FROM "inventario_activoinfraestructura";
DROP TABLE "inventario_activoinfraestructura";
ALTER TABLE "new__inventario_activoinfraestructura" RENAME TO "inventario_activoinfraestructura";
CREATE INDEX "inventario_activoinfraestructura_vlan_id_84138b9c" ON "inventario_activoinfraestructura" ("vlan_id");
CREATE INDEX "inventario_activoinfraestructura_zona_id_9c431343" ON "inventario_activoinfraestructura" ("zona_id");
--
-- Add field fecha_adquisicion to activoinfraestructura
--
ALTER TABLE "inventario_activoinfraestructura" ADD COLUMN "fecha_adquisicion" date NULL;
--
-- Add field fecha_ultimo_escaneo to activoinfraestructura
--
ALTER TABLE "inventario_activoinfraestructura" ADD COLUMN "fecha_ultimo_escaneo" date NULL;
--
-- Add field fin_garantia to activoinfraestructura
--
ALTER TABLE "inventario_activoinfraestructura" ADD COLUMN "fin_garantia" date NULL;
--
-- Add field fin_soporte_eol to activoinfraestructura
--
ALTER TABLE "inventario_activoinfraestructura" ADD COLUMN "fin_soporte_eol" date NULL;
--
-- Add field hallazgos_abiertos to activoinfraestructura
--
ALTER TABLE "inventario_activoinfraestructura" ADD COLUMN "hallazgos_abiertos" integer NULL;
--
-- Add field version_so_firmware to activoinfraestructura
--
CREATE TABLE "new__inventario_activoinfraestructura" ("activo_id" bigint NOT NULL PRIMARY KEY REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "tipo" varchar(60) NOT NULL, "subtipo" varchar(120) NOT NULL, "ip_segmento" varchar(120) NOT NULL, "modelo" varchar(120) NOT NULL, "serial_placa" varchar(120) NOT NULL, "vlan_id" bigint NULL REFERENCES "inventario_vlan" ("id") DEFERRABLE INITIALLY DEFERRED, "zona_id" bigint NULL REFERENCES "inventario_zona" ("id") DEFERRABLE INITIALLY DEFERRED, "fabricante_proveedor" varchar(150) NOT NULL, "fecha_adquisicion" date NULL, "fecha_ultimo_escaneo" date NULL, "fin_garantia" date NULL, "fin_soporte_eol" date NULL, "hallazgos_abiertos" integer NULL, "version_so_firmware" varchar(120) NOT NULL);
INSERT INTO "new__inventario_activoinfraestructura" ("activo_id", "tipo", "subtipo", "ip_segmento", "modelo", "serial_placa", "vlan_id", "zona_id", "fabricante_proveedor", "fecha_adquisicion", "fecha_ultimo_escaneo", "fin_garantia", "fin_soporte_eol", "hallazgos_abiertos", "version_so_firmware") SELECT "activo_id", "tipo", "subtipo", "ip_segmento", "modelo", "serial_placa", "vlan_id", "zona_id", "fabricante_proveedor", "fecha_adquisicion", "fecha_ultimo_escaneo", "fin_garantia", "fin_soporte_eol", "hallazgos_abiertos", '' FROM "inventario_activoinfraestructura";
DROP TABLE "inventario_activoinfraestructura";
ALTER TABLE "new__inventario_activoinfraestructura" RENAME TO "inventario_activoinfraestructura";
CREATE INDEX "inventario_activoinfraestructura_vlan_id_84138b9c" ON "inventario_activoinfraestructura" ("vlan_id");
CREATE INDEX "inventario_activoinfraestructura_zona_id_9c431343" ON "inventario_activoinfraestructura" ("zona_id");
--
-- Add field version to sistemainformacion
--
CREATE TABLE "new__inventario_sistemainformacion" ("activo_id" bigint NOT NULL PRIMARY KEY REFERENCES "inventario_activo" ("id") DEFERRABLE INITIALLY DEFERRED, "estado_operativo" varchar(4) NOT NULL, "backend" varchar(120) NOT NULL, "frontend" varchar(120) NOT NULL, "schema_bd" varchar(120) NOT NULL, "api_rest_nativa" bool NULL, "integracion_gateway" varchar(120) NOT NULL, "estado_documentacion" varchar(255) NOT NULL, "sistema_mca_equivalente" varchar(120) NOT NULL, "servidor_virtual" varchar(40) NOT NULL, "url" varchar(255) NOT NULL, "priorizar_analisis" varchar(5) NOT NULL, "gw_validacion_jwt" bool NULL, "gw_sso" bool NULL, "gw_cors" bool NULL, "gw_inyeccion_roles" bool NULL, "gw_refresh_token" bool NULL, "gw_balanceo_carga" bool NULL, "version" varchar(60) NOT NULL);
INSERT INTO "new__inventario_sistemainformacion" ("activo_id", "estado_operativo", "backend", "frontend", "schema_bd", "api_rest_nativa", "integracion_gateway", "estado_documentacion", "sistema_mca_equivalente", "servidor_virtual", "url", "priorizar_analisis", "gw_validacion_jwt", "gw_sso", "gw_cors", "gw_inyeccion_roles", "gw_refresh_token", "gw_balanceo_carga", "version") SELECT "activo_id", "estado_operativo", "backend", "frontend", "schema_bd", "api_rest_nativa", "integracion_gateway", "estado_documentacion", "sistema_mca_equivalente", "servidor_virtual", "url", "priorizar_analisis", "gw_validacion_jwt", "gw_sso", "gw_cors", "gw_inyeccion_roles", "gw_refresh_token", "gw_balanceo_carga", '' FROM "inventario_sistemainformacion";
DROP TABLE "inventario_sistemainformacion";
ALTER TABLE "new__inventario_sistemainformacion" RENAME TO "inventario_sistemainformacion";
--
-- Create model HistoricalActivo
--
CREATE TABLE "inventario_historicalactivo" ("id" bigint NOT NULL, "id_activo" varchar(30) NOT NULL, "nombre" varchar(255) NOT NULL, "descripcion" text NOT NULL, "clase" varchar(6) NOT NULL, "clasificacion_si" varchar(5) NOT NULL, "confidencialidad" integer NULL, "integridad" integer NULL, "disponibilidad" integer NULL, "valor" integer NULL, "nivel_riesgo" varchar(5) NOT NULL, "estado" varchar(4) NOT NULL, "fecha_registro" date NULL, "notas_seguridad" text NOT NULL, "propietario" varchar(150) NOT NULL, "custodio" varchar(150) NOT NULL, "area_responsable" varchar(150) NOT NULL, "procesa_datos_personales" bool NOT NULL, "rto" varchar(40) NOT NULL, "rpo" varchar(40) NOT NULL, "ciclo_vida" varchar(4) NOT NULL, "documentos_relacionados" text NOT NULL, "creado" datetime NOT NULL, "actualizado" datetime NOT NULL, "history_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "history_date" datetime NOT NULL, "history_change_reason" varchar(100) NULL, "history_type" varchar(1) NOT NULL, "history_user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model HistoricalActivoInfraestructura
--
CREATE TABLE "inventario_historicalactivoinfraestructura" ("tipo" varchar(60) NOT NULL, "subtipo" varchar(120) NOT NULL, "ip_segmento" varchar(120) NOT NULL, "modelo" varchar(120) NOT NULL, "serial_placa" varchar(120) NOT NULL, "fabricante_proveedor" varchar(150) NOT NULL, "fecha_adquisicion" date NULL, "fin_garantia" date NULL, "fin_soporte_eol" date NULL, "version_so_firmware" varchar(120) NOT NULL, "fecha_ultimo_escaneo" date NULL, "hallazgos_abiertos" integer NULL, "history_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "history_date" datetime NOT NULL, "history_change_reason" varchar(100) NULL, "history_type" varchar(1) NOT NULL, "activo_id" bigint NULL, "history_user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED, "vlan_id" bigint NULL, "zona_id" bigint NULL);
--
-- Create model HistoricalSistemaInformacion
--
CREATE TABLE "inventario_historicalsistemainformacion" ("estado_operativo" varchar(4) NOT NULL, "backend" varchar(120) NOT NULL, "frontend" varchar(120) NOT NULL, "schema_bd" varchar(120) NOT NULL, "api_rest_nativa" bool NULL, "integracion_gateway" varchar(120) NOT NULL, "estado_documentacion" varchar(255) NOT NULL, "sistema_mca_equivalente" varchar(120) NOT NULL, "servidor_virtual" varchar(40) NOT NULL, "url" varchar(255) NOT NULL, "priorizar_analisis" varchar(5) NOT NULL, "gw_validacion_jwt" bool NULL, "gw_sso" bool NULL, "gw_cors" bool NULL, "gw_inyeccion_roles" bool NULL, "gw_refresh_token" bool NULL, "gw_balanceo_carga" bool NULL, "version" varchar(60) NOT NULL, "history_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "history_date" datetime NOT NULL, "history_change_reason" varchar(100) NULL, "history_type" varchar(1) NOT NULL, "activo_id" bigint NULL, "history_user_id" integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX "inventario_historicalactivo_id_9c932e84" ON "inventario_historicalactivo" ("id");
CREATE INDEX "inventario_historicalactivo_id_activo_74978c5b" ON "inventario_historicalactivo" ("id_activo");
CREATE INDEX "inventario_historicalactivo_history_date_565d23f0" ON "inventario_historicalactivo" ("history_date");
CREATE INDEX "inventario_historicalactivo_history_user_id_dd07b134" ON "inventario_historicalactivo" ("history_user_id");
CREATE INDEX "inventario_historicalactivoinfraestructura_history_date_2c8bb936" ON "inventario_historicalactivoinfraestructura" ("history_date");
CREATE INDEX "inventario_historicalactivoinfraestructura_activo_id_d9e4bd9d" ON "inventario_historicalactivoinfraestructura" ("activo_id");
CREATE INDEX "inventario_historicalactivoinfraestructura_history_user_id_c0e5def6" ON "inventario_historicalactivoinfraestructura" ("history_user_id");
CREATE INDEX "inventario_historicalactivoinfraestructura_vlan_id_8ea17faf" ON "inventario_historicalactivoinfraestructura" ("vlan_id");
CREATE INDEX "inventario_historicalactivoinfraestructura_zona_id_1d72a989" ON "inventario_historicalactivoinfraestructura" ("zona_id");
CREATE INDEX "inventario_historicalsistemainformacion_history_date_75a242c5" ON "inventario_historicalsistemainformacion" ("history_date");
CREATE INDEX "inventario_historicalsistemainformacion_activo_id_be7cb8d0" ON "inventario_historicalsistemainformacion" ("activo_id");
CREATE INDEX "inventario_historicalsistemainformacion_history_user_id_70820018" ON "inventario_historicalsistemainformacion" ("history_user_id");
COMMIT;

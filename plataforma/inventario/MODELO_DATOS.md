# Modelo de datos — Inventario de Activos SGSI SUIIN

Esquema entidad-relación (SUIIN-SGSI-INV-001).

```
                        ┌─────────────────────────┐
                        │         ACTIVO          │  (entidad base)
                        ├─────────────────────────┤
                        │ id_activo (UNIQUE)      │
                        │ nombre                  │
                        │ descripcion             │
                        │ clase [INFRA|SIST]      │
                        │ clasificacion_si        │
                        │ confidencialidad (0-4)  │
                        │ integridad (0-4)        │
                        │ disponibilidad (0-4)    │
                        │ valor = C+I+D (auto)    │
                        │ nivel_riesgo            │
                        │ estado                  │
                        │ fecha_registro          │
                        │ notas_seguridad         │
                        └───────────┬─────────────┘
              1:1 ┌─────────────────┼─────────────────┐ 1:1
                  ▼                 │                 ▼
   ┌──────────────────────┐        │      ┌──────────────────────────┐
   │ ACTIVO_INFRAESTRUCTURA│       │      │   SISTEMA_INFORMACION     │
   ├──────────────────────┤        │      ├──────────────────────────┤
   │ tipo, subtipo        │        │      │ estado_operativo         │
   │ zona  ──► ZONA       │        │      │ backend, frontend        │
   │ ip_segmento          │        │      │ schema_bd                │
   │ vlan  ──► VLAN       │        │      │ api_rest_nativa          │
   │ modelo, serial_placa │        │      │ integracion_gateway      │
   └──────────────────────┘        │      │ estado_documentacion     │
                                    │      │ sistema_mca_equivalente  │
              M:N ┌─────────────────┤      │ servidor_virtual, url    │
                  ▼                 │      │ priorizar_analisis       │
   ┌──────────────────────┐        │      │ gw_validacion_jwt        │
   │    AMENAZA_MITRE      │        │      │ gw_sso, gw_cors          │
   ├──────────────────────┤        │      │ gw_inyeccion_roles       │
   │ codigo (T1486, TA…)  │        │      │ gw_refresh_token         │
   │ descripcion          │        │      │ gw_balanceo_carga        │
   └──────────────────────┘        │      └───────────┬──────────────┘
                                    │ M:N              │ M:N (con nivel)
                  ┌─────────────────┘                  ▼
                  ▼                          ┌──────────────────────┐
   ┌──────────────────────┐                 │      ACCESO_ROL       │
   │     CONTROL_ISO       │                 ├──────────────────────┤
   ├──────────────────────┤                 │ sistema ──► SISTEMA   │
   │ codigo (8.13, POL-…) │                 │ rol     ──► ROL_MCA   │
   │ descripcion          │                 │ nivel [C|M|L]         │
   └──────────────────────┘                 └──────────────────────┘
                                                        │
                                             ┌──────────────────────┐
                                             │       ROL_MCA         │
                                             ├──────────────────────┤
                                             │ sigla (CM, DOS, DBA) │
                                             │ nombre               │
                                             └──────────────────────┘
```

## Tablas

| Tabla | Propósito | Registros iniciales |
|---|---|---|
| `activo` | Entidad base de todo activo del SGSI | 38 |
| `activoinfraestructura` | Detalle hardware/red (1:1) | 19 |
| `sistemainformacion` | Detalle sistemas de software (1:1) | 19 |
| `zona` | Catálogo de zonas de red | auto |
| `vlan` | Catálogo de segmentos VLAN | auto |
| `amenazamitre` | Catálogo MITRE ATT&CK | 22 |
| `controliso` | Catálogo controles ISO 27002 / políticas | 21 |
| `rolmca` | Catálogo de roles organizacionales MCA | 9 |
| `accesorol` | Acceso sistema↔rol con nivel (C/M/L) | — |
| `activo_amenazas` | M:N activo↔amenaza | — |
| `activo_controles` | M:N activo↔control | — |

## Escalas de valoración

**C-I-D** (Confidencialidad, Integridad, Disponibilidad):
`0=N/A · 1=Bajo · 2=Medio · 3=Alto · 4=Crítico`
El campo `valor` se calcula automáticamente como C+I+D (rango 0–12).

**Nivel de riesgo:** Crítico · Alto · Medio · Bajo · Sin valorar

**Clasificación SI:** Altamente Confidencial · Confidencial · Uso Interno · Público

**Nivel de acceso (MCA):** C=Completo · M=Modificación · L=Lectura

---

## Ampliación v2 — Bitácora y campos nuevos

**Tablas históricas** (bitácora, una fila por cada versión de cada registro):

| Tabla | Versiona |
|---|---|
| `historicalactivo` | Activo (base) |
| `historicalactivoinfraestructura` | Detalle de infraestructura |
| `historicalsistemainformacion` | Detalle de sistemas |

Cada fila histórica guarda: `history_date` (cuándo), `history_user` (quién),
`history_type` (`+` creación, `~` modificación, `-` eliminación) y una copia
completa de los campos en ese momento. La diferencia campo a campo se calcula
comparando cada versión con la anterior (`diff_against`).

**Campos nuevos en `activo`:** propietario, custodio, area_responsable,
procesa_datos_personales, rto, rpo, ciclo_vida, documentos_relacionados,
y la relación reflexiva `dependencias` (activo↔activo, "depende de").

**Campos nuevos en `activoinfraestructura`:** fabricante_proveedor,
fecha_adquisicion, fin_garantia, fin_soporte_eol, version_so_firmware,
fecha_ultimo_escaneo, hallazgos_abiertos.

**Campo nuevo en `sistemainformacion`:** version.

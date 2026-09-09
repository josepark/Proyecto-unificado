# Sistema de Inventario de Activos SGSI — SUIIN (v2)

> **Plataforma unificada:** visión general e inicio rápido en [README.md](../README.md).

**Documento base:** SUIIN-SGSI-INV-001
**Alineación normativa:** ISO/IEC 27001:2022 · ISO/IEC 27002:2022 (Camino del SUIIN)
**Entidad:** SUIIN — Sistema Único de Información Indígena · CRIC

Sistematiza la matriz `Matriz_Activos_identificados.xlsx` en una base de datos
relacional con **gestión CRUD**, **bitácora de cambios** (trazabilidad ISO 8.15)
y **campos ampliados** de gobernanza, ciclo de vida, vulnerabilidades y continuidad.

---

## 1. Novedades v2

- **Gestión CRUD** (crear / editar / eliminar) desde dos interfaces:
  el panel de administración de Django y el tablero institucional SUIIN.
- **Bitácora de cambios** con `django-simple-history`: cada creación,
  modificación y eliminación queda registrada con usuario, fecha y el detalle
  campo por campo (valor anterior → valor nuevo). Es consultable por activo y
  de forma global. Satisface la trazabilidad exigida por ISO/IEC 27001 (8.15).
- **Campos ampliados del inventario:**
  - Gobernanza (ISO 5.9): propietario, custodio, área responsable.
  - Datos personales (Ley 1581/2012): marca estructurada.
  - Continuidad: RTO y RPO por activo.
  - Ciclo de vida: estado (planeado/producción/mantenimiento/retirado).
  - Infraestructura: fabricante/proveedor, fechas de adquisición, garantía y
    fin de soporte (EOL), versión de SO/firmware, fecha del último escaneo
    OpenVAS y número de hallazgos abiertos.
  - Trazabilidad documental: documentos SGSI relacionados (PTR, ARD, POL-SI…)
    y **dependencias entre activos** (para BIA/BCP).

## 2. Requisitos

- Python 3.10 o superior
- Dependencias de `requirements.txt`

## 3. Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py importar_matriz --file data/Matriz_Activos_identificados.xlsx
python manage.py populate_history --auto   # historial inicial de los registros importados
python manage.py createsuperuser
python manage.py runserver
```

> El paquete se entrega con `db.sqlite3` ya poblado (38 activos) y un usuario
> `admin` / `SUIIN2026#`. **Cambie esta contraseña antes de desplegar.**

## 4. Accesos

| Recurso | URL |
|---|---|
| Tablero institucional | http://127.0.0.1:8000/ |
| API REST (navegable) | http://127.0.0.1:8000/api/ |
| Panel de administración | http://127.0.0.1:8000/admin/ |

Para gestionar activos desde el tablero, inicie sesión primero en `/admin/login/`.
El botón "Nuevo activo" y las acciones Editar/Eliminar solo aparecen con sesión activa.

## 5. Gestión CRUD

**Opción A — Panel de administración de Django** (`/admin/`): alta, edición y
baja con validación, filtros, búsqueda, formularios anidados (infra/sistema) y
la pestaña de **historial** por registro.

**Opción B — Tablero institucional** (`/`): botón "Nuevo activo", y en la ficha
de cada activo los botones Editar, Eliminar y Ver historial. La pestaña
**Bitácora de cambios** muestra el registro consolidado del inventario.

## 6. API REST

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/activos/` | GET, POST | Listar / crear activos |
| `/api/activos/{id}/` | GET, PUT, PATCH, DELETE | Ver / editar / eliminar |
| `/api/activos/{id}/historial/` | GET | Bitácora de un activo |
| `/api/activos/estadisticas/` | GET | Agregados del tablero |
| `/api/bitacora/` | GET | Bitácora global consolidada |
| `/api/sesion/` | GET | Estado de autenticación |
| `/api/amenazas/` `/api/controles/` | GET | Catálogos |

Lectura libre; **escritura requiere sesión autenticada** (SessionAuthentication +
CSRF). En un cliente propio, envíe la cabecera `X-CSRFToken` con el valor de la
cookie `csrftoken`.

**Filtros** sobre `/api/activos/`: `?clase=`, `?nivel_riesgo=`,
`?clasificacion_si=`, `?estado=`, `?ciclo_vida=`, `?procesa_datos_personales=`,
`?search=`, `?ordering=-valor`.

**Creación/edición** — el serializador de escritura acepta el detalle anidado y
las relaciones por código:

```json
{
  "id_activo": "RED-023", "nombre": "Servidor QA", "clase": "INFRA",
  "clasificacion_si": "CONF", "confidencialidad": 3, "integridad": 3, "disponibilidad": 2,
  "propietario": "Coordinación SUIIN", "procesa_datos_personales": false,
  "amenazas_codigos": ["T1190", "T1078"],
  "controles_codigos": ["8.8", "POL-SI-009"],
  "infraestructura": {"tipo": "Servidor", "modelo": "Dell R340", "hallazgos_abiertos": 5}
}
```

## 7. Modelo de datos

Ver `MODELO_DATOS.md`. Se agregaron tres tablas históricas
(`HistoricalActivo`, `HistoricalActivoInfraestructura`,
`HistoricalSistemaInformacion`) que almacenan cada versión de los registros.

## 8. Datos cargados (estado inicial)

- 38 activos: 19 de infraestructura + 19 sistemas de información
- 22 amenazas MITRE ATT&CK, 21 controles ISO/POL, 9 roles MCA
- 11 activos en riesgo crítico · 8 en riesgo alto

## 9. Notas de seguridad para despliegue

- Cambiar `SECRET_KEY` (variable de entorno) y contraseña del admin.
- `DEBUG = False` y configurar `ALLOWED_HOSTS`.
- Migrar a PostgreSQL (coherente con el stack SUIIN).
- Proteger la API con JWT vía Keycloak (alineado con el gateway existente).
- Servir tras el firewall pfSense; no exponer directamente a internet.
- La bitácora es evidencia de auditoría: restrinja el borrado de tablas
  `Historical*` y considere respaldos periódicos.

---

## 10. Novedades v3 — CMDB extendida

El inventario ahora funciona como una **CMDB** (base de datos de gestión de
configuración) con las siguientes capacidades:

**Centros de datos y geolocalización.** Entidad `Datacenter` con tipo
(principal / mini / respaldo-DR / nube), nivel Tier (I–IV), dirección, ciudad y
**coordenadas geográficas**. La pestaña "Centros de datos" muestra un **mapa
interactivo** (Leaflet + OpenStreetMap) con la ubicación de cada sede y el
número de activos que aloja. Cada activo se enlaza a su datacenter y, para
infraestructura, a su **rack y unidad (U)**.

**Diagramas y topologías.** Entidad `Diagrama` con carga de archivos (imagen,
SVG o PDF) y tipo (topología de red, diagrama de rack, arquitectura, flujo,
plano). Se asocian a un datacenter y/o a activos específicos; se visualizan en
galería y en la ficha del activo.

**Hoja de vida del activo.** Entidad `EventoHojaVida`: historial cronológico
por equipo con tipo de evento (alta, mantenimiento preventivo/correctivo,
actualización de firmware, traslado, incidente, cambio de configuración,
garantía/RMA, baja), responsable, costo opcional y documento adjunto. Se
muestra como línea de tiempo en la ficha del activo. Es distinta de la bitácora:
la bitácora audita cambios en la base de datos; la hoja de vida es el registro
operativo del equipo.

### Endpoints v3

| Endpoint | Descripción |
|---|---|
| `/api/datacenters/` | CRUD de centros de datos |
| `/api/datacenters/{id}/activos/` | Activos alojados en un datacenter |
| `/api/diagramas/` | CRUD de diagramas (multipart para subir archivo) |
| `/api/diagramas/?activo={id}` | Diagramas de un activo |
| `/api/hojavida/` | CRUD de eventos de hoja de vida (multipart) |
| `/api/hojavida/?activo={id}` | Hoja de vida de un activo |

### Archivos subidos

Los diagramas y documentos se guardan en `media/` (`MEDIA_ROOT`). En producción,
sírvalos con el servidor web (nginx) y considere respaldarlos junto con la base
de datos. La carga de archivos requiere sesión no es obligatoria para lectura.

### Datos de ejemplo v3

Ejecute `python manage.py cargar_ejemplo_v3` para poblar dos centros de datos
(Popayán principal Tier II, Bogotá mini Tier III), ubicar los activos con su
rack/U, y crear una hoja de vida de ejemplo y un diagrama de topología.

### Sugerencias futuras (no implementadas aún)

- Exportar la hoja de vida de un activo a PDF como evidencia de auditoría.
- Generar un código QR por activo para etiquetado físico de equipos.

---

## 11. Novedades v4 — Tablero de alertas

Nueva pestaña **"Alertas"** que evalúa el estado del inventario y genera avisos
accionables. Cada alerta indica severidad (crítica / alta / media / baja) y
enlaza a la ficha del activo. Categorías:

- **Fin de soporte (EOL):** equipos con soporte vencido o que vence en ≤180 días.
- **Garantía:** garantías vencidas o que vencen en ≤90 días.
- **Mantenimiento preventivo:** activos sin mantenimiento en los últimos 12 meses
  o sin ningún mantenimiento registrado (según la hoja de vida).
- **Escaneo de vulnerabilidades:** activos sin escaneo o con último escaneo
  hace más de 90 días.
- **Hallazgos abiertos:** activos con hallazgos de vulnerabilidad pendientes.
- **Completitud del inventario:** activos críticos/altos sin propietario (ISO 5.9),
  sin valoración C-I-D completa, o sin centro de datos asignado.

La pestaña muestra un contador de alertas críticas/altas como distintivo (badge).

### Endpoint

| Endpoint | Descripción |
|---|---|
| `/api/alertas/` | Devuelve las alertas agrupadas por categoría con severidad |

Umbrales configurables en `inventario/views.py` (función `alertas`): 180 días
para EOL, 90 para garantía y escaneo, 365 para mantenimiento preventivo.

### Datos de ejemplo v4

`python manage.py cargar_ejemplo_alertas` completa fechas de EOL, garantía y
escaneo en algunos activos (no sobrescribe valores existentes) para que el
tablero muestre casos reales.

---

## 12. Novedades v5 — Catálogo MITRE ATT&CK e IDs automáticos

**Catálogo MITRE ATT&CK v19.1 integrado.** El catálogo de amenazas se enriqueció
con el dataset oficial de MITRE (712 entradas: 15 tácticas, 222 técnicas y 475
subtécnicas), cada una con nombre, descripción, tácticas asociadas, plataformas
y URL de referencia. Las amenazas que ya estaban vinculadas a los activos (desde
la matriz original) quedaron enriquecidas automáticamente con su nombre oficial.

Al crear o editar un activo, el campo de amenazas ofrece **autocompletado**
contra el catálogo (escribí un código o nombre y aparecen las coincidencias).
El catálogo es consultable por la API con búsqueda y filtro por tipo:

| Endpoint | Descripción |
|---|---|
| `/api/amenazas/?page_size=1000` | Catálogo MITRE completo |
| `/api/amenazas/?search=ransomware` | Búsqueda por código, nombre, descripción o táctica |
| `/api/amenazas/?tipo=TA` | Filtrar por tipo (TA=táctica, TE=técnica, ST=subtécnica) |

Reimportar el catálogo (por ejemplo, al salir una nueva versión de MITRE):

```bash
python manage.py importar_mitre --file data/enterprise-attack-v19_1.xlsx
```

**IDs auto-incrementales.** Al crear un activo ya no es necesario escribir el ID:
se genera automáticamente según la clase y el orden de creación —
`RED-0NN` para infraestructura y `SIS-0NN` para sistemas— tomando el siguiente
número disponible. En el formulario el campo queda opcional ("se generará
automáticamente"); si se deja vacío, el sistema asigna el consecutivo. La lógica
está en `Activo.siguiente_codigo()` y funciona igual desde el tablero y el admin.

---

## 13. Novedades v6 — Formulario diferenciado por clase

Al agregar o editar un activo, el formulario ahora **se adapta según la clase**:

- **Infraestructura de red:** muestra el bloque "Detalle de infraestructura de red"
  (tipo, IP/segmento, modelo, serial, rack y unidad, fabricante, firmware/SO,
  fin de soporte, hallazgos abiertos) y oculta el de sistema.
- **Sistema de información:** muestra el bloque "Detalle de sistema de información"
  (estado operativo, prioridad de análisis, backend, frontend, schema BD, servidor
  virtual, sistema MCA equivalente, versión, integración con Gateway, URL) y oculta
  el de infraestructura.

El cambio es dinámico: al seleccionar la clase en el desplegable, el formulario
alterna el bloque correspondiente. Al guardar, se envía únicamente el detalle
1:1 que corresponde (`infraestructura` o `sistema`), evitando registros vacíos.

---

## 14. Novedades v7 — Gestión y correlación de diagramas

La sección "Centros de datos" mejora la gestión de diagramas y topologías:

- **Editar y eliminar** cada diagrama: al hacer clic en una tarjeta se abre una
  vista previa ampliada con sus metadatos; desde allí (con sesión) se puede
  editar (título, tipo, versión, centro de datos, descripción y reemplazo
  opcional del archivo) o eliminar.
- **Correlación con el inventario:** en el formulario del diagrama se pueden
  seleccionar los activos con los que se relaciona. Esos diagramas aparecen
  automáticamente en la ficha de cada activo correlacionado, y desde la vista
  previa del diagrama se puede saltar a la ficha de cada activo vinculado.
- **Filtros:** búsqueda por título/descripción y filtros por centro de datos y
  por tipo de diagrama.
- **Ver activos por centro de datos:** cada tarjeta de datacenter tiene un botón
  que lista los activos alojados, con salto directo a su ficha.

Las tarjetas de diagrama muestran un indicador con el número de activos
correlacionados.

---

## 15. Novedades v8 — Motor de riesgos, roles, exportación y panel ejecutivo

Cuatro mejoras funcionales integradas en el tablero:

**1. Motor de riesgos (pestaña "Riesgos").** Calcula el riesgo por activo con
metodología probabilidad × impacto (ISO/IEC 27005): el impacto se deriva de la
valoración C-I-D y la probabilidad de la exposición a amenazas MITRE, hallazgos
de vulnerabilidad y controles aplicados. Muestra una **matriz de riesgo 5×5**,
la **cobertura de controles** ISO 27002, y una tabla del riesgo calculado por
activo comparado con el registrado. El botón "Recalcular" (rol Dinamizador/Admin)
aplica el nivel calculado a los activos y lo registra en la bitácora.

**2. Roles y permisos.** Tres roles vía grupos de Django: **Consultor** (solo
lectura), **Dinamizador** (crear/editar) y **Administrador** (control total,
incluye eliminar). El tablero muestra u oculta los botones según el rol, y la API
los aplica (`RolPermiso`). Página de **login propia** (`/login/`) para que los
roles no-staff puedan autenticarse. Usuarios de ejemplo creados con
`python manage.py crear_roles`:

| Usuario | Rol | Contraseña (cambiar) |
|---|---|---|
| admin | Administrador | SUIIN2026# |
| dinamizador | Dinamizador | Dinamizador2026# |
| consultor | Consultor | Consultor2026# |

**3. Exportación de evidencia y QR.** Exportar el inventario a **Excel**
(botón en la pestaña Inventario), la **hoja de vida de un activo a PDF** y un
**código QR** por activo (botones en la ficha) para etiquetado físico de equipos.

**4. Panel ejecutivo (pestaña "Panel ejecutivo").** Indicadores de madurez del
SGSI: completitud del inventario (valoración C-I-D, propietarios, ubicación,
controles), distribución de riesgo, cobertura de controles y un índice de madurez
compuesto. Además, la pestaña "Bitácora y auditoría" incorpora la **auditoría de
accesos** (inicios de sesión registrados con usuario, IP y fecha).

### Endurecimiento y despliegue

La configuración ahora se lee de variables de entorno (ver `.env.example`):
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, y variables de
PostgreSQL. Con `DJANGO_DEBUG=False` se activan cabeceras de seguridad (HSTS,
cookies seguras, SSL redirect, X-Frame-Options). En desarrollo no hay que definir
nada: los valores por defecto funcionan.

### Endpoints nuevos

| Endpoint | Descripción |
|---|---|
| `/api/riesgos/` | Matriz de riesgo y riesgo por activo |
| `/api/riesgos/recalcular/` | Aplica el nivel calculado (POST, rol edición) |
| `/api/cobertura/` | Cobertura de controles ISO |
| `/api/dashboard-ejecutivo/` | Métricas del panel ejecutivo |
| `/api/accesos/` | Auditoría de accesos |
| `/api/exportar/inventario.xlsx` | Inventario en Excel |
| `/api/activos/{id}/hojavida.pdf` | Hoja de vida en PDF |
| `/api/activos/{id}/qr.png` | Código QR del activo |
| `/login/` · `/logout/` | Autenticación propia del tablero |

# SUIIN-SGSI-RIESGOS

**Sistema de Gestión de Riesgos de Seguridad de la Información**
Consejo Regional Indígena del Cauca (CRIC) · UAIIN · SUIIN

> **Este módulo ahora forma parte de la Plataforma SUIIN unificada** (junto al
> Inventario de Activos y la Matriz RBAC) y consume su catálogo de activos desde
> ahí en vez de mantener uno propio — ver `../README-DESPLIEGUE.md`, sección 11,
> para el despliegue integrado (recomendado) y el comando
> `sincronizar_activos_inventario`. Lo que sigue en este documento describe el
> módulo en sí y también sirve para ejecutarlo de forma independiente si hace
> falta (ver sección 3 para ese caso).

Sistematización en Django + React de dos matrices de riesgos originalmente mantenidas en
Excel:

1. `SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx` — análisis cruzado de 38 activos ×
   OpenVAS × Nmap × Red Team (10 hojas).
2. `SUIIN_SGSI_CENSO_PlanTratamiento_de_Riesgos.xlsx` — Plan de Tratamiento de Riesgos
   (PTR) del engagement Red Team sobre el host CENSO.

La sistematización queda abierta a seguir creciendo: los activos, vulnerabilidades y
riesgos se pueden crear y editar directamente desde la aplicación (no solo por
importación de Excel), y el nivel de riesgo de cada activo se recalcula
automáticamente cuando cambian sus vulnerabilidades o riesgos asociados.

---

## 1. Arquitectura

```
suiin-riesgos/
├── backend/                   Django 6 + Django REST Framework
│   ├── suiin_riesgos_config/  Configuración del proyecto
│   ├── riesgos/                App con los 8 modelos, API REST y comando de importación
│   └── db.sqlite3              Base de datos SQLite — YA INCLUYE los datos de sus 2 Excel
└── frontend/                  React 19 + Vite + Tailwind v4
    └── src/
        ├── pages/              Panel general, Activos, Riesgos contextuales,
        │                       Red Team, Plan de tratamiento
        ├── components/         Heatmap ISO 27005, badges de riesgo, layout
        └── api/                Cliente Axios + endpoints
```

La base de datos SQLite incluida (`backend/db.sqlite3`) **ya tiene cargados los datos
de sus dos archivos originales** — puede clonar el proyecto y tenerlo funcionando en
minutos sin reimportar nada. Vea la sección 4 para reimportar cuando actualice los Excel.

---

## 2. Modelo de datos: de 10+3 hojas a 8 entidades + catálogo ISO 27001

Las hojas del Excel original mezclan datos crudos con vistas derivadas y repiten el
mismo hallazgo en más de una pestaña. La sistematización normaliza eso en 8 entidades:

| Modelo | Sustituye a | Nota |
|---|---|---|
| `Activo` | Hoja 01 + campos de hoja 04 y 06 | Un registro por activo del inventario |
| `PuertoServicio` | Hoja 03 | Puertos/servicios Nmap por activo |
| `Vulnerabilidad` | Hojas 02 **+** 09 (fusionadas) | Mismo hallazgo técnico, antes duplicado en dos vistas: hoja 02 (OpenVAS) y hoja 09 (riesgo). Aquí es una sola fila con ambos conjuntos de campos |
| `RiesgoActivo` | Hoja 08 | Riesgo agregado por activo (no por hallazgo) |
| `RiesgoContextual` | Hoja 10 | Riesgos organizacionales RC-01..RC-07 (no técnicos) |
| `CampanaRedTeam` | Hoja 07 | Una campaña por host objetivo |
| `PlanTratamientoRiesgos` | Portada del PTR | Encabezado del plan (referencia, fechas, herramientas) |
| `AccionTratamiento` | Hojas "Matriz PTR" **+** "Plan de Acción" **+** "Seguimiento" (fusionadas) | Mismo riesgo R-XX en tres momentos de su ciclo de vida en el Excel original; aquí es un solo registro con estado y % de avance |

Las hojas 04 (`Activos_Sin_Cobertura`), 05 (`Activos_Criticos_Consolidado`) y 06
(`SI_vs_Vulns_Servidor`) del análisis original son **vistas derivadas** — no se
modelan como tablas propias porque se reconstruyen con filtros/consultas sobre
`Activo` y `Vulnerabilidad` (así se hace, por ejemplo, en el endpoint de dashboard).

El nivel de riesgo (`nivel_riesgo`) se calcula siempre de forma determinística a
partir de `Probabilidad × Impacto` (escala ISO/IEC 27005: ≥20 Crítico, 12–19 Alto,
6–11 Medio, 1–5 Bajo), en vez de copiar el texto libre de la columna "Nivel" del
Excel — así el sistema queda consistente hacia adelante aunque el Excel original
tuviera alguna inconsistencia puntual en la clasificación manual.

Además, `Activo.riesgo_matriz` (el nivel de riesgo agregado que se ve en las tablas
y el dashboard) se recalcula automáticamente vía señales de Django cada vez que se
crea, edita o elimina una `Vulnerabilidad` o `RiesgoActivo` de ese activo — toma el
nivel más alto entre todos sus hallazgos. Esto es lo que permite que el sistema
siga siendo confiable a medida que se editan datos desde el frontend, en vez de
quedar con el valor congelado del último Excel importado.

### Cumplimiento ISO 27001 (Anexo A)

Un noveno modelo, `ControlISO27001`, mantiene el catálogo completo de los 93
controles del Anexo A de ISO/IEC 27001:2022 (37 organizacionales, 8 de personas,
14 físicos, 34 tecnológicos). No depende de ningún Excel — es la taxonomía fija
del estándar, sembrada con:

```bash
python manage.py cargar_catalogo_iso27001
```

`AccionTratamiento` y `RiesgoContextual` tienen un vínculo estructurado
(`controles_iso_vinculados`, M2M) hacia este catálogo, además de los campos de
texto libre originales heredados del Excel (`control_iso27001` / `controles_iso`),
que se conservan para no perder los datos ya importados. Un control se considera
"con evidencia" si tiene al menos una acción de tratamiento o riesgo contextual
vinculado — eso es lo que calcula `GET /api/cumplimiento/resumen/` para dar la
cobertura real del SoA, por categoría y global. Página **Cumplimiento** en el
frontend.

### Alertas de vencimiento

`AccionTratamiento`, `RiesgoActivo` y `RiesgoContextual` calculan automáticamente
si están vencidos o próximos a vencer (7 días) a partir de una fecha real —
`AccionTratamiento.fecha_limite` y `RiesgoContextual.fecha_limite` (se conserva
`fecha_limite_texto`/`plazo` para los plazos relativos heredados del Excel
original, ej. "0–4 h post-incidente"; en `RiesgoContextual` ese texto libre
puede traer varios subplazos a la vez, así que `fecha_limite` es para el ítem
más urgente, a criterio del analista — no se intenta parsear el texto) y
`RiesgoActivo.fecha_objetivo` (ya existía). Los registros cerrados/aceptados
nunca cuentan como vencidos. El endpoint `GET /api/alertas/resumen/` agrupa todo
esto, y el dashboard del frontend muestra un aviso cuando hay algo pendiente.

`RiesgoContextual` también ganó un campo `estado` estructurado (mismas opciones
que el resto del sistema: Pendiente/En progreso/Cerrado/Falso positivo/Aceptado)
— antes solo tenía `estado_actual`, texto libre sin validar, heredado del Excel
y ahora conservado igual que `plazo`.

Para el envío por correo, `python manage.py enviar_alertas_vencimiento` construye
un resumen y lo envía a `ALERTAS_EMAIL_DESTINATARIOS` (ver `.env.example`) — no
envía nada si no hay vencimientos, para no generar ruido diario. Pensado para
correr periódicamente vía cron:

```bash
# Todos los días laborales a las 8:00 a.m.
0 8 * * 1-5 cd /ruta/backend && venv/bin/python manage.py enviar_alertas_vencimiento
```

Sin configurar `DJANGO_EMAIL_BACKEND`, los correos se imprimen en la consola —
útil para probar el contenido sin necesitar un servidor SMTP real.

### Adjuntos de evidencia

`Evidencia` es un modelo genérico (`GenericForeignKey`) que se puede adjuntar a
`Activo`, `Vulnerabilidad`, `RiesgoActivo`, `RiesgoContextual` o
`AccionTratamiento` — una sola tabla en vez de repetir un modelo de archivos por
cada entidad. Es lo que un auditor ISO 27001 suele pedir ver junto al riesgo o la
acción de tratamiento: la prueba concreta (captura de pantalla, reporte de
escaneo, acta, PDF).

Validaciones aplicadas en el servidor, no solo en el frontend: extensión
permitida (`.jpg .jpeg .png .gif .webp .pdf .doc .docx .xls .xlsx` — deliberadamente
sin ejecutables ni scripts), máximo 10 MB por archivo, y una **whitelist explícita**
de qué modelos pueden recibir evidencia (`MODELOS_CON_EVIDENCIA` en
`riesgos/models.py`) — no se puede adjuntar un archivo a, por ejemplo, la tabla de
usuarios, aunque técnicamente exista un `ContentType` para ella.

En desarrollo, los archivos se guardan en `backend/media/` (fuera de git) y Django
los sirve directamente. **En producción, no debe usarse el servidor de desarrollo
de Django para servir archivos subidos por usuarios** — configure Nginx (o un
bucket S3/equivalente) para servir `MEDIA_ROOT` en la ruta `MEDIA_URL`.

---

## 3. Instalación

### Requisitos

- Python 3.12+
- Node.js 20+

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# La base de datos ya viene con sus datos cargados — solo aplique migraciones
# por si acaso (no debería crear nada nuevo si db.sqlite3 ya está presente):
python manage.py migrate

# El catálogo de 93 controles ISO 27001 (Anexo A) también viene precargado en
# db.sqlite3. Si arranca desde una base de datos nueva, siémbrelo con:
python manage.py cargar_catalogo_iso27001

# Cree un usuario para entrar al panel de administración /admin:
python manage.py createsuperuser

python manage.py runserver 0.0.0.0:8000
```

API disponible en `http://localhost:8000/api/` · Panel de administración en
`http://localhost:8000/admin/`.

### Pruebas automatizadas

```bash
cd backend
source venv/bin/activate
python -m pytest riesgos/tests/
```

258 pruebas cubren la lógica de negocio central: cálculo de Score/Nivel de riesgo
(ISO/IEC 27005), las señales de recálculo automático, autenticación y permisos,
CRUD de cada entidad (incluyendo M2M y trazabilidad de origen), los endpoints de
dashboard/cumplimiento, el historial de auditoría, y las funciones auxiliares del
importador de Excel (parseo de fechas, normalización de texto). No dependen de
ningún archivo externo — usan una base de datos de prueba aislada
(`--reuse-db`, ver `pytest.ini`) que nunca toca `db.sqlite3`.

### Pruebas automatizadas del frontend

```bash
cd frontend
npm install
npm run test        # una sola corrida
npm run test:watch  # modo watch, para ir escribiendo
```

Base agregada el 2026-08-25 (Vitest + React Testing Library — mismo criterio
que ya usa Vite, sin herramientas nuevas que aprender). Hasta esa fecha, el
frontend (9 páginas, ~3.700 líneas) no tenía ninguna prueba automatizada —
todo lo que ya funciona ahí (revalidación de sesión, operaciones en lote,
"Generar acción" con sus tres orígenes) solo estaba verificado por pruebas
manuales con navegador, una vez, durante el desarrollo — sin ninguna red que
atrapara una regresión futura.

117 pruebas cubren, por ahora, las ocho piezas de más riesgo real:

- `context/AuthContext.test.jsx` (12): la distinción entre un JWT de sesión
  única silenciosa (se re-verifica contra el Inventario, cada 3 minutos y al
  montar) y un login manual — cuenta propia de riesgos, o credenciales del
  Inventario tecleadas a mano (NO se re-verifica, es intencionalmente
  independiente de que exista una cookie del Inventario en ese navegador).
- `components/RutaProtegida.test.jsx` (6): el bloqueo de rutas sin sesión, y
  que el modo embebido no ofrezca su propio botón de login (mismo motivo que
  en el pie de la barra lateral — es la misma sesión, un botón aparte
  confunde).
- `components/GenerarAccionModal.test.jsx` (15): las tres ramas de origen
  (vulnerabilidad / riesgo por activo / riesgo contextual) — qué campo de
  cada objeto de origen precarga cada una, que el payload de guardado solo
  lleva el `origen_*` correcto (los otros dos en null), la conversión del
  plan elegido a número, y los cuatro valores por defecto
  (`opcion_tratamiento`/`fase`/`estado`/`porcentaje_avance`) que se
  corrigieron para los tres orígenes por igual. `EntityForm` (componente
  genérico y reusado por casi toda la app) se simula con un doble mínimo
  que expone justo lo que este componente le entrega, para no reimplementar
  EntityForm ni acoplarse a su render interno — cubierto aparte, ver abajo.
- `components/EntityForm.test.jsx` (28): los 9 tipos de campo (uno por
  widget), los valores por defecto según el tipo, que `initialValues` los
  sobrescriba, la conversión a `null` de fecha/número/`fkId` vacíos antes de
  enviar (`sanitize` — la pieza más sutil del componente), la agrupación
  por `section`, y el formato de los tres tipos de error que puede devolver
  el backend (`{detail}`, validación DRF `{campo: [msgs]}`, string plano).
  `CatalogoCombobox` y `MitreMultiSelect` se simulan por el mismo motivo que
  EntityForm en el archivo anterior — cada uno hace sus propias llamadas a
  la API y merece su propio archivo de pruebas.
- `components/CatalogoCombobox.test.jsx` (13): sugiere lo ya cargado y
  filtra al escribir, elegir una sugerencia la pone como valor, y — la
  pieza de negocio real del componente — que un valor nuevo se registre en
  el catálogo solo al perder el foco, pero **no** si coincide exactamente
  (sin distinguir mayúsculas) con algo que ya existe, para no duplicar. El
  registro fallido (ej. sin sesión) no debe borrar lo escrito.
- `components/MitreMultiSelect.test.jsx` (12): arma y desarma la cadena de
  códigos según el separador (`/` por defecto, ` · ` en
  `tecnica_mitre_cwe`), la búsqueda con debounce de 200 ms (con
  temporizadores simulados — no espera 200ms reales por prueba), que no
  duplique un código ya agregado, y que Enter/coma agreguen el texto tal
  cual aunque no esté en el catálogo MITRE (para códigos CWE).
- `pages/Vulnerabilidades.test.jsx` (20): la primera página completa
  cubierta, no solo un componente reusado. Carga y estados (vacío/error),
  que cada filtro mande el parámetro correcto a la API, selección
  individual y "seleccionar todos", **las operaciones en lote en sí**
  (cambiar estado o tratamiento manda los ids correctos y el campo
  correcto — nunca confunde uno con el otro), que cambiar un filtro limpie
  la selección, y el flujo CRUD completo (crear, editar con el id correcto,
  eliminar con confirmación previa, generar acción con el origen correcto).
  `EntityForm` y `GenerarAccionModal` se simulan (ya tienen sus propios
  archivos); `useAuthGuard` también, para poder probar tanto el caso normal
  como el de "sin sesión, no se ejecuta la acción" sin necesitar todo el
  `AuthContext` real.
- `components/Layout.test.jsx` (11): las cuatro combinaciones de
  embebido/directo × con/sin sesión — específicamente, que el bloque de
  sesión propio (usuario + "Cerrar sesión", o "Iniciar sesión") no se
  muestre en absoluto en modo embebido, en ningún estado de autenticación,
  para no duplicar lo que ya muestra el Inventario arriba. Ver §4.13.

**Hallazgo real al escribir estas pruebas, no solo cobertura:** el
`<label>` de cada campo (salvo checkbox) no estaba asociado a su control —
ni por `htmlFor`/`id`, ni por anidamiento. No es solo un problema para
`getByLabelText`: un lector de pantalla tampoco anunciaba el campo
correctamente, y hacer clic en la etiqueta no enfocaba el control. Se
corrigió en el componente real (no solo rodeando el problema en las
pruebas) y se confirmó con navegador real, en la aplicación completa: clic
en la etiqueta "Probabilidad" de un formulario real ahora sí mueve el foco
al `<input>` correspondiente.

**Verificado seis veces que la suite atrapa bugs reales, no solo que pasa
porque no prueba nada:**
- Se reemplazó `AuthContext.jsx` por la versión vieja (sin la
  re-verificación contra el Inventario) — 5 de las 12 pruebas fallaron, la
  más reveladora exactamente la que reproduce el reporte original ("si el
  Inventario ya cerró sesión, se descarta el JWT aunque no haya vencido").
- Se reemplazó `GenerarAccionModal.jsx` por la versión sin los cuatro
  valores por defecto — fallaron exactamente las 3 pruebas escritas para
  eso (una por cada origen), confirmando que el bug afectaba a los tres por
  igual, como ya se sabía.
- Se reemplazó `sanitize()` de `EntityForm.jsx` por una versión sin la
  conversión a `null` — fallaron exactamente las 3 pruebas de esa
  conversión (fecha, número, `fkId`), y ninguna de las otras 25 se vio
  afectada, confirmando que están bien aisladas entre sí.
- Se quitó el chequeo de coincidencia exacta de `CatalogoCombobox.jsx` —
  fallaron exactamente las 2 pruebas de no-duplicar.
- Se quitó el chequeo de duplicados de `MitreMultiSelect.jsx` — falló
  exactamente 1 prueba, la de no-duplicar; las otras 11 no se vieron
  afectadas.
- Se quitó el `setSeleccionados(new Set())` tras aplicar en lote en
  `Vulnerabilidades.jsx` — falló exactamente 1 prueba, la que verifica que
  la selección se limpia después; las otras 19 no se vieron afectadas.

Las seis veces se restauró la versión correcta después y se confirmó que
toda la suite vuelve a pasar completa.

Sigue pendiente: el resto de las páginas (Activos, Riesgos contextuales,
Campañas Red Team, Plan de tratamiento, Cumplimiento, Catálogos, Panel
general, detalle de Activo) — esta es la base, no el final.

Con cobertura:

```bash
python -m pytest riesgos/tests/ --cov=riesgos --cov-report=term-missing
```

**Nota sobre el importador de Excel:** se prueban sus funciones auxiliares
(`parse_fecha_relativa`, `leer_hoja`, normalización de texto) de forma unitaria,
pero no el flujo completo de las 13 hojas contra un archivo sintético — construir
y mantener un fixture fiel al formato exacto de esas hojas tenía un costo/riesgo
mayor que el valor que aportaba. Si el formato del Excel cambia en el futuro, siga
verificando el resultado de `importar_matrices` con los conteos esperados (ver §4)
antes de confiar en una corrida nueva.

### Autenticación (necesaria para crear/editar/eliminar)

La lectura de la API es libre; crear, editar o eliminar registros requiere sesión.
El superusuario que creó arriba con `createsuperuser` sirve como esa cuenta — inicie
sesión desde el botón **"Iniciar sesión"** al pie de la barra lateral del frontend.
Internamente usa autenticación por token (`rest_framework.authtoken`): el login
(`POST /api/auth/login/`) devuelve un token que el frontend guarda en el navegador y
adjunta a cada request de escritura.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Disponible en `http://localhost:5173`. Por defecto apunta a `http://localhost:8000/api`
(ver `frontend/.env.example` si necesita cambiarlo).

### Producción

- Backend: sirva con `gunicorn suiin_riesgos_config.wsgi` detrás de Nginx; configure
  `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS` en `.env`
  (ver `backend/.env.example`). Para integrarlo al stack **SUIIN Platform**
  (docker-compose con PostgreSQL) defina `DJANGO_DB_ENGINE=postgresql` y las
  variables `DJANGO_DB_*` correspondientes.
- Frontend: `npm run build` genera `frontend/dist/` como sitio estático, listo para
  servir desde Nginx o el mismo contenedor del stack SUIIN.

---

## 4. Reimportar cuando actualice los archivos Excel

El comando es **idempotente y protege sus ediciones manuales**: puede correrlo
tantas veces como quiera tras corregir datos en el Excel, sin duplicar registros
(usa una clave natural por entidad — `ID Activo` / `ID Riesgo` / `RC-XX` / `R-XX`
/ `(activo, nombre, IP)` para vulnerabilidades) y **sin sobrescribir nada que haya
sido editado desde la aplicación** después de la última importación.

Cada registro que toca el importador guarda cuándo fue importado por última vez
(`importado_en`). Si detecta que `actualizado_en` es más reciente que
`importado_en` — es decir, que alguien lo tocó desde la app después de esa
importación — lo **protege** y lo deja intacto, en vez de sobrescribirlo con lo
que diga el Excel. Esto también aplica a `Vulnerabilidad`: antes de este mecanismo,
reimportar borraba y recreaba TODAS las vulnerabilidades del activo, lo que
destruía sin aviso cualquier hallazgo creado manualmente o progreso de tratamiento
registrado; ahora usa la misma protección (única excepción: `PuertoServicio`, que
sí se reemplaza por completo en cada reimportación — es una foto del último escaneo
Nmap, no una entidad con ciclo de vida propio, así que tiene sentido que el Excel
más reciente gane siempre ahí).

```bash
cd backend
source venv/bin/activate

# Solo la matriz de riesgos:
python manage.py importar_matrices --matriz-riesgos /ruta/SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx

# Solo un PTR (puede repetir --ptr para varios archivos):
python manage.py importar_matrices --ptr /ruta/SUIIN_SGSI_CENSO_PlanTratamiento_de_Riesgos.xlsx

# Ambos a la vez:
python manage.py importar_matrices \
  --matriz-riesgos /ruta/SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx \
  --ptr /ruta/SUIIN_SGSI_CENSO_PlanTratamiento_de_Riesgos.xlsx
```

El comando termina con un resumen (`N creado(s), M actualizado(s)`) y, si aplica,
la lista exacta de qué se protegió y por qué:

```
⚠ 1 registro(s) protegido(s) — editados manualmente desde la última importación, NO se sobrescribieron:
    · AccionTratamiento SUIIN-SGSI-PTR-001 v1.0 · R-01
  Use --forzar-sobrescritura si de verdad quiere que el Excel gane sobre esas ediciones (se perderán).
```

Si de verdad quiere que el Excel gane sobre ediciones hechas en la app (por
ejemplo, corrigió un typo en el Excel original y quiere que se propague), agregue
`--forzar-sobrescritura` — pero tenga presente que esas ediciones manuales se
pierden sin posibilidad de recuperarlas desde la app (sí quedan en el historial de
auditoría de Django admin, si necesita consultarlas después).

**Importante:** un PTR se asocia a una `CampanaRedTeam` existente, así que si va a
importar un PTR nuevo (ej. de MINGA-PARA-TEJER), importe primero la matriz de
riesgos (o cree la campaña manualmente en `/admin`) para que la campaña exista.

---

## 4.1. Sincronizar el catálogo de activos desde el Inventario

Si este módulo corre dentro de la Plataforma SUIIN unificada (ver
`../README-DESPLIEGUE.md` sección 11), el catálogo de activos ya no se
mantiene aquí — se trae del Inventario:

```bash
python manage.py sincronizar_activos_inventario
python manage.py sincronizar_activos_inventario --url http://otro-host:8000/api
python manage.py sincronizar_activos_inventario --forzar-sobrescritura
```

Usa `INVENTARIO_API_URL` (por defecto `http://localhost:8000/api`, o
`http://inventario:8000/api` dentro de docker-compose) y el mismo mecanismo
de protección que el importador de Excel — un activo editado manualmente en
Riesgos después de la última sincronización no se sobrescribe, salvo que se
use `--forzar-sobrescritura`. El comando reporta qué activos vinculó por
nombre (no por código exacto) para que se pueda auditar la correlación, y
cuáles quedaron sin vincular tras la corrida.

## 4.2. Catálogo de valores parametrizable

Cinco campos de texto libre que se repiten mucho al capturar datos —
`Activo.tipo`, `RiesgoActivo.responsable_sugerido`, `AccionTratamiento.fuente`,
`AccionTratamiento.responsable` y `AccionTratamiento.plazo` — ahora tienen un
combo respaldado por `CatalogoValor` en vez de un campo de texto vacío cada
vez. No es un `choices=` fijo en el modelo: el propio analista agrega o
desactiva valores desde la página **Catálogos** de la app, sin necesitar un
cambio de código — el campo real del modelo sigue siendo texto libre, el
catálogo solo alimenta las sugerencias del formulario.

Se decidió deliberadamente **no** convertir a catálogo los campos narrativos
de `RiesgoContextual` (`actor_amenaza`, `responsable`, `ley_marco_legal`):
son textos largos, casi únicos por registro (verificado contra los 7 riesgos
contextuales reales — ninguno se repite), así que un desplegable no habría
ayudado ahí, solo habría sido fricción de más.

```bash
python manage.py sembrar_catalogos
```
Puebla el catálogo con los valores que ya están en uso en los datos reales
(idempotente — correrlo de nuevo solo agrega valores nuevos que hayan
aparecido desde la última vez, no duplica ni borra nada).

## 4.3. Catálogo MITRE ATT&CK (mismo catálogo que el Inventario)

`Activo.mitre_attck` y `AccionTratamiento.tecnica_mitre_cwe` tienen un
selector múltiple que busca en vivo contra el catálogo MITRE ATT&CK real del
Inventario (`/api/amenazas/` — 712 entradas: 15 tácticas, 222 técnicas, 475
subtécnicas), en vez de tener que recordar y escribir cada código a mano. Se
sincroniza un espejo local de solo lectura (`TecnicaMitre`) con:

```bash
python manage.py sincronizar_tecnicas_mitre
```

A diferencia de `sincronizar_activos_inventario`, este no usa el mecanismo de
protección contra ediciones manuales — es catálogo de referencia externo
(viene de MITRE, vía el Inventario), no algo que se edite campo a campo desde
riesgos, así que un upsert directo es correcto.

`AccionTratamiento.tecnica_mitre_cwe` también recibe códigos **CWE** (Common
Weakness Enumeration — verificado contra los datos reales: `"T1041 ·
CWE-306"` mezcla ambos catálogos en el mismo campo, según la naturaleza del
hallazgo). El selector no bloquea esto: cualquier código que no esté en el
catálogo MITRE igual se puede agregar tal cual, como una ficha más — solo
pierde el autocompletado de nombre/táctica que sí tienen los códigos MITRE.

## 4.4. Vista global de vulnerabilidades

Hallazgo del análisis de gestionabilidad del 2026-08-24: con 225
vulnerabilidades repartidas en 38 activos, no había manera de ver "todas las
críticas sin tratar" de un tirón — antes solo se podían ver/editar entrando
primero al detalle de un activo específico. La página **Vulnerabilidades**
(`/vulnerabilidades`) las cruza todas, filtrable por nivel de riesgo,
severidad OpenVAS y estado, con el mismo flujo de creación/edición/generar
acción de tratamiento que ya existía dentro del detalle de activo — no se
duplicó lógica, se reutilizaron `EntityForm`, `vulnerabilidadFields` y
`GenerarAccionModal` tal cual. No requirió ningún cambio en el backend: el
endpoint `/api/vulnerabilidades/` ya soportaba filtrar y buscar sin acotar
por activo — verificado en vivo con navegador real: 225 filas al cargar, 94
al filtrar por "Crítico" (coincide exacto con el conteo real de la base).

## 4.5. Operaciones en lote sobre vulnerabilidades

Segundo hallazgo del mismo análisis: ningún listado del sistema tenía forma
de editar varios registros a la vez — cambiar el estado de 10 vulnerabilidades
tras un ciclo de parches significaba abrirlas una por una. La página
Vulnerabilidades ahora tiene casillas de selección y una barra de acción que
aplica `estado` o `tratamiento` a todas las seleccionadas de una vez, vía
`POST /api/vulnerabilidades/bulk-actualizar/`.

**Decisión de diseño importante:** el endpoint guarda cada objeto por
separado (`for obj in queryset: obj.save()`), no un `QuerySet.update()` en
una sola pasada — esto es a propósito. `django-simple-history` solo registra
el historial en la señal `post_save` de cada `.save()` individual; un
`.update()` masivo la salta por completo y dejaría el cambio en lote sin
ningún rastro de auditoría, algo que no es aceptable en un sistema donde el
historial es parte del cumplimiento ISO 27001. Verificado con datos reales:
tras aplicar un cambio en lote a 2 vulnerabilidades reales, cada una quedó
con su propio registro de historial individual, no uno solo compartido.

Solo `estado` y `tratamiento` están en la lista blanca de campos que se
pueden cambiar en lote (protegido también con una prueba automatizada que
confirma que un campo fuera de esa lista, como el nombre del hallazgo, se
rechaza). Requiere el mismo rol de escritura que el resto del sistema — un
Consultor no puede usarlo.

## 4.6. Catálogo para "Solución recomendada"

Tercer hallazgo: `Vulnerabilidad.solucion_recomendada` se quedó fuera de la
ronda original del catálogo de valores (§4.2) por no haber hecho entonces un
barrido exhaustivo de todos los campos de texto libre. Con datos reales: 225
valores, solo 50 distintos — la recomendación de OpenVAS de deshabilitar
TLSv1.0/1.1 se repite 78 veces. Se agregó la categoría `SOLUCION_VULN` y se
sembró con esos 50 valores reales.

Como estos textos son mucho más largos que los de las demás categorías
(hasta 400 caracteres, algunos varios párrafos), el campo `CatalogoValor.valor`
pasó de `CharField(max_length=255)` a `TextField` — 59 de los 225 valores
reales ya pasaban ese límite de 255 y se habrían truncado. `CatalogoCombobox`
ahora acepta una prop `multiline` que cambia el campo de una sola línea a un
`<textarea>`, con las sugerencias del desplegable recortadas a 140 caracteres
para no mostrar párrafos completos ahí — el resto de las categorías (cortas)
no se vieron afectadas.

## 4.7. Sesión: sin login duplicado dentro del panel embebido

Hallazgo real, con captura: dentro del panel embebido en el Inventario, si la
sesión única (SSO) todavía no había terminado de resolverse, el pie de la
barra lateral de riesgos mostraba su propio botón "Iniciar sesión" — daba la
impresión equivocada de que este módulo pide credenciales aparte de las del
Inventario, cuando es exactamente la misma sesión (JWT único). Ese botón ya
no aparece en modo embebido sin sesión; solo se muestra en acceso directo
(`/riesgos/` fuera del Inventario), donde sí hace falta un login manual
propio. El estado autenticado (usuario + cerrar sesión) sigue visible en
ambos modos — eso no era confuso, solo el botón de "entrar" aparte lo era.

Verificado con navegador real en los tres casos: embebido sin sesión (sin
botón), embebido con sesión (usuario visible, sin botón), y acceso directo
sin sesión (el botón sí aparece, como debe ser en modo independiente).

## 4.8. El progreso del PTR en pantalla no coincidía con el del backend

Seguimiento a un fix anterior (§ el de `porcentaje_avance_global` contando
`ACEPTADO`): ese arreglo vivía solo en el backend — el componente
`ProgresoGlobal` de la página Plan de tratamiento tenía su **propio** cálculo
en el frontend, duplicado, con el mismo bug (excluía `ACEPTADO`). El backend
ya devuelve `porcentaje_avance_global` correcto en el serializer de detalle;
el frontend ahora lo usa directo en vez de recalcularlo. Verificado con una
acción real: marcar una pendiente como "Aceptado" pasó el plan de 8% a 17%,
tanto en la respuesta de la API como en lo que se ve en pantalla — antes se
habría quedado congelado en el número viejo.

## 4.9. Riesgos contextuales ya pueden generar una acción de tratamiento trazada

Hallazgo del análisis de funcionalidad del 2026-08-24: `AccionTratamiento`
tenía `origen_vulnerabilidad` y `origen_riesgo_activo`, pero ningún vínculo
equivalente para `RiesgoContextual` — los 7 riesgos contextuales (amenaza
interna, legales, físicos) eran la única categoría del sistema sin forma de
generar una acción de tratamiento trazada desde la interfaz. Aunque alguien
creara la acción a mano, no quedaba ningún vínculo de origen, y la Hoja de
Riesgo en PDF nunca la mostraba.

Se agregó `AccionTratamiento.origen_riesgo_contextual` (mismo patrón que los
otros dos: `SET_NULL`, opcional, `related_name="acciones_generadas"`), se
conectó el botón "Generar acción" en la página Riesgos Contextuales, y la
Hoja de Riesgo en PDF ahora también cruza acciones que vengan de un riesgo
contextual relacionado con el activo (`origen_riesgo_contextual__activos_relacionados`).

**Dos bugs reales, no relacionados con este cambio, encontrados al probar el
flujo de punta a punta con navegador real:** el formulario "Generar acción"
no traía valores por defecto para `opcion_tratamiento`, `fase`, `estado` ni
`porcentaje_avance` — aunque el modelo sí los tiene — así que el guardado
fallaba con "no es una elección válida" para los **tres** orígenes por
igual, no solo el nuevo. `GenerarAccionModal` ahora los precarga
(`MITIGAR`/`FASE_1`/`PENDIENTE`/`0`), igual que ya hace con los demás
campos. Verificado generando una acción real desde RC-03: quedó enlazada
correctamente en la base de datos, con la descripción y el responsable
precargados desde el riesgo contextual real.

## 4.10. Panel general en modo consulta sin sesión — el resto requiere iniciar sesión

A pedido explícito: mismo criterio de acceso que ya usa RBAC. Sin sesión,
el menú lateral solo navega a **Panel general** (modo consulta); el resto
(Activos, Vulnerabilidades, Riesgos contextuales, Campañas Red Team, Plan
de tratamiento, Cumplimiento ISO 27001, Catálogos) aparece recién con la
sesión iniciada.

Esto es una restricción real, no solo estética: `RutaProtegida.jsx` envuelve
todas las rutas salvo el Dashboard, así que llegar por URL directa a
`/activos` sin sesión tampoco funciona — muestra un aviso de "Esta sección
requiere sesión" en vez del contenido. Ocultar el enlace del menú sin
bloquear también la ruta habría sido solo cosmético.

Importante: esto es una capa de **navegación/UX**, no la autoridad real de
permisos — esa sigue siendo `EscrituraSegunRolDePlataforma` en el backend,
sin cambios. Antes de este ajuste, cualquiera (con o sin sesión) podía
navegar y *ver* todo; el backend solo bloqueaba *escribir*. Ahora, sin
sesión, tampoco se navega a ver el resto — el backend seguiría permitiendo
esas lecturas si se llamara la API directo, pero la interfaz ya no ofrece
ese camino.

En modo embebido (dentro del Inventario) sin sesión sincronizada todavía,
la pantalla de bloqueo no ofrece su propio botón "Iniciar sesión" — mismo
motivo que ya llevó a quitarlo del pie de la barra lateral (§ ya
corregido): es la misma sesión (JWT único), y un botón aparte ahí daba a
entender que este módulo pide credenciales propias. En su lugar sugiere
recargar o revisar la sesión desde el Inventario.

Verificado con navegador real en los cuatro casos: sin sesión (menú
reducido + acceso directo bloqueado) y con sesión (menú completo + acceso
directo funciona, con datos reales cargando).

## 4.11. Cerrar sesión en el Inventario no cerraba la de riesgos

Hallazgo real, con captura del usuario (2026-08-25): después de cerrar
sesión en el Inventario, el panel embebido de riesgos seguía mostrando el
menú completo con la sesión vieja ("admin"). Causa: el JWT de sesión única,
una vez obtenido, se guarda en `localStorage` con su propio vencimiento —
`AuthContext.jsx` solo validaba que ESE token siguiera siendo válido
(`/api/auth/me/`, que mira la firma y el vencimiento, no si la cookie que lo
originó sigue viva), nunca volvía a preguntarle al Inventario si la sesión
real seguía activa. Cerrar sesión arriba no invalida ese JWT ya emitido —
sigue funcionando hasta que expira solo.

Corrección: un JWT que vino de sesión única silenciosa (no un login manual,
ver más abajo) ahora se re-verifica contra el Inventario — al montar la
aplicación, y además cada 3 minutos mientras el panel embebido queda abierto
sin recargar (el Inventario no destruye el iframe al cambiar de pestaña,
solo lo oculta — ver Layout.jsx). Si el Inventario ya no respalda ese JWT,
se descarta y se pasa a "sin sesión", aunque el token en sí no hubiera
vencido todavía.

**Distinción importante que hay que preservar si se toca este archivo:** un
login manual — cuenta propia de riesgos, o credenciales del Inventario
tecleadas a mano en el modal de login de riesgos — NO se re-verifica contra
la cookie del Inventario. Ese tipo de sesión es intencionalmente
independiente (típicamente sin siquiera haber una cookie del Inventario en
ese navegador, ej. alguien usando riesgos de forma standalone) — solo el
origen "sso" (obtenido en silencio, sin que la persona hiciera nada) queda
sujeto a esta revalidación periódica. Se distingue con una marca aparte en
`localStorage` (`suiin_auth_origen`), no solo por el esquema del token.

Verificado con el stack completo (nginx + Inventario + riesgos, cookies
reales): login real en el Inventario → SSO automático a riesgos (menú
completo, "qa_sso" visible) → logout real en el Inventario → volver a entrar
al panel de riesgos → ya no muestra la sesión vieja, vuelve a "Panel general"
en modo consulta. Reproduce exactamente el escenario de la captura original.

## 4.12. Base de datos reiniciada a un ejemplo por entidad (2026-08-25)

A pedido explícito: se limpió toda la información cargada de gestión de
riesgos, campañas Red Team y PTR, dejando **un solo ejemplo real de cada
tipo** como base para empezar de cero, en vez de partir de una base vacía
sin ninguna referencia de la forma esperada de los datos.

| Entidad | Antes | Después | Se conservó |
|---|---|---|---|
| Vulnerabilidad | 225 | 1 | SSL/TLS Renegotiation DoS, sobre RED-012 |
| RiesgoActivo | 38 | 1 | RA-001, también sobre RED-012 (mismo activo que la vulnerabilidad, a propósito — ejemplo coherente) |
| RiesgoContextual | 7 | 1 | RC-01 (el más completo: 4 activos relacionados) |
| CampanaRedTeam | 4 | 1 | SUIIN-CENSO |
| AccionTratamiento | 12 | 1 | R-01 |
| PlanTratamientoRiesgos | 1 | 1 | SUIIN-SGSI-PTR-001 (sin cambios — ya era el único) |
| CatalogoValor | 86 | 18 | Re-sembrado desde cero (`sembrar_catalogos`) tras la limpieza, para que solo sugiera valores que corresponden a lo que quedó — no los 86 viejos, huérfanos de datos que ya no existen |

**Explícitamente fuera de alcance, sin tocar:** los 38 `Activo` (inventario
técnico de hardware/sistemas — no es "gestión de riesgos" en el sentido que
se pidió limpiar) y las 712 `TecnicaMitre` (catálogo de referencia externo,
sincronizado del Inventario, no datos cargados de este sistema).

**Restricción real que definió qué campaña conservar:**
`PlanTratamientoRiesgos.campana_red_team` usa `on_delete=PROTECT` — Django
rechaza borrar una campaña mientras un PTR la siga referenciando. Como solo
existe un PTR y ya apuntaba a SUIIN-CENSO, esa fue la que se conservó (no
una elección arbitraria).

**No se inventó ningún vínculo de origen falso.** Las 12 acciones
originales del PTR nunca tuvieran `origen_vulnerabilidad`/
`origen_riesgo_activo`/`origen_riesgo_contextual` trazado (vienen del Excel
importado, sin esa granularidad) — la acción que se conservó (R-01) se dejó
tal cual, sin forzar un enlace con la vulnerabilidad o el riesgo por activo
que también se conservaron, porque su contenido real no se corresponde
(R-01 es sobre exfiltración de `docker-compose.yml`, no sobre TLS). Forzar
ese vínculo habría sido más engañoso que dejarlo como está.

Verificado antes de entregar: sin evidencias (`Evidencia`) huérfanas
apuntando a algo borrado (se confirmó que no había ninguna adjunta a estos
tipos antes de borrar); los endpoints clave (`dashboard/resumen`,
`cumplimiento/resumen`, `alertas/resumen`, hoja de riesgo en PDF) responden
`200` sin errores contra el dataset reducido; 258 pruebas de backend + 106
de frontend siguen pasando (usan sus propias bases de datos aisladas, no
`db.sqlite3`, así que no dependían de este cambio de todas formas, pero se
confirmó que nada se rompió estructuralmente).

## 4.13. El bloque de sesión propio seguía duplicando lo del Inventario

Hallazgo real, con captura (2026-08-25), del mismo tipo que el de §4.7 pero
al revés. §4.7 quitó el botón de "Iniciar sesión" duplicado cuando **no**
había sesión en el panel embebido; con sesión activa quedaba el problema
simétrico: el pie de la barra lateral de riesgos seguía mostrando "admin"
con su propio botón de "Cerrar sesión", separado del que ya muestra el
Inventario arriba ("Sesión: admin (roles) · Salir") — daba la impresión de
dos inicios de sesión distintos, aunque técnicamente sea el mismo JWT único.

Corrección: en modo embebido, el bloque completo de sesión (usuario +
"Cerrar sesión", o el botón de "Iniciar sesión" si no hay sesión) ya no se
muestra en ningún caso — solo en acceso directo (`/riesgos/` fuera del
Inventario), donde sí es la única forma de ver o cerrar la sesión. La
navegación completa sigue disponible con sesión, embebido o no; lo único
que cambia es que ya no hay una segunda "cuenta" visible al pie.

**Se agregaron 11 pruebas automatizadas** (`components/Layout.test.jsx`) —
faltaban, a pesar de que este archivo ya se había tocado dos veces por el
mismo tipo de problema. Cubren las cuatro combinaciones (embebido/directo ×
con/sin sesión) y que la navegación siga completa con sesión aunque el
bloque de sesión esté oculto. Verificado que atrapan el bug real: se revirtió
la condición a la versión anterior y fallaron exactamente las 2 pruebas
relevantes, una de ellas la que reproduce el reporte exacto de la captura
("con sesión activa, NO muestra el usuario ni un botón de cerrar sesión
propio"). Se restauró la versión correcta después.

## 5. Referencia de la API

Todos los endpoints devuelven JSON paginado (`count`, `next`, `previous`, `results`),
salvo `/dashboard/resumen/` que devuelve un objeto único. Soportan `?search=`,
filtros por campo (ver `filterset_fields` en `riesgos/views.py`), `?ordering=` y
`?page_size=` (hasta 1000, útil para poblar selects sin paginar).

| Endpoint | Descripción |
|---|---|
| `POST /api/auth/login/` | `{username, password}` → `{token, username, is_staff}` |
| `POST /api/auth/logout/` | Invalida el token actual (requiere token) |
| `GET /api/auth/me/` | Verifica el token y devuelve el usuario actual |
| `GET /api/dashboard/resumen/` | KPIs, heatmap Probabilidad×Impacto, campañas, top activos críticos |
| `GET/POST/PATCH/DELETE /api/activos/` | Inventario de activos (filtros: `riesgo_matriz`, `clasificacion_si`, `cobertura`, `afectado_red_team`, `tipo`) |
| `GET /api/activos/{id}/` | Detalle de un activo con sus puertos y vulnerabilidades (usar este endpoint antes de editar — el listado usa un serializer más liviano) |
| `GET/POST/PATCH/DELETE /api/vulnerabilidades/` | Hallazgos técnicos (filtros: `severidad_ov`, `nivel_riesgo`, `estado`, `activo`) |
| `GET/POST/PATCH/DELETE /api/riesgos-activo/` | Riesgo agregado por activo |
| `GET/POST/PATCH/DELETE /api/riesgos-contextuales/` | Riesgos organizacionales RC-01..RC-07 |
| `GET/POST/PATCH /api/campanas-red-team/` | Campañas Red Team (sin DELETE expuesto en el frontend — están referenciadas por PTR) |
| `GET/POST /api/planes-tratamiento/` | Planes de tratamiento (PTR) |
| `GET/POST/PATCH/DELETE /api/acciones-tratamiento/{id}/` | Acciones de tratamiento (items del PTR) — CRUD completo, con trazabilidad opcional a su origen (`origen_vulnerabilidad`/`origen_riesgo_activo`) |
| `GET/POST/PATCH/DELETE /api/controles-iso27001/` | Catálogo de los 93 controles del Anexo A |
| `GET /api/cumplimiento/resumen/` | Cobertura global y por categoría del Anexo A |
| `GET /api/<recurso>/{id}/historial/` | Historial de auditoría (quién, cuándo, qué campo cambió) — disponible en `activos`, `vulnerabilidades`, `riesgos-activo`, `riesgos-contextuales`, `campanas-red-team`, `planes-tratamiento`, `acciones-tratamiento`, `controles-iso27001` |
| `GET /api/alertas/resumen/` | Acciones de tratamiento y riesgos por activo vencidos o por vencer en 7 días |
| `GET/POST/DELETE /api/evidencias/?modelo=X&object_id=Y` | Adjuntos de evidencia — `modelo` ∈ `activo`, `vulnerabilidad`, `riesgoactivo`, `riesgocontextual`, `acciontratamiento`. `POST` es `multipart/form-data` (`modelo`, `object_id`, `archivo`, `descripcion`) |
| `GET /api/activos/{id}/hoja-riesgo.pdf/` | Hoja de riesgo del activo en PDF — vulnerabilidades, riesgos, acciones de tratamiento vinculadas y evidencia. Lectura pública. |
| `GET/PATCH/DELETE /api/catalogo/?categoria=X` | Valores de catálogo parametrizable — `categoria` ∈ `TIPO_ACTIVO`, `RESPONSABLE_RIESGO`, `RESPONSABLE_ACCION`, `FUENTE_HALLAZGO`, `PLAZO_ACCION`. `?activo=false` lista los desactivados. |
| `POST /api/catalogo/obtener-o-crear/` | `{categoria, valor}` — idempotente (case-insensitive): usa el existente o crea uno nuevo. Lo que llama el combo del formulario. |
| `GET /api/tecnicas-mitre/?search=X&tipo=TE` | Catálogo MITRE ATT&CK (espejo del Inventario) — de solo lectura, búsqueda por código o nombre. `tipo` ∈ `TA`, `TE`, `ST`. |
| `POST /api/vulnerabilidades/bulk-actualizar/` | `{ids: [...], campos: {estado, tratamiento}}` — actualiza varias vulnerabilidades a la vez, guardando cada una por separado para no perder el historial de auditoría. Solo esos dos campos están permitidos. |

Escrituras (`POST`/`PATCH`/`DELETE`) requieren el header `Authorization: Token <token>`.
Lecturas (`GET`) no requieren autenticación.

---

## 6. Limitaciones conocidas

- **Fechas en texto libre:** los campos de fecha del Excel ("1-2 jun 2026", "26 mayo
  – 5 junio 2026") se interpretan con un parser best-effort en español. Si alguna
  fecha no se reconoce, el campo queda vacío en vez de fallar la importación completa.
- **`Host objetivo` del PTR de CENSO:** la portada del Excel original tiene un error
  de copiado (dice `192.168.1.204`, la IP de MINGA-PARA-TEJER, en vez de `.203`). El
  importador prioriza el título/subtítulo de la portada sobre ese campo para asociar
  el PTR a la campaña correcta — quedó vinculado a SUIIN-CENSO correctamente.
- **R-17 y R-24** aparecen en la hoja "Plan de Acción" del PTR de CENSO pero no en
  "Matriz PTR" (sin Probabilidad/Impacto definidos ahí) — parecen referenciar riesgos
  de un registro consolidado más amplio que no forma parte de este documento. Se
  omiten en la importación con una advertencia en consola; puede cargarlos
  manualmente desde `/admin` si tiene sus valores de P×I.
- **Activos SUIIN sin IP fija** (ej. algunos activos perimetrales) usan el campo
  `ip_principal` como texto libre en vez de `GenericIPAddressField`, ya que el Excel
  original mezcla IPs únicas, listas y segmentos CIDR en la misma columna.

## 7. Próximos pasos sugeridos

Priorizados por Jose el 2026-08-04, los 4 bloques originales ya están completos:

1. ~~CRUD completo en frontend~~ — ✅ hecho (Activos, Vulnerabilidades, Riesgos por
   activo, Riesgos contextuales, Campañas Red Team).
2. ~~PTR generado desde la matriz, no desde Excel~~ — ✅ hecho. Botón "Generar
   acción de tratamiento" (ícono de portapapeles) en cada fila de `Vulnerabilidad`
   o `RiesgoActivo` dentro del detalle de un activo — prellena descripción, P×I y
   solución recomendada, y enlaza `origen_vulnerabilidad`/`origen_riesgo_activo`
   en la `AccionTratamiento` resultante para trazabilidad completa. El botón
   "Nuevo PTR" en la página Plan de tratamiento crea el encabezado sin depender
   del importador de Excel (que sigue disponible como carga masiva alterna).
3. ~~Recalculo automático de `riesgo_matriz`~~ — ✅ hecho (señales `post_save`/`post_delete`).
4. ~~Auditoría / historial de cambios~~ — ✅ hecho con `django-simple-history` sobre
   7 de los 8 modelos (todos salvo `PuertoServicio`, de bajo valor de auditoría por
   ser detalle técnico auto-importado). Cada ViewSet expone
   `GET /api/<recurso>/{id}/historial/` con el diff campo a campo contra la versión
   anterior, quién lo hizo y cuándo. Visible en el frontend como panel colapsable
   en el detalle de Activo y en cada tarjeta de acción del PTR; también disponible
   de forma nativa en `/admin` (Django admin incluye una vista de historial propia
   vía `SimpleHistoryAdmin`). **Nota:** el historial solo registra cambios desde que
   se activó esta función — los datos importados antes de esa fecha no tienen
   entrada de "Creación" retroactiva.

Adicionales, menor prioridad — ver el análisis completo del 2026-08-04 en la
conversación con Claude para el detalle de cada uno:

- ~~**Cumplimiento ISO 27001**~~ — ✅ hecho. Catálogo de 93 controles del Anexo A,
  vínculo estructurado desde `AccionTratamiento`/`RiesgoContextual`, endpoint de
  cobertura y página **Cumplimiento** en el frontend (ver §2). Queda pendiente,
  si se necesita más adelante: modelar el catálogo de las 25 políticas
  (POL/MAN-SI-001 a 025) como entidad propia — hoy `politica_referencia` en
  `ControlISO27001` es solo texto libre — y exportación del SoA/PTR a Word/PDF
  con el formato institucional SUIIN-SGSI.
- **Alertas y vencimientos**: ✅ hecho (ver §2). `fecha_limite` real en
  `AccionTratamiento` y `RiesgoContextual`, endpoint `/api/alertas/resumen/`,
  aviso en el dashboard, y `enviar_alertas_vencimiento` para correo periódico vía
  cron. Los tres modelos con seguimiento de plazo (`AccionTratamiento`,
  `RiesgoActivo`, `RiesgoContextual`) ya entran en las alertas. Pendiente si se
  necesita más adelante: un canal de notificación adicional (Slack/Tag) además
  de correo.
- ~~**Protección del importador contra reimportaciones destructivas**~~ — ✅
  hecho (ver §4). Hallazgo del análisis de gestionabilidad del 2026-08-06: antes,
  reimportar el Excel podía sobrescribir en silencio ediciones hechas desde la
  app, y en el caso de `Vulnerabilidad` directamente las borraba y recreaba por
  completo. Ahora cada registro protege automáticamente su estado si fue editado
  manualmente después de la última importación.
- ~~**Integración con el ecosistema SUIIN**~~ — ✅ hecho parcialmente: el
  catálogo de activos se sincroniza desde el Inventario de la Plataforma SUIIN
  unificada (ver §4.1 y `../README-DESPLIEGUE.md` sección 11) en vez de duplicarse.
  Sigue pendiente: consumo directo de la API de OpenVAS/GVM en vez de exportar
  Excel a mano, y webhook desde el SIEM Elastic para crear borradores de
  `Vulnerabilidad`/`RiesgoActivo` desde alertas críticas.
- ~~Permisos por rol~~ — ✅ hecho vía sesión única con la Plataforma SUIIN: el
  JWT que emite el Inventario trae el rol (Consultor/Dinamizador/Administrador,
  de `SUIIN-SGSI-MCA-001`), y `riesgos/auth_jwt.py` lo aplica — Consultor solo
  lee, Dinamizador/Administrador escriben, Administrador obtiene acceso al admin
  de Django. Ver `../README-DESPLIEGUE.md` sección 11.4bis. El login por token
  propio de este módulo (para cuando corre de forma independiente, sin el resto
  de la plataforma) sigue siendo binario: cualquier cuenta autenticada puede
  escribir todo.
- ~~Suite de pruebas automatizadas (`pytest-django`)~~ — ✅ hecho, 258 pruebas (ver §3).
- ~~**Adjuntos de evidencia**~~ — ✅ hecho (ver §2). Modelo genérico `Evidencia`
  sobre Activo/Vulnerabilidad/RiesgoActivo/RiesgoContextual/AccionTratamiento, con
  validación de extensión, tamaño máximo y whitelist de modelos en el servidor.
- **Respaldo y checklist de salida a producción** — pendiente. Del análisis de
  gestionabilidad del 2026-08-06 y del análisis de integración de los tres
  proyectos: `respaldar_plataforma.py` (raíz de la plataforma unificada) todavía
  no incluye la base de datos ni los adjuntos de evidencia de este módulo — solo
  respalda Inventario y RBAC. Falta además rotar `SECRET_KEY`/`RIESGOS_SECRET_KEY`
  antes de cualquier despliegue fuera de un entorno de desarrollo, y evaluar la
  migración a PostgreSQL si más de una persona edita a la vez.
- ~~Exportación de una "hoja de riesgo" en PDF por activo~~ — ✅ hecho.
  `GET /api/activos/{id}/hoja-riesgo.pdf/` (botón "Hoja de riesgo (PDF)" en el
  detalle de cada activo) — vulnerabilidades, riesgos evaluados, acciones de
  tratamiento vinculadas (por origen fino o, si el PTR vino de Excel sin ese
  detalle, por campaña de Red Team compartida) y evidencia adjunta (del activo
  y de sus vulnerabilidades/riesgos), con el mismo lenguaje visual que la
  `hojavida.pdf` del Inventario. Es de lectura pública, igual que el resto del
  sistema.
- Modelar el catálogo de las 25 políticas (POL/MAN-SI-001 a 025) como entidad
  propia — hoy `politica_referencia` en `ControlISO27001` es solo texto libre.
- Series de tiempo en el dashboard (evolución del riesgo total mes a mes).
- ~~Vista global de vulnerabilidades~~ — ✅ hecho, ver §4.4.
- ~~`Vulnerabilidad.solucion_recomendada` sin agregar al catálogo~~ — ✅ hecho,
  ver §4.6.
- ~~Operaciones en lote~~ — ✅ hecho para vulnerabilidades, ver §4.5. Sigue
  pendiente para acciones de tratamiento (Plan de tratamiento no tiene el
  equivalente todavía).
- ~~Campañas Red Team con conteo de riesgo desactualizado~~ — ✅ hecho. Hallazgo
  del análisis del 2026-08-20: `riesgos_criticos/altos/medios/bajos` son una
  foto congelada de la importación (nunca se recalculan solas, a diferencia de
  `Activo.riesgo_matriz`) y se mostraban en el frontend sin ninguna indicación
  de eso — la discrepancia real que se encontró en CENSO fue 7 críticos
  importados contra 68 reales al momento de revisar. Se agregó
  `CampanaRedTeam.riesgos_actuales_por_nivel` (propiedad calculada en vivo a
  partir de los activos vinculados) sin tocar el campo histórico, y el
  frontend ahora muestra ambos números, claramente diferenciados.
- ~~`PlanTratamientoRiesgos.porcentaje_avance_global` no contaba `ACEPTADO`~~ —
  ✅ hecho. Inconsistente con `ESTADOS_CERRADOS` (el mismo criterio que usan las
  alertas de vencimiento) — un riesgo formalmente aceptado es una disposición
  válida, no un pendiente, y ahora sí suma al avance del plan.
- ~~Integrar este módulo al `docker-compose` de SUIIN Platform~~ — ✅ hecho, ver
  `../README-DESPLIEGUE.md` sección 11.

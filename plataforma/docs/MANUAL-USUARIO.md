# Manual de usuario — Plataforma SUIIN-SGSI

**Versión:** 1.0 · **Fecha:** septiembre 2026  
**Ámbito:** Inventario de activos, Matriz RBAC (MCA-001) y Gestión de Riesgos y PTR  
**Organización:** SUIIN — Consejo Regional Indígena del Cauca (CRIC)

Este manual describe cómo usar la interfaz web unificada del SGSI. Para instalación, configuración y mantenimiento, consulte [MANUAL-TECNICO.md](MANUAL-TECNICO.md).

---

## Tabla de contenidos

1. [Introducción](#1-introducción)
2. [Acceso al sistema](#2-acceso-al-sistema)
3. [Roles y permisos](#3-roles-y-permisos)
4. [Navegación general](#4-navegación-general)
5. [Inventario de activos](#5-inventario-de-activos)
6. [Matriz RBAC](#6-matriz-rbac)
7. [Gestión de Riesgos y PTR](#7-gestión-de-riesgos-y-ptr)
8. [Alertas y panel ejecutivo](#8-alertas-y-panel-ejecutivo)
9. [Preguntas frecuentes](#9-preguntas-frecuentes)

---

## 1. Introducción

La plataforma SUIIN-SGSI reúne en una sola aplicación web tres herramientas del Sistema de Gestión de Seguridad de la Información:

| Módulo | Documento base | Función principal |
|--------|----------------|-------------------|
| **Inventario de activos** | SUIIN-SGSI-INV-001 | Catálogo de activos, valoración inherente, infraestructura |
| **Matriz RBAC** | SUIIN-SGSI-MCA-001 | Control de acceso basado en roles |
| **Gestión de Riesgos y PTR** | SUIIN-SGSI-RIESGOS | Vulnerabilidades, riesgos, plan de tratamiento, Red Team |

Al abrir la aplicación verá un encabezado común con tres pestañas de módulo. Cada módulo tiene su propia barra de navegación interna, pero comparte el mismo inicio de sesión y la misma identidad visual.

---

## 2. Acceso al sistema

### 2.1 Iniciar sesión

1. Abra la URL de la plataforma (por ejemplo `http://localhost/` en entorno local).
2. Si no tiene sesión activa, será redirigido a **Iniciar sesión** (`/login`).
3. Ingrese su **usuario** y **contraseña** institucionales.
4. Tras un inicio correcto, la aplicación lo llevará al **Dashboard del Inventario**.

### 2.2 Cerrar sesión

Use el enlace **Cerrar sesión** en el encabezado. Esto invalida la sesión en el servidor y lo devuelve a la pantalla de login.

### 2.3 Usuarios de demostración (solo entornos de prueba)

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `SUIIN2026#` | Administrador |
| `dinamizador` | `Dinamizador2026#` | Dinamizador |
| `consultor` | `Consultor2026#` | Consultor |

> **Importante:** cambie estas contraseñas antes de exponer la plataforma en red.

### 2.4 Bloqueo por intentos fallidos

Tras varios intentos de login incorrectos, el sistema puede bloquear temporalmente la cuenta o la dirección IP. Si esto ocurre, espere el tiempo indicado o contacte al administrador del SGSI.

---

## 3. Roles y permisos

Los permisos se asignan mediante **grupos de Django** vinculados a su usuario. Además, cada cuenta puede tener **proyectos específicos** (Inventario, Matriz RBAC, Gestión de Riesgos); solo verá las pestañas de los proyectos asignados. Véase [§5.10 Cuentas de acceso](#510-cuentas-de-acceso-administrador).

| Acción | Consultor | Dinamizador | Administrador |
|--------|:---------:|:-----------:|:-------------:|
| Ver datos del Inventario | ✓ | ✓ | ✓ |
| Crear o editar activos | — | ✓ | ✓ |
| Eliminar activos | — | — | ✓ |
| Acceder al módulo RBAC | ✓ (solo lectura) | ✓ | ✓ |
| Editar matriz, roles, usuarios RBAC | — | ✓ | ✓ |
| Ver Gestión de Riesgos | ✓ | ✓ | ✓ |
| Crear o editar riesgos, PTR, vulns | — | ✓ | ✓ |
| Auditoría unificada cross-módulo | — | — | ✓ |

### Modo consulta

Si tiene rol **Consultor**, verá un aviso de **modo consulta** en formularios del Inventario y RBAC: los campos aparecen deshabilitados y no hay botones de guardar. En RBAC, las rutas de creación (`/nuevo`) muestran un mensaje de bloqueo en lugar del formulario.

---

## 4. Navegación general

### 4.1 Encabezado principal

El encabezado muestra:

- **Logo e identidad** SUIIN/CRIC
- **Pestañas de módulo:** Inventario · Matriz RBAC · Gestión de Riesgos (solo las asignadas a su cuenta)
- **Badge de alertas** (número rojo) cuando hay pendientes críticos
- **Usuario actual** y enlace de cierre de sesión

### 4.2 Badges y alertas

Los números en las pestañas indican elementos pendientes de atención:

- **Inventario:** alertas de calidad de datos, sync con Riesgos, etc.
- **Matriz RBAC:** MFA incumplido, certificaciones vencidas, excepciones vencidas
- **Gestión de Riesgos:** vencimientos de PTR, riesgos por revisar

Haga clic en la pestaña o en **Centro de alertas** (Inventario) para ver el detalle.

### 4.3 Enlaces entre módulos

Desde la ficha de un activo del Inventario puede saltar a:

- Su **espejo en Riesgos** (si existe sincronización)
- El **sistema RBAC** vinculado (si tiene `sistema_rbac_id` configurado)

Desde **Centro de alertas**, los enlaces profundos lo llevan directamente a la sección relevante de RBAC (vencimientos, MFA, excepciones, certificaciones).

---

## 5. Inventario de activos

Ruta base: `/inventario/`

### 5.1 Dashboard

**Ruta:** `/inventario/dashboard`

Vista principal del inventario. Muestra:

- **KPIs:** total de activos, distribución por clase, riesgo inherente, completitud de datos
- **Tabla de activos** con búsqueda, filtros por clase, nivel de riesgo y estado de sincronización
- **Acciones masivas:** exportar a Excel, generar etiquetas PDF
- **Panel de vinculación** con el módulo de Riesgos (activos con y sin espejo)

**Filtro útil:** *Sin espejo en Riesgos* — lista activos que aún no tienen registro correspondiente en Gestión de Riesgos.

**Acciones habituales:**

| Botón | Requiere rol | Descripción |
|-------|--------------|-------------|
| Nuevo activo | Dinamizador+ | Alta manual de un activo |
| Importar | Dinamizador+ | Carga masiva desde Excel |
| Exportar Excel | Autenticado | Descarga el inventario completo |
| Etiquetas | Dinamizador+ | PDF con códigos QR por activo |

### 5.2 Ficha de activo

**Ruta:** `/inventario/activos/{id}`

Muestra todos los campos del activo organizados por secciones:

- Identificación (código, nombre, clase)
- Gobernanza (propietario, custodio, área)
- Confidencialidad, integridad y disponibilidad (C-I-D)
- Infraestructura, ciclo de vida, continuidad (RTO/RPO)
- Vulnerabilidades y controles asociados
- Cruce con RBAC y Riesgos

**Acciones:**

- **Editar** — modifica el activo (Dinamizador+)
- **Eliminar** — solo Administrador; pide confirmación
- **Historial** — cambios registrados en bitácora
- **Hoja de vida PDF** — documento exportable del activo

### 5.3 Alta y edición de activos

**Rutas:** `/inventario/activos/nuevo` · `/inventario/activos/{id}/editar`

El formulario se adapta a la **clase de activo** seleccionada:

| Clase | Prefijo de código | Ejemplo |
|-------|-------------------|---------|
| Infraestructura | `RED-` | `RED-SW-CORE-01` |
| Sistemas de información | `SIS-` | `SIS-ERP-01` |
| Equipos de cómputo | `PC-` | `PC-CONT-042` |

Campos obligatorios mínimos: código, nombre y clase. El sistema valida coherencia antes de guardar.

En sistemas de información, puede vincular un **sistema RBAC** del catálogo MCA-001 para cruce automático de permisos.

### 5.4 Importación masiva

**Ruta:** `/inventario/activos/importar`

Flujo en dos pasos:

1. **Descargar plantilla** Excel con columnas esperadas
2. **Subir archivo** → el sistema **analiza** y muestra un resumen (filas nuevas, actualizaciones, errores)
3. **Confirmar** solo si el resumen es correcto

No se aplican cambios hasta confirmar explícitamente.

### 5.5 Panel ejecutivo

**Ruta:** `/inventario/panel-ejecutivo`

Tablero de madurez del SGSI con indicadores consolidados:

- Completitud del inventario (C-I-D, propietarios, controles)
- KPIs de RBAC (MFA, certificaciones, excepciones)
- KPIs de Riesgos (vulnerabilidades abiertas, PTR)
- Estado de sincronización Inventario ↔ Riesgos
- Cambios registrados en los últimos 30 días

Puede descargar un **reporte consolidado PDF** (requiere sesión autenticada).

### 5.6 Valoración inherente

**Ruta:** `/inventario/riesgos`

> **No confundir** con el módulo *Gestión de Riesgos y PTR*. Esta pantalla calcula el **riesgo inherente** del activo según amenazas MITRE, controles ISO 27002 y la matriz C-I-D del propio Inventario.

Permite:

- Ver el nivel de riesgo calculado por activo
- Recalcular niveles tras cambios en amenazas o controles
- Filtrar por nivel (Crítico, Alto, Medio, Bajo)

### 5.7 Centro de datos

**Ruta:** `/inventario/centro-datos`

Gestión de infraestructura física:

- **Datacenters** — sitios, dirección, responsable
- **Racks** — ubicación dentro del datacenter
- **Diagramas** — planos y esquemas de red (subida de archivos)

Desde aquí puede crear y editar datacenters y diagramas (Dinamizador+).

### 5.8 Clases de activo

**Ruta:** `/inventario/clases`

Catálogo de las tres clases principales (Infraestructura, Sistemas, Equipos) con sus campos y reglas de codificación.

### 5.10 Cuentas de acceso (Administrador)

**Ruta:** `/inventario/usuarios`

> **No confundir** con **Usuarios** del módulo RBAC (`/rbac/usuarios`). Las cuentas de acceso son los usuarios que **inician sesión** en la plataforma; el registro RBAC documenta personas del control MCA-001.

Solo visible para rol **Administrador**. Permite:

- Crear cuentas con usuario, contraseña, nombre, correo, **área organizacional**, **proyectos permitidos** y rol SGSI (Consultor, Dinamizador o Administrador)
- Editar datos, cambiar rol, restablecer contraseña o desactivar cuentas
- Filtrar por área, rol o búsqueda de texto

**Roles disponibles:**

| Rol | Acceso en la plataforma |
|-----|-------------------------|
| Consultor | Solo lectura (Inventario y RBAC) |
| Dinamizador | Lectura y escritura |
| Administrador | Control total, incluye gestión de cuentas |

**Proyectos (módulos) asignables:**

| Proyecto | Contenido |
|----------|-----------|
| Inventario de activos | Dashboard, activos, alertas, panel ejecutivo |
| Matriz RBAC | Control de acceso MCA-001 |
| Gestión de Riesgos y PTR | Vulnerabilidades, PTR, Red Team |

Marque solo los proyectos que el usuario necesite. Los Administradores tienen acceso a los tres automáticamente. Tras guardar, el usuario solo verá las pestañas de los proyectos asignados. Si una cuenta queda sin ningún proyecto, al ingresar verá un aviso para contactar al administrador.

Cada cuenta nueva recibe un **espacio de datos propio** en el Inventario (vacío hasta que registre activos). Las cuentas de demostración (`admin`, `dinamizador`, `consultor`) comparten el inventario de ejemplo de la organización.

Al **cerrar sesión** o **cambiar de usuario** en el mismo navegador, la plataforma descarta credenciales locales para que no se mezclen datos entre cuentas.

### 5.11 Bitácora

**Ruta:** `/inventario/bitacora`

Historial global de cambios en el Inventario: quién modificó qué, cuándo y el detalle campo por campo. Útil para auditorías ISO 27001 (control 8.15).

Puede filtrar por entidad, usuario o rango de fechas.

---

## 6. Matriz RBAC

Ruta base: `/rbac/`

Documento fuente: **SUIIN-SGSI-MCA-001 v2.0** (ISO 27002 controles 5.15–5.18).

### 6.1 Acceso al módulo

Para entrar al módulo RBAC debe tener sesión activa con rol **Consultor**, **Dinamizador** o **Administrador**. Si no tiene sesión, verá un mensaje con enlace al login.

### 6.2 Inicio (tablero de control)

**Ruta:** `/rbac/inicio`

Resumen ejecutivo del control de acceso:

- Cumplimiento **MFA** por rol
- **Vencimientos próximos** (usuarios temporales, excepciones)
- **Certificaciones de roles** vencidas o por vencer
- Gráficos de distribución por nivel de riesgo MITRE ATT&CK
- Accesos directos a secciones con pendientes

### 6.3 Roles

**Ruta:** `/rbac/roles`

Listado de roles del SGSI con:

- Código, nombre, grupo, categoría
- Nivel de riesgo ATT&CK
- Estado de **certificación periódica** (control 5.18)
- Requisito de MFA

**Acciones (Dinamizador+):**

- **Nuevo rol** — formulario guiado; opción de **clonar** un rol existente copiando su fila de la matriz
- **Editar** — modificar metadatos del rol
- **Certificar** — registrar fecha y nota de revisión periódica
- **Desactivar** — el rol deja de aplicarse sin perder trazabilidad

### 6.4 Usuarios

**Ruta:** `/rbac/usuarios`

Catálogo de usuarios con acceso al SGSI:

- Identidad (nombre, correo, documento)
- Rol asignado y estado (Activo, Suspendido, Temporal)
- Cumplimiento MFA
- Vigencia (obligatoria para accesos temporales)

**Alta de usuario (Dinamizador+):**

1. Sección **Identidad** — datos personales
2. Sección **Cumplimiento** — rol, MFA; el formulario muestra el requisito MFA del rol elegido
3. Sección **Vigencia** — fechas solo si el acceso es Temporal

Desde la ficha de un usuario puede **asignar excepciones individuales** (ver §6.7).

### 6.5 Matriz de acceso

**Ruta:** `/rbac/matriz`

La matriz principal (sistemas × roles) con niveles de acceso:

| Nivel | Significado |
|-------|-------------|
| Ninguno | Sin acceso al sistema |
| Lectura | Solo consulta |
| Operación | Uso operativo limitado |
| Administración | Control total del sistema |

**Edición (Dinamizador+):**

- Haga clic en una celda para cambiar el nivel; el cambio se guarda al instante
- Aparece aviso flotante con botón **Deshacer** para revertir
- Use el buscador de sistema (Enter para ir a la fila)
- Filtro **Solo columnas con acceso** para ocultar columnas vacías
- Mapa de calor para visualizar densidad de permisos

**Herramientas adicionales:**

| Ruta | Función |
|------|---------|
| `/rbac/matriz/comparar` | Comparar dos roles lado a lado (mínimo privilegio) |
| `/rbac/matriz/importar` | Importar matriz desde CSV (analizar → confirmar) |
| Exportar CSV | Descarga la matriz completa |

### 6.6 Sistemas de información

**Ruta:** `/rbac/sistemas`

Catálogo de los ~29 sistemas de la matriz MCA-001:

- Código, nombre, categoría, clasificación
- Nivel de riesgo ATT&CK
- Técnicas MITRE asociadas (selector con chips, no texto libre)

Desde aquí puede crear, editar o desactivar sistemas (Dinamizador+). Un sistema con excepciones documentadas no se puede eliminar, solo desactivar.

### 6.7 Excepciones de acceso

**Ruta:** `/rbac/excepciones`

Gestión del control **5.18** — accesos que difieren del rol base:

- Listado de excepciones vigentes y vencidas
- **Motivo obligatorio** y fecha de vencimiento
- Retiro manual de excepciones

**Excepción individual:** desde la ficha de usuario o desde esta pantalla.

**Excepción masiva:** `/rbac/excepciones/masiva` — aplica la misma excepción a varios usuarios; cada una queda registrada en bitácora.

> Las excepciones vencidas se retiran automáticamente; los usuarios temporales vencidos pasan a Suspendido.

### 6.8 Auditoría

**Ruta:** `/rbac/auditoria`

Bitácora encadenada con hash SHA-256:

- Filtro por entidad, acción o texto
- Paginación
- Botón **Verificar integridad** — detecta alteraciones fuera de la aplicación

Desde fichas de rol, usuario o sistema hay enlaces directos al historial filtrado.

---

## 7. Gestión de Riesgos y PTR

Ruta base: `/gestion-riesgos/`

### 7.1 Acceso

- El **Dashboard** de Riesgos es visible sin sesión (modo consulta pública de KPIs).
- El resto de pantallas requiere inicio de sesión en la plataforma.
- La escritura (crear, editar, eliminar) requiere rol **Dinamizador** o **Administrador**.

### 7.2 Dashboard

**Ruta:** `/gestion-riesgos/`

Panel general con:

- Total de activos espejo sincronizados
- Vulnerabilidades abiertas por severidad
- Riesgos por nivel
- Estado del plan de tratamiento (PTR)
- Campañas Red Team activas

### 7.3 Activos

**Ruta:** `/gestion-riesgos/activos`

Lista de activos **espejo** sincronizados desde el Inventario. No se crean activos aquí de forma independiente: la fuente canónica es el Inventario.

Cada activo muestra:

- Código y nombre (desde Inventario)
- Puertos detectados (Nmap)
- Vulnerabilidades (OpenVAS)
- Riesgo agregado calculado

**Detalle:** `/gestion-riesgos/activos/{id}` — ficha completa con historial de cambios.

> Si un activo del Inventario no aparece aquí, ejecute la sincronización (contacte al administrador) o revise el panel de vinculación en el Dashboard del Inventario.

### 7.4 Vulnerabilidades

**Ruta:** `/gestion-riesgos/vulnerabilidades`

Vista global de hallazgos OpenVAS y Nmap:

- Filtros por severidad, activo, estado (abierto/cerrado)
- Actualización masiva de estado
- Enlace al activo afectado

### 7.5 Riesgos

| Ruta | Contenido |
|------|-----------|
| `/gestion-riesgos/riesgos-activo` | Riesgo agregado por activo (cruce vulns + C-I-D) |
| `/gestion-riesgos/riesgos-contextuales` | Riesgos organizacionales RC-01 a RC-07 |

### 7.6 Red Team

**Ruta:** `/gestion-riesgos/red-team`

Registro de campañas de prueba de penetración: alcance, hallazgos, estado y vinculación con activos.

### 7.7 Plan de Tratamiento (PTR)

**Ruta:** `/gestion-riesgos/plan-tratamiento`

Plan de Tratamiento de Riesgos según el engagement Red Team:

- Acciones de mitigación con responsable y fecha límite
- Estado (pendiente, en curso, completada, vencida)
- Evidencias adjuntas

El sistema alerta cuando una acción se acerca a su vencimiento.

### 7.8 Importación

**Ruta:** `/gestion-riesgos/importar`

Carga de matrices originales en Excel (análisis de riesgos, PTR). Útil para migraciones o actualizaciones masivas.

### 7.9 Cumplimiento ISO 27001

**Ruta:** `/gestion-riesgos/cumplimiento`

Cobertura del Anexo A ISO 27001:2022 según controles implementados y evidencias registradas.

### 7.10 Catálogos

**Ruta:** `/gestion-riesgos/catalogos`

Parámetros configurables: severidades, estados, tipos de riesgo, etc.

---

## 8. Alertas y panel ejecutivo

### 8.1 Centro de alertas unificado

**Ruta:** `/inventario/alertas`

Agrupa señales de los tres módulos en grupos por severidad:

| Origen | Ejemplos de alerta |
|--------|-------------------|
| Inventario | Propietario faltante, C-I-D incompleto, fin de soporte (EOL) próximo |
| RBAC | MFA incumplido, certificación vencida, excepción vencida |
| Riesgos | Acción PTR vencida, vulnerabilidad crítica abierta |
| Integración | Activos sin espejo en Riesgos, sync desactualizado |

Cada alerta incluye un **enlace directo** a la pantalla donde puede resolverla.

### 8.2 Badges en la shell

Los números en las pestañas del encabezado se actualizan al cargar la aplicación. Un badge rojo indica pendientes que requieren atención prioritaria.

### 8.3 Panel de vinculación (sync)

Visible en Dashboard, Panel ejecutivo y Alertas cuando hay activos pendientes de sincronizar con Riesgos:

- Total consolidado de activos
- Cuántos tienen espejo en Riesgos
- Cuántos faltan (`sin_espejo_riesgos`)
- Enlace para filtrar el listado de activos sin espejo
- Descarga CSV del estado de vinculación

### 8.4 Reporte PDF consolidado

Desde el Panel ejecutivo, el botón **Descargar reporte** genera un PDF con KPIs de los tres módulos. Requiere sesión autenticada.

---

## 9. Preguntas frecuentes

### No puedo iniciar sesión

- Verifique usuario y contraseña (mayúsculas y símbolos cuentan).
- Si la cuenta está bloqueada por intentos fallidos, espere o contacte al administrador.
- Asegúrese de acceder por la URL correcta (no por un puerto de backend directo).

### Veo "modo consulta" y no puedo guardar

Tiene rol **Consultor**. Solo puede ver datos. Para editar, solicite rol **Dinamizador** o **Administrador** al responsable del SGSI.

### Un activo no aparece en Gestión de Riesgos

El catálogo de Riesgos se alimenta por **sincronización** desde el Inventario. Revise el panel de vinculación en el Dashboard. Si persiste, el administrador debe ejecutar `sincronizar_activos_inventario`.

### Cambié una celda de la matriz RBAC y quiero deshacer

Use el botón **Deshacer** del aviso flotante que aparece inmediatamente tras el cambio. Si ya cerró el aviso, edite la celda de nuevo al valor anterior.

### ¿Cuál es la diferencia entre "Valoración inherente" y "Gestión de Riesgos"?

- **Valoración inherente** (`/inventario/riesgos`): motor del Inventario; calcula riesgo según amenazas y controles del propio activo.
- **Gestión de Riesgos** (`/gestion-riesgos/`): módulo PTR con vulnerabilidades OpenVAS/Nmap, Red Team y plan de tratamiento.

### ¿Dónde reporto un error técnico?

Contacte al administrador del SGSI o al equipo de soporte de la plataforma. Para detalles de logs y configuración, consulte [MANUAL-TECNICO.md](MANUAL-TECNICO.md).

---

## Documentos relacionados

- [README.md](../README.md) — visión general e inicio rápido
- [MANUAL-TECNICO.md](MANUAL-TECNICO.md) — instalación, APIs, operaciones
- [README-DESPLIEGUE.md](../README-DESPLIEGUE.md) — despliegue integrado y seguridad

— Camino del SUIIN · CRIC

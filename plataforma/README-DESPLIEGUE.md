# Plataforma SUIIN-SGSI — Despliegue integrado

Una sola interfaz web (SPA React en `/`) que unifica tres módulos del SGSI.
Cada aplicación conserva su stack y base de datos; nginx enruta las peticiones
y delega la autorización de RBAC en la sesión del Inventario.

| Aplicación | Stack | URL principal |
|---|---|---|
| Inventario de Activos SGSI (SUIIN-SGSI-INV-001) | Django (API) | `/inventario/…` en React; `/api/` JSON |
| Matriz RBAC / MCA-001 (SUIIN-SGSI-MCA-001) | Flask (API JSON) | `/rbac/…` en React; `/rbac/api/` JSON |
| Gestión de Riesgos y PTR (SUIIN-SGSI-RIESGOS) | Django + React | `/gestion-riesgos` (iframe `/riesgos/?embed=1`) |

> **Nota histórica:** las secciones 1–3 más abajo describen la integración
> original con iframe HTML de RBAC. La arquitectura actual está resumida en
> la sección 9 (migración a React). RBAC ya no sirve plantillas Jinja2.

## 1. Cómo se logra "una sola interfaz" sin fusionar el código

Las dos aplicaciones son stacks distintos (Django vs. Flask, con su propio
ORM, sesiones y esquema de base de datos). Reescribir una dentro de la otra
para fusionarlas en un solo framework habría significado rehacer buena parte
de dos herramientas ya en producción y validadas con sus propias suites de
pruebas — riesgo innecesario para herramientas del SGSI, y no era lo que se
pidió: el pedido fue "una sola interfaz", no "un solo código".

Por eso el enfoque es:

1. **Un gateway nginx único** enruta `/`, `/admin/`, `/api/`, `/login/`,
   `/static/`, `/media/` al Inventario (Django), y `/rbac/` a la Matriz RBAC
   (Flask). Un solo dominio, un solo puerto.
2. **La pestaña "Matriz RBAC" del tablero del Inventario incrusta ese módulo
   en un `<iframe>`** apuntando a `/rbac/?embed=1`. Para quien la usa, es una
   pestaña más del mismo tablero — igual que "Panel ejecutivo" o "Riesgos" —
   no una redirección a otra página con otro diseño.
3. **El parámetro `?embed=1` le dice a RBAC que se está mostrando incrustada**:
   oculta su propio encabezado de marca y su pie de página (para no duplicar
   chrome dentro del módulo) y conserva solo su barra de navegación interna
   compacta (Inicio/Matriz/Roles/Sistemas/Usuarios/Excepciones/Auditoría),
   que es la navegación propia de ese módulo — el mismo patrón que ya usan
   las demás pestañas del tablero, cada una con su propio contenido interno
   bajo el único encabezado del Inventario.
4. Ese `?embed=1` se propaga automáticamente a toda la navegación interna de
   RBAC (enlaces, redirects tras guardar un formulario, etc.) mediante los
   hooks nativos de Flask `url_value_preprocessor`/`url_defaults` — no hubo
   que tocar cada una de sus 15 plantillas.

Cada aplicación conserva su código, su base de datos y su lógica interna
intactos. Los cambios de código fueron mínimos y quirúrgicos (sección 3).

## 2. Decisión de seguridad: RBAC ya no queda expuesta sin control

El propio `README.md` de SUIIN-RBAC advertía:

> "La aplicación no exige autenticación [...] IMPORTANTE: no la exponga a la
> red; manténgala en 127.0.0.1 [...] porque cualquiera con alcance al puerto
> puede modificar la matriz."

Al integrarla en un despliegue con acceso de red junto al Inventario, ese
supuesto ya no aplica si no se hace algo al respecto. La solución elegida
**no modifica la lógica de RBAC** (que sigue "sin login" tal como fue
diseñada), sino que nginx exige, antes de dejar pasar cualquier petición a
`/rbac/`, que exista una sesión de Django con rol **Dinamizador** o
**Administrador** (los roles con permiso de escritura en el Inventario).
Esto se implementa con `auth_request` contra un endpoint interno
(`/api/auth-rbac/`, no accesible desde fuera) que devuelve `204` (autorizado)
o `401` (no autorizado, y nginx redirige a `/login/?next=/rbac/`).

Como el módulo ahora vive dentro de una pestaña del tablero, el propio
JavaScript del Inventario ya sabe si el usuario tiene ese rol (reutiliza el
mismo dato que usa para mostrar u ocultar los botones de "Nuevo activo") y,
si no lo tiene, muestra directamente dentro de la pestaña un mensaje —
"la Matriz RBAC requiere rol Dinamizador o Administrador" — con un enlace a
iniciar sesión, en vez de intentar cargar el iframe y toparse con la
redirección de nginx dentro de un recuadro pequeño.

**Para ajustar quién puede entrar a RBAC:** edite en
`inventario/inventario/views.py` la función `auth_check_rbac` (por ejemplo,
para permitir también al rol Consultor, cambie la condición a
`roles & {ROL_CONSULTOR, ROL_DINAMIZADOR, ROL_ADMIN}`) — y, para que el
mensaje in-situ del tablero coincida, ajuste también la condición de
`puede_editar` en `sesion_info_v2` si decide separar ambos criterios.

## 3. Cambios de código realizados (resumen)

**RBAC (Flask):**
- **`app.py`**: `ProxyFix` para funcionar bajo el prefijo `/rbac/` detrás de
  nginx; hooks `url_value_preprocessor`/`url_defaults` que propagan
  automáticamente `?embed=1` a todo `url_for()` de la app (enlaces,
  formularios, redirects) cuando se carga incrustada.
- **`auth.py`**: `X-Frame-Options` cambiado de `DENY` a `SAMEORIGIN` y se
  agregó `frame-ancestors 'self'` a la CSP — necesario para que el navegador
  permita incrustar RBAC en el `<iframe>` del Inventario (un origen externo
  sigue sin poder enmarcarla).
- **`templates/base.html`**: cuando `?embed=1` está presente, oculta el
  encabezado de marca y el pie de página propios (evita chrome duplicado
  dentro del módulo) y conserva solo la navegación interna, en versión
  compacta.
- **`static/style.css`**: estilos de la navegación desacoplados de su
  anidamiento en el header (ya no está anidada) y variante compacta
  `.nav-incrustada`.
- **`tests/test_sistema.py`**: actualizado el test de encabezados
  (`SAMEORIGIN` en vez de `DENY`) y agregada una prueba de propagación de
  `embed=1`. Las 41 pruebas pasan.

**Inventario (Django):**
- **`inventario/views.py`** y **`urls.py`**: nueva vista/ruta
  `auth_check_rbac` / `/api/auth-rbac/` (puerta de autorización, sección 2).
- **`templates/inventario/dashboard.html`**: la pestaña "Matriz RBAC" carga
  (una sola vez, de forma perezosa) un `<iframe src="/rbac/?embed=1">` dentro
  de la misma pestaña del tablero si el usuario tiene rol Dinamizador o
  Administrador; si no, muestra un mensaje in-situ con enlace a iniciar
  sesión, en vez de un `<iframe>` que se toparía con la redirección de nginx.
- **`config/settings.py`**: se agregó `STATIC_ROOT` para que `collectstatic`
  tenga destino y nginx pueda servir los estáticos directamente.

Nada de la lógica de negocio, modelos, permisos o bases de datos de ninguna
de las dos aplicaciones fue tocado.

## 4. Requisitos

- Docker y el plugin `docker compose` (`docker compose version`).
- Puerto 80 libre en el host (o cambiar el mapeo en `docker-compose.yml`).

## 5. Puesta en marcha

```bash
cd suiin-plataforma
cp .env.example .env
nano .env                      # defina DJANGO_SECRET_KEY, SUIIN_RBAC_SECRET,
                                # DJANGO_ALLOWED_HOSTS, etc.
docker compose up -d --build
```

Al terminar:

| Recurso | URL |
|---|---|
| Tablero del Inventario (incluye la pestaña "Matriz RBAC") | `http://<host>/` |
| Panel de administración Django | `http://<host>/admin/` |
| API REST del Inventario | `http://<host>/api/` |
| Login propio del tablero | `http://<host>/login/` |
| Matriz RBAC de forma directa (uso interno del iframe; también accesible sola) | `http://<host>/rbac/` — pide sesión Dinamizador/Administrador |

El `db.sqlite3` del Inventario y el `rbac.db` de RBAC que vienen en cada
carpeta **ya están poblados** (38 activos, catálogo MITRE, roles y usuarios
de ejemplo del Inventario; matriz 25×29 del RBAC) — no hay que correr
migraciones ni seeds manualmente para el primer arranque. El contenedor del
Inventario sí aplica `migrate` automáticamente en cada arranque (idempotente,
por si en el futuro agrega migraciones nuevas).

### Cambie las contraseñas de ejemplo antes de exponer esto en la red

El Inventario trae usuarios de ejemplo (`admin` / `SUIIN2026#`,
`dinamizador` / `Dinamizador2026#`, `consultor` / `Consultor2026#`, según su
propio README). Cámbielos ya que este despliegue deja de ser "solo
localhost":

```bash
docker compose exec inventario python manage.py changepassword admin
docker compose exec inventario python manage.py changepassword dinamizador
docker compose exec inventario python manage.py changepassword consultor
```

## 6. TLS / producción real

Este `nginx.conf` sirve en HTTP plano (puerto 80) para simplificar el primer
despliegue. Para producción, tal como ya recomendaban los README de ambos
proyectos originales (nginx con TLS en la VLAN de gestión), agregue un
bloque `server { listen 443 ssl; ... }` con sus certificados (por ejemplo,
emitidos internamente o vía Certbot) y redirija el 80 a 443. Si termina TLS
en un balanceador/firewall (pfSense) delante de este stack en vez de en este
nginx, deje `DJANGO_SSL_REDIRECT=False` en `.env` para evitar bucles de
redirección, y añada ese dominio a `DJANGO_CSRF_TRUSTED`.

## 7. Respaldo

Los datos persistentes viven como archivos normales del host (montados por
bind mount, no ocultos dentro de un volumen Docker gestionado), así que su
esquema de respaldo actual sigue sirviendo tal cual:

- `inventario/db.sqlite3` y `inventario/media/`
- `rbac/rbac.db` (o programe `rbac/respaldar.py` por cron, como ya
  documentaba su propio README)

## 8. Mejoras implementadas sobre la unificación

Sobre la base del despliegue integrado (secciones 1-7), se agregaron las
siguientes mejoras que solo tenían sentido *porque* los proyectos ya
comparten red y gateway:

### 8.1 Trazabilidad real en la bitácora de RBAC (ISO 8.15)

Antes, como varios usuarios ahora entran a RBAC por la misma puerta
(Dinamizador/Administrador), su bitácora encadenada registraba a todos como
`"operador local"`, perdiendo la trazabilidad individual. Ahora:

- Django's `auth_check_rbac` (sección 2) devuelve, además del `204`, un
  header `X-Usuario-Autorizado` con el usuario real de la sesión.
- nginx lo captura de la subpetición interna (`auth_request_set`) y lo
  reenvía a RBAC como `X-Usuario-SGSI` — un cliente no puede falsificarlo
  porque nginx lo fija él mismo, sobrescribiendo cualquier header con ese
  nombre que venga del navegador.
- `rbac/db.py:_responsable_actual()` usa ese header si está presente; si no
  (uso local, scripts de línea de comandos, pruebas), conserva el
  comportamiento original (`"operador local"`).

### 8.2 Prueba automatizada de la puerta de autorización

`inventario/inventario/tests.py` (antes un stub vacío) ahora cubre
`auth_check_rbac` con 6 casos (anónimo, Consultor, Dinamizador,
Administrador, superusuario, y el header de identidad). Si alguien cambia
el modelo de roles sin querer romper esto, la prueba lo va a detectar.

### 8.3 Endpoint de resumen de RBAC (`/api/resumen`)

Expone en JSON los KPIs que ya calculaba la vista `Inicio` de RBAC (roles,
sistemas, usuarios activos, cumplimiento MFA, próximos vencimientos,
excepciones vigentes/vencidas, roles con certificación vencida, y un
`pendientes_total` agregado). Es la base de las dos mejoras siguientes.

### 8.4 Badge de pendientes en la pestaña "Matriz RBAC"

La pestaña de módulo "Matriz RBAC" ahora muestra un contador (igual que ya
hacía "Alertas" con el Inventario) cuando `pendientes_total > 0`. Solo se
consulta si el usuario tiene rol de escritura (mismo criterio que ya usa el
tablero para mostrar/ocultar botones de edición).

### 8.5 Panel ejecutivo unificado

`dashboard_ejecutivo()` (Django) ahora incluye una clave `"rbac"` con el
resultado de `/api/resumen`, obtenida con una llamada **servidor-a-servidor**
dentro de la red de docker-compose (`http://rbac:5000`, no pasa por nginx
ni por su puerta de autorización — esa protege el acceso desde el
navegador, no las llamadas de un backend ya confiable dentro de la misma
red). Si RBAC no responde, la clave queda en `null` y el resto del panel
sigue funcionando igual (probado con RBAC apagado y con RBAC respondiendo).
En el tablero, la pestaña "Panel ejecutivo" agrega una tarjeta
"Cumplimiento de Control de Acceso (RBAC)" con estos indicadores.

La lógica de esta llamada vive en `inventario/inventario/integracion_rbac.py`
(un solo lugar, reusado también por 8.6) — variable de entorno
`RBAC_INTERNAL_URL` (por defecto `http://rbac:5000`) si el nombre del
servicio cambiara.

### 8.6 Cruce en vivo del catálogo de Roles/Sistemas (Inventario ↔ RBAC)

Se detectó que el Inventario mantiene su **propia copia** de la matriz de
accesos (modelos `RolMCA` / `AccesoRol`, con niveles Completo/Modificación/
Lectura) y que el campo `sistema_mca_equivalente` de cada Sistema de
información es **texto libre**, sin ninguna referencia real al `sistema` de
RBAC — dos fuentes de verdad para lo mismo, con riesgo real de
desincronizarse.

En vez de eliminar el modelo local de Django (habría exigido una migración
y tocar el admin y los serializers existentes, con más riesgo del que
justifica esta iteración), se agregó un **cruce en vivo, no destructivo**:

- RBAC expone `/api/sistemas`: catálogo completo con los accesos reales
  por rol (fuente canónica).
- El serializer del Sistema de información en Django
  (`SistemaSerializer.get_accesos_rbac`) busca, por nombre (sin distinguir
  mayúsculas), el sistema cuyo nombre coincide con `sistema_mca_equivalente`
  y devuelve sus accesos reales.
- La ficha de cada activo de tipo Sistema ahora muestra **dos secciones**:
  "Roles con acceso — registrado en el Inventario" (la copia local) y
  "Roles con acceso — según Matriz RBAC (en vivo)" (la fuente canónica). Si
  RBAC no respondió o el nombre no coincide con ningún sistema de la
  matriz, se lo indica explícitamente en vez de mostrar datos
  potencialmente engañosos.

Esto no reemplaza el modelo local todavía — lo dejó explícitamente **visible
y comparable** para que se detecten discrepancias antes de decidir
retirarlo. 3 pruebas Django cubren coincidencia / sin coincidencia / RBAC
caído.

### 8.7 Catálogo MITRE ATT&CK: script de sincronización desde el Inventario

El Inventario mantiene su propio catálogo MITRE (v19.1, importado con
`python manage.py importar_mitre`) y RBAC el suyo
(`static/attack_tecnicas.json`, generado desde el Excel oficial de MITRE).
Al comparar ambos en este momento **son idénticos** (697 técnicas y
subtécnicas en los dos), pero seguían siendo dos copias independientes sin
ninguna garantía de que sigan iguales en la próxima versión de MITRE.

`rbac/catalogo_attack_desde_inventario.py` (nuevo) regenera
`static/attack_tecnicas.json` consultando `/api/amenazas/` del Inventario
en vez de requerir el Excel de MITRE otra vez — probado de extremo a
extremo contra una instancia real del Inventario. Uso:

```bash
cd rbac
INVENTARIO_URL=http://inventario:8000 python3 catalogo_attack_desde_inventario.py
python3 migrar_v2_1.py   # recarga el catálogo en rbac.db, como ya documentaba el flujo original
```

`catalogo_attack_actualizar.py` (a partir del Excel de MITRE) se conserva
tal cual, por si el Inventario no está disponible o se prefiere esa fuente.

### 8.8 Identidad visual unificada (botones y colores)

Las variables de color de `rbac/static/style.css` se remapearon a los
mismos valores hexadecimales que usa el Inventario (verde profundo, acento,
dorado, gris de fondo, colores de riesgo) — sin reescribir cada regla
individual, ya que todas referencian esas variables. Los botones
(`button`, `.boton`) ahora comparten exactamente la misma geometría que
`.btn` del Inventario (padding, radio de borde, tamaño y peso de fuente), y
la tipografía base pasó de "Segoe UI" a Arial/Helvetica, igual que el
Inventario. Las 44 pruebas de RBAC siguen pasando (ninguna dependía de
colores específicos).

### 8.9 Endurecimiento del login (rate limiting + bloqueo por intentos)

Desde la unificación, el login de Django protege el acceso a **los dos**
módulos (Inventario directamente, y RBAC a través de la puerta de
autorización). Eso lo vuelve un objetivo más valioso para un atacante, así
que se reforzó en dos capas independientes:

- **nginx** (`limit_req` sobre `/login/`): máximo 5 solicitudes por minuto
  por IP, con ráfaga de 3 sin demora (`burst=3 nodelay`) y `429` explícito
  al superarla (`limit_req_status 429`). Protege contra volumen, sin
  depender de que la aplicación esté arriba.
- **django-axes** (bloqueo por usuario): `AXES_FAILURE_LIMIT=5`,
  combinando usuario + IP (`AXES_LOCKOUT_PARAMETERS`) para no bloquear a
  toda una VLAN por un solo usuario con la contraseña equivocada; se
  resetea automáticamente tras un login correcto
  (`AXES_RESET_ON_SUCCESS`). Al superar el límite, se muestra una página
  de bloqueo propia (`templates/registration/bloqueado.html`) en vez del
  error genérico de Django.

Ambas capas se probaron de extremo a extremo: nginx real (429 tras la
ráfaga) y Django real (bloqueo tras 5 intentos, incluso con la contraseña
correcta en el sexto, y reseteo del contador tras un login exitoso). Corra
`python3 manage.py migrate` si actualiza un despliegue existente — la
migración de `axes` ya quedó aplicada en el `db.sqlite3` que se entrega.

**MFA (segundo factor):** no se implementó en esta iteración — habilitarlo
bien (enrolamiento con código QR, códigos de respaldo, decidir si es
obligatorio solo para Dinamizador/Administrador o para todos) es una
decisión de producto con superficie propia, no solo configuración. Queda
como próximo paso en la sección 10, con `django-otp` como opción evaluada.

### 8.10 Healthchecks y respaldo único

- **Healthchecks** en `docker-compose.yml` para los tres servicios:
  `inventario` y `rbac` se verifican golpeando su propio puerto interno
  (`/api/sesion/` y `/`, respectivamente); `nginx` expone un endpoint
  dedicado `/healthz` (sin tocar ningún backend, para no mezclar el
  healthcheck con tráfico real ni con el rate limiting del login). `nginx`
  ahora espera (`condition: service_healthy`) a que **ambos** backends
  estén realmente sanos antes de arrancar, no solo iniciados. Probado con
  un nginx real: `/healthz` responde `200 ok` de forma aislada.
- **Respaldo único** (`respaldar_plataforma.py`, en la raíz): reemplaza la
  necesidad de correr por separado el respaldo de RBAC
  (`rbac/respaldar.py`) y una copia manual del Inventario. Empaqueta en un
  solo `.tar.gz` fechado: una copia consistente de `inventario/db.sqlite3`
  y de `rbac/rbac.db` (con el Online Backup API de SQLite — segura de
  correr con los contenedores arriba) más `inventario/media/`. Conserva
  las últimas 30 copias, igual que ya hacía `rbac/respaldar.py`. Probado
  contra los archivos reales del proyecto. Prográmelo en cron:

```bash
0 2 * * *  cd /ruta/suiin-plataforma && python3 respaldar_plataforma.py >> respaldos/respaldar.log 2>&1
```

### 8.11 Detección automática de activos al subir un diagrama

El formulario para subir un diagrama/topología ya tenía un campo para
relacionarlo con activos del inventario (`Diagrama.activos`), pero había
que buscarlos y marcarlos a mano uno por uno en una lista de toda la
organización. Ahora, al elegir un archivo **SVG**, el navegador envía su
contenido a `POST /api/diagramas/sugerir_activos/` (sin guardar nada
todavía) y el formulario **pre-marca** los activos que el diagrama parece
mencionar, mostrando con qué texto de la imagen coincidió cada uno y con
qué confianza — la persona revisa y confirma antes de guardar, la
relación nunca se aplica sola.

**Cómo funciona la coincidencia** (`inventario/deteccion_diagramas.py`):
el SVG es XML, así que sus elementos `<text>` se leen directo con la
librería estándar (sin dependencias nuevas). El texto de un diagrama rara
vez trae el código formal del activo ("RED-003") — normalmente trae un
nombre visible ("pfSense FW") — así que la señal principal es la
**superposición de palabras significativas** entre ese texto y el nombre
del activo (comparar las cadenas completas subestima coincidencias como
"pfSense FW" contra "Firewall — Netgate pfSense NG Firewall", por ser de
longitud muy distinta). Las palabras con dígitos ("r740", "x8-2s") pesan
más que una marca genérica compartida por varios equipos ("Proxmox",
"Dell"), y una lista corta de términos institucionales ("SUIIN", "CRIC",
"topología"...) queda excluida para que no generen coincidencias falsas
solo por aparecer en el título de cualquier diagrama.

**Alcance:** solo SVG. Para PDF o imagen (JPG/PNG) el endpoint responde
`soportado: false` con la razón, y el formulario sigue funcionando
exactamente igual que antes (selección manual) — leer texto de una imagen
o un PDF de forma confiable requeriría OCR, que no se agregó en esta
iteración.

Probado de extremo a extremo (endpoint HTTP real, con y sin autenticación,
con SVG y con PDF) y con 8 pruebas unitarias sobre el algoritmo de
coincidencia, incluyendo el caso que motivó el ajuste de la fórmula
(desambiguar entre tres servidores que comparten la marca "Proxmox" pero
solo uno coincide en el modelo exacto) y el de falso positivo por
boilerplate institucional.

### 8.12 Correlación de riesgo cruzado

Nueva categoría en la pestaña **Alertas**: un activo con `nivel_riesgo`
Crítico o Alto que además tiene **excepciones de acceso vigentes en
RBAC** es una señal compuesta que ninguna de las dos apps ve por separado
— el Inventario sabe que el activo es riesgoso, RBAC sabe que tiene
accesos fuera de lo normal, pero hasta ahora nadie cruzaba las dos cosas.

Reutiliza el cruce por `sistema_mca_equivalente` ya construido en la
sección 8.6: se extendió `/api/sistemas` de RBAC para incluir
`excepciones_vigentes` por sistema, y `alertas()` en Django arma un nuevo
grupo `riesgo_cruzado` cuando ambas condiciones se cumplen a la vez. Si
RBAC no responde, el grupo simplemente no aparece (no rompe el resto de
las alertas, que siguen siendo propias del Inventario) — probado
explícitamente con RBAC real corriendo y con RBAC simulado caído.

3 pruebas automatizadas: activo crítico con excepciones sí aparece (y con
la severidad correcta), activo de riesgo bajo con excepciones no
aparece, y RBAC caído no rompe la respuesta.

### 8.13 Registro de equipos de cómputo como nueva clase de activo

Hasta ahora el Inventario solo distinguía dos clases de activo:
Infraestructura de red (`RED-`) y Sistema de información (`SIS-`) — no
había forma de registrar los equipos de cómputo de usuario final
(escritorios, portátiles) que también son activos del SGSI. Se agregó
una tercera clase, **Equipo de cómputo** (`PC-`), con su propio modelo de
detalle (`EquipoComputo`) además de `ActivoInfraestructura` y
`SistemaInformacion`, siguiendo exactamente el mismo patrón de los dos
existentes (fieldset propio en el formulario que se muestra/oculta según
la clase elegida, sub-serializer anidado, `create()`/`update()` en
`ActivoWriteSerializer`).

**Campos capturados**, pensados para lo que un SGSI necesita rastrear de
un endpoint (ISO/IEC 27002:2022 — 8.1 Dispositivos de punto final de
usuario, 8.7 Protección contra malware):

- Identificación: tipo (escritorio/portátil/tablet/todo-en-uno), marca,
  modelo, serial, dirección MAC.
- Custodia: usuario asignado, ubicación física/sede.
- Especificaciones: sistema operativo, RAM, almacenamiento.
- **Postura de seguridad del endpoint**: antivirus/EDR instalado, disco
  cifrado (BitLocker/LUKS), unido al dominio/SSO corporativo, fecha de
  última actualización del sistema operativo.
- Ciclo de vida: fecha de adquisición, fin de garantía — este último ya
  se cruza automáticamente con la pestaña **Alertas** (mismo criterio de
  severidad que ya aplicaba a infraestructura: vencida = medio, próxima a
  vencer en 90 días = bajo).

También se sumó al KPI "Equipos de cómputo" del Dashboard, al filtro de
clases, y a la ficha de detalle del activo (con su propia insignia de
color azul, `.cl-EQUI`).

6 pruebas automatizadas: creación con código autogenerado (`PC-00N`),
detalle completo, edición parcial (PATCH no pierde el resto de los datos
del equipo), rechazo a usuarios anónimos, aparición en alertas de
garantía, y conteo correcto en `/api/activos/estadisticas/`.

### 8.14 Corrección: catálogo MITRE ATT&CK del buscador de Sistemas (404 bajo el gateway)

Detectado en el navegador (`GET /static/attack_tecnicas.json 404`): el
buscador de técnicas MITRE ATT&CK de las páginas **Sistemas** y **Detalle
de sistema** de RBAC dejaba de funcionar en el despliegue integrado. La
causa: `rbac/static/app.js` pedía el catálogo con una ruta **absoluta
hardcodeada** (`/static/attack_tecnicas.json`). Eso funcionaba con RBAC
sola en la raíz del dominio, pero bajo el gateway esa misma ruta apunta a
la raíz del dominio unificado — servida por el Inventario, no por RBAC —
y devolvía 404. Es un caso distinto de los que ya cubría `ProxyFix`
(sección 3): ese ajusta las URLs que genera **Flask/Jinja** en el
servidor (`url_for()`), pero no tiene ningún efecto sobre rutas
hardcodeadas dentro de JavaScript que corre en el navegador.

La corrección: la URL correcta (ya resuelta con `url_for()`, sensible al
prefijo) se expone en un atributo `data-attack-catalog-url` del `<body>`
(no en un `<script>` inline, que la política de seguridad de contenido de
RBAC habría bloqueado — `script-src 'self'`, sin `'unsafe-inline'`), y
`app.js` lo lee en vez de reconstruir la ruta. Probado en los dos modos
(standalone y tras el gateway) con los headers reales que envía nginx, y
cubierto con una prueba automatizada permanente (46 pruebas RBAC en
total).

**Adenda — el mismo bug reapareció por caché del navegador.** Después de
corregido en el servidor, alguien lo siguió viendo: el navegador seguía
usando la copia vieja de `app.js` (sin recargar con Ctrl+Shift+R, o sin
haber reconstruido la imagen de Docker con `--build`). Para que un
arreglo de código nunca vuelva a quedar enmascarado así, se agregó
*cache-busting* automático: `static_v(filename)` (una función de Jinja)
agrega a la URL de cada estático (`app.js`, `style.css`, `favicon.svg`,
`attack_tecnicas.json`) un parámetro `?v=<fecha de modificación>`. Si el
archivo no cambia, la URL tampoco cambia (el cacheo normal sigue
funcionando); si cambia, la URL cambia y el navegador está obligado a
pedir la copia nueva. 47 pruebas RBAC en total, incluida una que edita la
fecha de modificación de `app.js` y confirma que la URL generada cambia
en consecuencia.

### 8.15 Notificaciones proactivas por correo (resumen semanal de alertas)

Hasta ahora, las alertas del SGSI eran enteramente "pull": el fin de
soporte (EOL), las garantías vencidas, los hallazgos abiertos, las
certificaciones de rol vencidas en RBAC, las excepciones por vencer — todo
esto **solo se veía si alguien entraba a mirar** la pestaña Alertas o el
tablero de Inicio de RBAC. No había ningún aviso que llegara solo.

El comando `python manage.py enviar_resumen_alertas` (Inventario) reutiliza
exactamente el mismo cálculo que ya usa la pestaña Alertas
(`calcular_alertas()`, extraída de la vista para no duplicar la lógica) y
lo combina con el detalle del tablero de Inicio de RBAC
(`GET /api/inicio` — vencimientos próximos, incumplimientos de MFA),
consultado servidor-a-servidor igual que el resto de la integración
(`inventario/integracion_rbac.py`). Envía un correo (texto plano + HTML)
con ambas secciones; si RBAC no responde, lo indica en el correo sin
romper el envío del lado Inventario.

Sin `DJANGO_EMAIL_HOST` configurado, usa el backend de consola de Django
(los correos se imprimen en los logs, no se envían de verdad) — así el
comando nunca falla en un despliegue que todavía no configuró SMTP, solo
no envía nada hasta que se complete esa configuración. Sin destinatarios
configurados (`DJANGO_ALERTAS_EMAIL`), avisa en el log y no hace nada más.
Cubierto con 6 pruebas automatizadas (54 pruebas del Inventario en total),
incluida la verificación de que el HTML y el texto plano realmente
contienen los datos reales de la base de prueba.

Prográmelo en cron, igual que el respaldo (sección 8.10):

```bash
0 7 * * 1  cd /ruta/suiin-plataforma && \
  docker compose exec -T inventario python manage.py enviar_resumen_alertas \
  >> respaldos/alertas.log 2>&1
```

Use `--solo-si-hay-criticas` si prefiere que el comando no envíe nada
cuando no hay alertas crít/alto ni vencimientos próximos en RBAC (por
defecto sí envía siempre, como confirmación de que el resumen sigue vivo).
`--destinatarios correo1@x.com,correo2@x.com` sobrescribe puntualmente los
de `.env` para una prueba manual.

### 8.16 Bitácora encadenada por hash en el Inventario (misma garantía que RBAC)

RBAC ya daba evidencia criptográfica de que su bitácora no había sido
alterada por fuera de la aplicación (cadena de hashes SHA-256, botón
"Verificar integridad" en Auditoría). El Inventario usaba
`django-simple-history` — registra bien quién/cuándo/qué campo cambió,
pero nada impedía editar esa bitácora directamente en la base de datos
sin dejar rastro. Ambas aplicaciones son parte del mismo SGSI y debían dar
la misma garantía.

`inventario/integridad.py` replica el esquema exacto de `rbac/db.py`
(`_hash_registro`, incluido el mismo formato de cadena `anterior|fecha|
entidad|accion|detalle|responsable`) — no es casualidad, es intencional:
quien ya conoce la verificación de RBAC reconoce de inmediato la misma
lógica aquí. Un nuevo modelo `RegistroIntegridad` se llena solo, vía una
señal (`post_create_historical_record` de `django-simple-history`) que se
dispara cada vez que se crea, edita o elimina un `Activo` o cualquiera de
sus modelos de detalle 1:1 (infraestructura, sistema, equipo) o un
`Datacenter` — sin duplicar el detalle campo por campo, que sigue
viviendo donde ya vivía; esto solo agrega la garantía criptográfica
encima del mismo evento. El usuario responsable se toma del middleware ya
configurado (`HistoryRequestMiddleware`), sin necesitar nada nuevo.

`GET /api/integridad/verificar/` recorre toda la cadena y confirma que
cada hash es exactamente el que resulta de recalcular con el registro
anterior — mismo endpoint en espíritu que
`GET /api/auditoria/verificar` de RBAC. Expuesto en la pestaña Bitácora
con el mismo botón "Verificar integridad de la cadena". Probado extremo a
extremo con activos reales creados/editados/eliminados vía la API real
(no solo con mocks), incluyendo alterar una fila directamente en la base
de datos y confirmar que la verificación detecta exactamente cuál — 7
pruebas nuevas (55 pruebas del Inventario en total).

### 8.17 Importación masiva de activos desde Excel

Registrar un lote grande de equipos nuevos (tras una compra, por ejemplo)
significaba cargarlos uno por uno desde el formulario. Sigue el mismo
patrón de dos pasos que ya usaba RBAC para importar la matriz por CSV
(`rbac/rutas.py`: `matriz_importar` / `matriz_importar_confirmar`):

1. **Analizar** (`POST /api/activos/importar/analizar/`): se sube un
   `.xlsx` y se valida fila por fila — sin guardar nada — reutilizando el
   mismo `ActivoWriteSerializer` del formulario individual, para no
   duplicar reglas de validación que podrían desalinearse con el tiempo.
2. **Confirmar** (`POST /api/activos/importar/confirmar/`): crea solo las
   filas que la persona confirmó. Se vuelve a validar cada una (no se
   confía ciegamente en lo que ya analizó el navegador: pudo pasar tiempo
   entre analizar y confirmar), y cada fila se crea de forma
   independiente — si una falla, no bloquea a las demás.

`GET /api/activos/importar/plantilla.xlsx` da una plantilla descargable
con encabezados, una fila de ejemplo, y una segunda hoja con los valores
válidos de cada campo de opciones. El centro de datos se indica por
código (ej. `DC-POPAYAN`), no por id interno. Como cada fila pasa por el
mismo serializer que el formulario individual, las filas creadas quedan
en la bitácora y en la cadena de integridad (sección 8.16) exactamente
igual que si se hubieran creado a mano. Cubierto con 11 pruebas nuevas
(66 pruebas del Inventario en total) y probado extremo a extremo con un
archivo `.xlsx` real generado desde la propia plantilla.

### 8.18 Reporte consolidado exportable (PDF)

Preparar evidencia para una auditoría externa o para la Junta significaba
combinar a mano varias exportaciones parciales (Excel del inventario, CSV
de la matriz, capturas del panel ejecutivo). `GET
/api/reporte-consolidado.pdf` junta en un solo PDF los datos que ya
calcula cada pantalla por separado — no agrega ningún cálculo nuevo, solo
los presenta juntos:

1. Resumen ejecutivo (KPIs del Inventario y de RBAC)
2. Declaración de Aplicabilidad dinámica (cobertura de controles ISO/IEC
   27002:2022)
3. Matriz de riesgo (distribución por nivel + los 15 activos de mayor
   riesgo)
4. Alertas operativas del Inventario, agrupadas por categoría
5. RBAC: roles críticos, cumplimiento MFA, vencimientos próximos

Las vistas `riesgos()`, `cobertura_controles()` y `dashboard_ejecutivo()`
se separaron en funciones puras (`calcular_riesgos()`,
`calcular_cobertura()`, `calcular_panel_ejecutivo()`), mismo patrón que ya
se había usado con `calcular_alertas()` (sección 8.15) — así el reporte
reusa exactamente el mismo cálculo que ya usa cada pantalla, en vez de
duplicar la lógica. El PDF se genera sin comprimir (archivo pequeño, bajo
demanda, no se almacena) para que su contenido quede verificable en texto
plano sin herramientas adicionales — útil tanto para las pruebas
automatizadas como para cualquier revisión manual. Botón "⬇ Reporte
consolidado (PDF)" en el Panel ejecutivo. Cubierto con 5 pruebas nuevas
(71 pruebas del Inventario en total) y probado extremo a extremo con
datos reales de ambas aplicaciones.

## 9. Migración a React (completa)

La interfaz unificada vive en `frontend/` (Vite + React 19). Django e Inventario
siguen como API; RBAC como API JSON bajo `/rbac/api/`; Riesgos sigue embebido
por iframe en `/gestion-riesgos`. Las subsecciones 9.1–9.10 documentan el
historial de la migración fase a fase.

### 9.1 Por qué RBAC necesitaba trabajo primero

El Inventario ya tenía una API REST madura (DRF, 19 endpoints) — portar su
interfaz a React consiste en construir componentes que consuman lo que ya
existe. RBAC, en cambio, era 100% renderizada en el servidor (Jinja2 +
formularios), sin ninguna API JSON. Antes de tocar una sola línea de
interfaz, había que construirle esa API.

### 9.2 API REST de RBAC — completa

(`rbac/api_rest.py` + `negocio.py`). Flask ya no sirve HTML; toda la UI RBAC
está en React. Vive bajo `/rbac/api/` (nginx + auth_request).

### 9.3 Fase 2 — scaffold de React e integración Docker/nginx (completa)

Proyecto nuevo en `frontend/` (Vite + React 19 + react-router-dom 7.18.1,
en modo declarativo únicamente — ver nota de seguridad más abajo).

**Arquitectura de convivencia durante la migración:** nginx sigue
sirviendo la interfaz actual (Django + iframe de RBAC) en `/`, sin ningún
cambio; el build de React convive aparte en **`/app/`** para poder
probarlo en un despliegue real sin arriesgar lo que ya funciona. El día
del corte final (fin de la Fase 4), `/app/` pasa a ser `/` — un cambio de
una línea en `vite.config.js` (`base`) y otra en `nginx.conf`.

**Lo que se construyó:**
- `src/theme.css` — misma paleta e identidad visual exacta que ya usaba
  el resto de la plataforma (ni un valor de color nuevo).
- `src/api/client.js` + `inventario.js` + `rbac.js` — cliente HTTP con el
  manejo de CSRF de cada backend (cookie `csrftoken` para Django,
  `GET /rbac/api/csrf` para RBAC), cubriendo todos los endpoints
  construidos en la Fase 1.
- `Shell.jsx` — encabezado + pestañas de módulo con enrutamiento real de
  React Router (ya no el iframe con `?embed=1`).
- Dos páginas de prueba de concepto, con datos reales: `Dashboard` del
  Inventario (KPIs + tabla de activos) y `Roles` de RBAC (lista +
  certificación).
- `nginx/Dockerfile` (nuevo) — build multi-etapa: compila el frontend con
  Node y copia el resultado a la imagen final de nginx, que no necesita
  Node en tiempo de ejecución. `docker-compose.yml` actualizado para
  construir nginx desde ahí. `nginx.conf` con el nuevo `location /app/`
  (con *fallback* a `index.html` para las rutas de React Router).

**Verificación:** `npm run build` compila limpio. Sintaxis de
`nginx.conf` validada, y probada con un nginx real sirviendo el build
compilado (archivo real → 200; ruta de React Router → cae correctamente a
`index.html`; `/healthz` sin interferencia). El proxy de desarrollo se
probó con **los tres servidores reales corriendo a la vez** (Django, RBAC
y Vite): los dos clientes API devuelven datos reales a través del proxy.
Y lo más importante — **se verificó el renderizado real en un navegador**
(Playwright/Chromium): las dos páginas cargan sin ningún error de consola
y muestran datos reales (38 activos, KPIs correctos, 27 roles con sus
denominaciones y estado de certificación).

*Nota honesta: no se pudo ejecutar `docker compose build`/`up` en este
entorno de trabajo (no hay demonio de Docker disponible aquí) — lo que sí
se verificó exhaustivamente por fuera de Docker (build de producción,
nginx real, navegador real) cubre lo mismo que haría ese build, pero
conviene confirmar el `docker compose up -d --build` completo en un
entorno con Docker antes de dar la Fase 2 por cerrada del todo.*

**Bug real encontrado y corregido en el camino:** al construir el manejo
de CSRF para el cliente de React, se descubrió que con la configuración
de producción documentada (`DEBUG=False`, sin TLS todavía —
`DJANGO_SSL_REDIRECT=False`), `CSRF_COOKIE_SECURE` quedaba en `True` sin
condición, y el navegador descarta cookies `Secure` sobre HTTP plano. Es
decir: **el Inventario, en su configuración de producción documentada, no
podía crear/editar/eliminar nada** — afectaba por igual al JS anterior y
al nuevo cliente de React. Corregido en `config/settings.py`: la cookie
ahora sigue el mismo indicador que ya gobernaba la redirección a HTTPS
(`DJANGO_SSL_REDIRECT`), no `DEBUG` solo. 2 pruebas automatizadas nuevas
verifican los dos escenarios (con y sin TLS). 35 pruebas Django en total.

**Seguridad de dependencias:** `npm audit` marca `react-router-dom` con
un aviso de severidad alta (GHSA-qwww-vcr4-c8h2, CSRF en modo "RSC"). Se
verificó contra el aviso oficial: solo afecta acciones de servidor en
"Framework Mode" o RSC — explícitamente **no afecta** al modo declarativo
(`<BrowserRouter>`), que es el único que usa este proyecto. Documentado
en `vite.config.js` y `frontend/README.md`.

### 9.4 Manejo global de sesión vencida + bug real de enrutamiento en nginx

Cualquier llamada de cualquiera de los dos clientes (Inventario o RBAC)
que devuelva `401` ahora dispara un evento global (`api/client.js`), que
`Shell.jsx` escucha para mostrar un aviso único y dispensable en toda la
app ("Tu sesión venció... Iniciar sesión de nuevo"), en vez de que cada
pantalla maneje ese caso por su cuenta.

Para que esto funcionara con la Matriz RBAC hubo que resolver algo que no
existía antes de React: hasta ahora, `/rbac/` respondía a `401` con una
**redirección** (302 a `/login/`), pensada para navegación de página
completa del navegador — pero `fetch()` sigue redirecciones
automáticamente, así que la SPA habría recibido el HTML de la página de
login como si fuera la respuesta de la API, en vez de un `401` limpio. Se
separó `/rbac/api/` (nueva, para React — nunca redirige) de `/rbac/`
(páginas HTML de Flask que aún quedan del lado viejo — sigue
redirigiendo, sin cambios).

**Bug real encontrado probando el camino con sesión activa** (no solo el
caso "sin sesión", que es el que se prueba primero y más fácil): el
`proxy_pass` de la nueva ubicación recortaba el prefijo completo
`/rbac/api/` en vez de solo `/rbac/`, así que Flask recibía `/roles` (su
página HTML) en lugar de `/api/roles` (la API JSON nueva) — con sesión
válida, `GET /rbac/api/roles` devolvía `200` pero con el **HTML de la
página**, no JSON, y React fallaba al intentar iterar sobre eso como si
fuera una lista. Corregido (`proxy_pass http://rbac_up/api/;`, no
`http://rbac_up/;`) y verificado explícitamente con un nginx real,
sesión autenticada de verdad, y confirmando por `content-type` que la
respuesta es JSON.

*Lección general: probar solo el caso "sin sesión" no alcanza — muchos
bugs de enrutamiento solo aparecen en el camino autenticado, porque son
justamente las peticiones que antes no llegaban tan lejos.*

### 9.5 Fase 3 — pantallas portadas (completa)

**Inventario**: Dashboard, Panel ejecutivo, Alertas, Riesgos (motor del
Inventario), Centro de datos (datacenters + diagramas), Bitácora, ficha de
activo, formularios de creación/edición e importación masiva.

**RBAC**: Inicio (tablero), Roles, Usuarios, Matriz (edición de celda +
comparar), Sistemas, Excepciones (individual y masiva), Auditoría, y todos
los formularios de creación/edición.

Cada módulo tiene sub-navegación propia (`ModuloInventario.jsx`,
`ModuloRBAC.jsx`) con rutas reales (`/app/inventario/alertas`,
`/app/rbac/matriz`…).

**Verificado con navegador real y sesión autenticada**: las pantallas cargan
sin errores de consola, con datos reales. Edición de celda de la Matriz
probada de punta a punta.

**Bug evitado en Fase 3:** el contexto de sesión (`puedeEditar`) no se
propaga automáticamente a través de un `<Outlet>` intermedio — hay que
reenviarlo explícitamente en cada módulo.

### 9.6 Fase 4 — paridad con tablero Django (completa)

1. Tercera pestaña de módulo (`/gestion-riesgos`) embebe SUIIN-SGSI-RIESGOS.
2. Puerta RBAC por rol, badge de pendientes, pruebas Vitest ampliadas.

### 9.7 Corte final — React como interfaz principal (completa)

- `vite.config.js`: `base: '/'`.
- `nginx.conf`: el build de React se sirve en `/`; Django queda en
  `/api/`, `/logout/`, `/admin/`; redirección 301 de `/app/*` a `/*`.
- Retirado `templates/inventario/dashboard.html`; la ruta raíz de Django
  redirige a `/inventario/dashboard` (solo acceso directo al puerto 8000).
- RBAC nativo en React bajo `/rbac/…` (sin iframe en el tablero).

### 9.8 Login en React (completa)

- Pantalla `/login` en la SPA; `POST /api/auth/login/` abre sesión por cookie.
- Rate limiting en nginx sobre `/api/auth/login/`.
- `/logout/` sigue en Django.

### 9.9 Retiro de plantillas HTML de RBAC (completa)

- Eliminadas 15 plantillas Jinja2, `static/app.js`, `static/style.css` y
  `rutas.py` (rutas HTML y formularios POST).
- Flask queda como **API JSON** (`api_rest.py` + `negocio.py`); la UI vive
  en React bajo `/rbac/…`.
- nginx ya no proxea `/rbac/` a Flask — solo `/rbac/api/`; las rutas
  `/rbac/inicio`, `/rbac/matriz`, etc. las sirve la SPA en `/`.
- Se conserva `static/attack_tecnicas.json` para sincronizar el catálogo
  MITRE ATT&CK en la base de datos.

### 9.10 Exportación e importación CSV de la matriz (completa)

- Endpoints JSON/CSV en la API Flask:
  `GET /rbac/api/export/matriz.csv`, `GET /rbac/api/export/accesos_usuarios.csv`,
  `POST /rbac/api/matriz/importar/analizar`, `POST /rbac/api/matriz/importar/confirmar`.
- Pantalla React `/rbac/matriz/importar` (mismo flujo de dos pasos que tenía
  la plantilla HTML retirada).
- Enlaces de exportación en Matriz e Inicio RBAC.

### 9.11 Ficha de activo — cruce Inventario ↔ RBAC (completa)

- `Activo.jsx` muestra las dos secciones de accesos por sistema que ya tenía
  el tablero Django: copia local (`RolMCA`) y matriz RBAC en vivo (`accesos_rbac`).
- Misma semántica que §8.6: `null` en RBAC muestra aviso explícito, no datos
  engañosos.

## 10. Próximos pasos sugeridos (no implementados aún)

- Migrar el Inventario a PostgreSQL (ya recomendado en su README original;
  basta con completar las variables `DJANGO_DB_*` en `.env` y descomentar
  esa sección — el `settings.py` ya soporta el cambio).
- Si más adelante quiere una sesión verdaderamente única entre ambas apps
  (hoy RBAC no tiene noción de "usuario", solo de "autorizado o no" vía
  nginx), podría integrarse con Keycloak (ya presente en la infraestructura
  SUIIN) como IdP común para el Inventario y, con más trabajo, para RBAC.
- TLS real (sección 6).
- Decidir si retirar el modelo local `RolMCA`/`AccesoRol` del Inventario
  ahora que la sección 8.6 permite comparar ambas fuentes en la ficha de
  cada sistema — o dejarlo como respaldo si RBAC no está disponible.
- MFA (segundo factor) para Dinamizador/Administrador — ver sección 8.9.

## 11. Integración con SUIIN-SGSI-RIESGOS (Gestión de Riesgos)

Un tercer módulo se suma a la plataforma: **SUIIN-SGSI-RIESGOS**, la
sistematización de la matriz de riesgos y el Plan de Tratamiento de Riesgos
(PTR) — hasta ahora un proyecto Django + React aparte, con su propio
catálogo de activos. Al integrarlo aquí, ese catálogo propio se retira: pasa
a **consumir los activos directamente del Inventario**, que es la fuente
canónica de esa información en la plataforma.

### 11.1 Por qué no se fusionó como un solo catálogo de base de datos

Se consideraron dos formas de que Riesgos "consuma" los activos del
Inventario:

1. Apuntar el ORM de Riesgos a la misma base de datos del Inventario
   (acoplamiento fuerte, ambas apps comparten esquema).
2. Que Riesgos sincronice desde la **API** del Inventario hacia su propia
   tabla de activos, con un comando que se puede volver a correr.

Se eligió la opción 2, por la misma razón de fondo que ya explica la
sección 1 de este documento: cada aplicación conserva su base de datos y su
ciclo de vida independiente. Un cambio de esquema en el Inventario no puede
tumbar a Riesgos en caliente, y Riesgos puede seguir operando (con la última
copia sincronizada) aunque el Inventario esté temporalmente caído.

### 11.2 Cómo se resuelve la correlación entre catálogos

Los activos de Riesgos venían de una matriz en Excel más antigua que el
Inventario, con su propia numeración (`SI-06` para CENSO, por ejemplo),
mientras que el Inventario usa `SIS-006` para ese mismo activo. El comando
`sincronizar_activos_inventario` (`riesgos/backend/riesgos/management/
commands/`) correlaciona por, en orden: el vínculo ya establecido en una
sincronización previa, el código exacto (los activos `RED-XXX` sí coinciden
entre ambos catálogos desde el origen), el nombre normalizado sin tildes
(cubre la mayoría de los `SI-XX` ↔ `SIS-XXX`), y como último recurso, que un
nombre contenga literalmente al otro. Deliberadamente **no** intenta nada
más difuso que eso — un typo real en uno de los dos catálogos (se encontró
uno real: "MOODLE" en Riesgos vs. "MOODEL" en el Inventario) no debe
autocorregirse en silencio; el comando prefiere reportar un activo sin
vincular a fusionar mal dos activos distintos.

Al vincular, el `id_activo` de Riesgos adopta el código canónico del
Inventario — es seguro porque ninguna relación interna de Riesgos usa ese
código como clave, todas usan el identificador numérico interno.

### 11.3 Qué sigue siendo de quién

| Campo | Fuente canónica |
|---|---|
| Identidad del activo (código, nombre, tipo, IP, clasificación, valoración C-I-D) | Inventario — se sincroniza hacia Riesgos, no al revés |
| Riesgo técnico (vulnerabilidades, cobertura de escaneo, campaña Red Team, plan de tratamiento) | Riesgos — el Inventario no tiene noción de esto |

Si alguien edita un activo directamente en Riesgos (por ejemplo, corrige una
observación de riesgo), esa edición queda protegida en la siguiente
sincronización — el mismo mecanismo que ya protege las reimportaciones de
Excel (sección 8 del README de Riesgos), reutilizado aquí sin duplicar
código (`riesgos/backend/riesgos/sincronizacion.py`).

### 11.4 Enrutamiento

Igual que RBAC, Riesgos se sirve bajo su propio prefijo:

- `/riesgos/` — frontend (React, build estático, mismo patrón que `/app/`).
- `/riesgos/api/` — API REST (Django REST Framework).
- `/riesgos/admin/` — panel de administración de Django.
- `/riesgos/media/` — adjuntos de evidencia subidos por los usuarios.

### 11.4bis Sesión única (JWT)

A diferencia de RBAC (que usa `auth_request` de nginx contra el Inventario en
cada petición), Riesgos verifica una **identidad firmada** sin depender de
que el Inventario esté disponible en el momento de cada llamada:

1. El Inventario ya sabe quién es el usuario y qué rol tiene (sesión +
   `permisos.py`, igual que para RBAC). El endpoint `GET /api/token-jwt/`
   firma esa identidad en un JWT de corta duración (30 min por defecto) con
   `JWT_SHARED_SECRET` — variable de entorno **compartida** entre el
   Inventario y Riesgos (a propósito, a diferencia de `DJANGO_SECRET_KEY`/
   `RIESGOS_SECRET_KEY`, que sí deben ser distintas — ver `.env.example`).
2. Al cargar `/riesgos/`, el frontend intenta ese endpoint en silencio
   (`AuthContext.jsx`) usando la cookie de sesión que ya tenga el navegador.
   Si el Inventario responde con un token, Riesgos queda autenticado sin
   pedir login — si no hay sesión activa (o el Inventario no está
   disponible), no pasa nada visible: cae al login manual de Riesgos, sin
   errores en pantalla.
3. Riesgos verifica la firma **localmente** (`riesgos/auth_jwt.py`) — no
   llama de vuelta al Inventario para validar cada petición. El usuario se
   aprovisiona automáticamente la primera vez que se ve su JWT (mismo
   username que en el Inventario), y su rol decide si puede escribir:
   Consultor solo lee, Dinamizador/Administrador pueden escribir,
   Administrador además obtiene acceso al admin de Django de Riesgos — todo
   recalculado en cada request, así que un cambio de rol en el Inventario se
   refleja en Riesgos en la siguiente petición, sin paso manual aparte.
4. El formulario manual de "Iniciar sesión" de Riesgos ya **no exige una
   cuenta aparte**: prueba primero esas mismas credenciales contra el
   Inventario (mismo endpoint `/api/token-jwt/`, ahora también por
   usuario/clave en vez de solo por cookie), y únicamente si el Inventario
   las rechaza o no está disponible, cae al login propio de Riesgos — que
   sigue existiendo como respaldo para cuando Riesgos corre de forma
   independiente, sin el resto de la plataforma.

Verificado de extremo a extremo con los tres servicios y nginx reales: login
por sesión en el Inventario → cookie real → JWT real a través de
`/api/token-jwt/` → escritura autenticada real en `/riesgos/api/` con ese
JWT, todo pasando por el gateway.

### 11.5 Puesta en marcha

**Automatizado (recomendado):**
```bash
./desplegar.sh --sincronizar
# o, en el primer despliegue de todos, o tras purgar imágenes viejas:
./desplegar.sh --purgar --sincronizar
```
Encadena todo lo de abajo: genera los secretos que falten, detiene lo que esté
corriendo, reconstruye, y **espera de verdad** a que los servicios con
healthcheck queden sanos antes de darse por terminado (usa `docker compose up
--wait`, no una espera fija) — si algo no arranca bien, el script termina con
error ahí mismo en vez de reportar éxito falso. Agregue `--desbloquear
<usuario>` si además necesita liberar una cuenta bloqueada (ver 11.5bis).
`./desplegar.sh --help` para el detalle de cada bandera.

**Manual, paso a paso (lo que hace el script de arriba):**
```bash
cp .env.example .env
python3 generar_secretos.py
# Complete manualmente los valores que el script no pueda generar solo
# (DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED, credenciales de correo, etc.)

docker compose up -d --build

# Primera sincronización del catálogo de activos (el Inventario debe estar
# arriba y saludable — depends_on ya lo garantiza en el arranque normal):
docker compose exec riesgos-backend python manage.py sincronizar_activos_inventario

# Revise en la salida cuántos activos quedaron vinculados por nombre (no por
# código) y confirme que la correlación sea la correcta antes de continuar.
```

### 11.5quinquies "sincronizar_activos_inventario" da 400 Bad Request

Hallazgo real de un despliegue: `docker compose exec riesgos-backend python
manage.py sincronizar_activos_inventario` fallaba con
`400 Client Error: Bad Request for url: http://inventario:8000/api/activos/`
— pero el sitio funcionaba perfectamente para las personas.

La causa: ese comando llama a `http://inventario:8000/...` **directo**,
contenedor a contenedor dentro de la red de docker-compose, sin pasar por
nginx — a diferencia de todo el tráfico de usuarios, que sí pasa por nginx
(que reescribe el header `Host` al dominio público antes de reenviarlo). Con
`Host: inventario:8000`, Django lo rechazaba porque `inventario` (el nombre
del servicio) no estaba en `DJANGO_ALLOWED_HOSTS` — nadie tenía por qué haber
pensado en agregarlo ahí, es un detalle interno de la red de contenedores, no
un dominio público.

`inventario/config/settings.py` ahora agrega `'inventario'` a `ALLOWED_HOSTS`
**siempre**, sin importar qué tenga configurado `DJANGO_ALLOWED_HOSTS` en el
`.env` — no depende de que alguien se acuerde de incluirlo a mano. Verificado
con una petición real simulando el `Host` exacto que manda ese comando, y con
una prueba de control que confirma que esto no abre la puerta a cualquier
dominio — solo al nombre interno específico que hacía falta.

### 11.5quater "nginx" no queda "healthy" aunque todo funcione bien

Si `docker compose ps` muestra `suiin-nginx` como `unhealthy` pero el sitio
carga bien en el navegador (o `docker compose logs nginx` muestra tráfico
real respondiendo `200`), es un desajuste entre IPv4 e IPv6 dentro del
contenedor, no un problema del gateway en sí — se diagnosticó con un
despliegue real:

- El entrypoint oficial de la imagen `nginx:alpine` intenta agregar soporte
  IPv6 al `server{}` automáticamente al arrancar, pero como `nginx.conf` se
  monta de solo lectura (`:ro` en `docker-compose.yml`, a propósito, para que
  nadie edite la configuración corriendo del contenedor), no puede — queda
  registrado como un aviso inofensivo en el log
  (`can not modify /etc/nginx/conf.d/default.conf`).
- Sin ese soporte, nginx solo escucha en IPv4 (`listen 80;`). El tráfico real
  entra bien porque Docker reenvía el puerto del host directo por IPv4. Pero
  el propio healthcheck, corriendo *dentro* del contenedor con `wget
  http://localhost/...`, puede resolver "localhost" primero a `::1` (IPv6) —
  ahí no hay nada escuchando, así que falla con "Connection refused", aunque
  el servidor esté perfectamente sano.

Los cuatro healthchecks del `docker-compose.yml` ya usan `127.0.0.1` en vez
de `localhost` — sin ambigüedad de resolución posible, ya no depende de qué
prefiera el contenedor. Si aun así ve este síntoma en un healthcheck nuevo
que agregue más adelante, use `127.0.0.1` (o el puerto del servicio) en vez
de `localhost` ahí también.

### 11.5ter Guardia contra secretos sin configurar

Hallazgo real, más serio que el bloqueo de login: un despliegue corrió con
`DJANGO_DEBUG=False` mientras `DJANGO_SECRET_KEY`, `RIESGOS_SECRET_KEY` y
`JWT_SHARED_SECRET` seguían siendo literalmente el texto de ejemplo de
`.env.example` — nunca se reemplazaron. Como esa plantilla es pública (viene
con el proyecto), cualquiera que la haya visto conoce esos mismos "secretos":
podría forjar sesiones de Django, o directamente un JWT que diga "soy
Administrador" para cualquier usuario, sin ninguna contraseña.

Las tres aplicaciones ahora **se niegan a arrancar** si detectan esto — no es
una advertencia que se pueda pasar por alto:

- Con `DJANGO_DEBUG=False` (o sin definir, en el caso de RBAC) y un valor que
  empiece con `defina-` (el marcador de la plantilla) o `django-insecure-`/
  `suiin-rbac-desarrollo-` (los valores por defecto del propio código): la app
  lanza una excepción al arrancar y el contenedor no queda arriba — el error
  en los logs dice exactamente qué variable falta por configurar.
- Con `DJANGO_DEBUG=True`: solo advierte (para no estorbar el desarrollo
  local), pero dice explícitamente que eso no debe llegar a producción.

Si al desplegar un contenedor no arranca y el log menciona "valor de ejemplo
de .env.example", es esto — genere valores reales para las cuatro variables
de una sola vez con:
```bash
python3 generar_secretos.py
```
(detecta solo las que sigan con el valor de ejemplo, sin tocar ninguna que ya
haya configurado — seguro de correr más de una vez por error. Deja un
respaldo con fecha del `.env` anterior junto al original.)

### 11.5bis "No me deja entrar" — dos capas de bloqueo distintas, no una

Si el login rechaza credenciales que son correctas, hay **dos mecanismos
independientes** que pueden estar bloqueando, y hay que saber cuál es:

1. **django-axes** (por cuenta) — bloquea la combinación usuario+IP tras 5
   intentos fallidos, por 1 hora (`AXES_COOLOFF_TIME`). Se desbloquea con:
   ```bash
   docker compose exec inventario python manage.py desbloquear_login <usuario>
   docker compose exec riesgos-backend python manage.py desbloquear_login <usuario>
   ```
   (son contadores independientes — resetee en los dos si probó el login en
   ambos). Este comando (no el `axes_reset_username` nativo de la librería)
   es el recomendado: muestra el estado real antes y después con datos de la
   base — no un mensaje genérico de "N intentos eliminados" que no siempre
   refleja lo que realmente pasó en un despliegue real. También busca el
   username guardado con mayúsculas o espacios distintos, y acepta `--todos`
   para limpiar cualquier bloqueo de cualquier usuario/IP de una sola vez si
   no está claro cuál es el que está aplicando.

2. **nginx `limit_req`** (por IP, sin importar la cuenta) — protege `/login/`,
   `/riesgos/api/auth/login/` y los POST de `/api/token-jwt/` contra ráfagas de
   intentos. **Un reset de axes NO lo toca** — son sistemas completamente
   distintos (uno vive en la base de datos de Django, el otro en memoria
   compartida dentro de nginx). Si ejecutó el reset de axes y el login *sigue*
   mostrando la misma pantalla de bloqueo con el branding de la aplicación (no
   un error 429 genérico), es señal de que en realidad sigue siendo axes — pero
   si cambia a un error distinto o más simple, es nginx. Para este caso, o
   simplemente para no esperar a que el cupo se libere solo:
   ```bash
   docker compose restart nginx
   ```
   (un `reload` no siempre libera la memoria compartida del límite; `restart`
   sí, de forma confiable).

El login unificado de riesgos (11.4bis) manda **dos peticiones POST** por cada
intento humano (primero prueba el JWT del Inventario, si falla cae al login
propio) — con eso en mente, el cupo de nginx se calibró a 10 solicitudes/min
con ráfaga de 6 (ver el comentario en `nginx/nginx.conf`), y las peticiones GET
(el chequeo silencioso de sesión que se dispara solo al cargar `/riesgos/`, sin
que la persona haga nada) quedan explícitamente fuera de ese cupo — antes
compartían el mismo límite que un POST con credenciales, lo que hacía que
recargar la página un par de veces, sumado a un par de intentos reales,
alcanzara a agotarlo sin que hubiera ningún ataque de por medio.

### 11.4ter Riesgos embebido en la misma página del Inventario (no otra pestaña del navegador)

Igual que la Matriz RBAC (ver más abajo), SUIIN-SGSI-RIESGOS ahora se
incrusta como una pestaña más dentro de la página del Inventario —
`riesgos/frontend/src/components/Layout.jsx` detecta `?embed=1` en la URL
(mismo mecanismo que `rbac/templates/base.html`) y oculta lo decorativo,
dejando la navegación funcional intacta. El Inventario inyecta
`<iframe src="/riesgos/?embed=1">` al hacer clic en la pestaña "Gestión de
Riesgos y PTR", en vez de navegar a otra URL.

**Corrección sobre la primera versión de esto:** al principio se ocultaba el
`<aside>` completo en modo embebido — la primera prueba real reveló el
problema: eso también ocultaba la navegación (Activos, Riesgos contextuales,
Plan de tratamiento, etc.), dejando a quien entra embebido solo con el Panel
general, sin forma de llegar a las demás páginas. La corrección sigue el
mismo criterio exacto que ya usaba RBAC (`rbac/templates/base.html`): oculta
solo el bloque de marca de arriba, el pie "Consejo Regional..." y el enlace
"Volver a Soluciones SUIIN" — la barra de navegación se mantiene siempre
visible y funcional, embebido o no.

A diferencia de RBAC (que no tiene control de acceso propio — todo pasa por
`auth_request` de nginx), esta pestaña **no** se condiciona a
`puedeEditar`: riesgos ya trae su propio control por rol vía el JWT de
sesión única (Consultor=solo lectura, Dinamizador/Administrador=escritura),
así que cualquier sesión válida puede entrar a ver — lo que cada quien puede
editar lo decide riesgos por su cuenta, adentro.

Verificado con un navegador real (Playwright, no solo revisando el código):
en acceso directo (`/riesgos/`) se ve la marca, el pie y el enlace de
volver; en modo embebido (`/riesgos/?embed=1`) esos tres desaparecen pero
las 7 páginas de navegación siguen visibles y funcionan — se probó haciendo
clic real en "Activos" estando embebido y confirmando que navega y carga
datos reales sin salir del panel. También se confirmó de punta a punta
haciendo clic en la pestaña real del Inventario.

**Nota de diseño (decisión del cliente):** se dejó el tema oscuro de riesgos
sin modificar dentro del panel embebido — el problema que se resolvió fue la
navegación (ya no sale de la página), no el contraste visual claro/oscuro
entre el Inventario y Riesgos.

### 11.6 Próximos pasos específicos de esta integración

- ~~Sesión única con el Inventario~~ — ✅ hecho (ver 11.4bis).
- ~~Riesgos se sentía "como otra página" al navegar desde el Inventario~~ —
  ✅ hecho (ver 11.4ter). Ahora se incrusta como pestaña, mismo patrón que
  ya usaba la Matriz RBAC.
- ~~"No me deja entrar" con axes reseteado pero el bloqueo persiste~~ — ✅
  hecho (ver 11.5bis). Causa real: el límite de nginx (`login_limit`) es un
  sistema aparte de django-axes, que ningún comando de Django puede tocar, y
  antes compartía cupo con el chequeo pasivo de sesión — fácil de agotar sin
  que fuera un ataque real.
- Programar `sincronizar_activos_inventario` en un cron/systemd timer
  periódico, igual que ya se sugiere para `enviar_alertas_vencimiento` en el
  README de Riesgos.
- Archivos estáticos del admin de Django de Riesgos: a diferencia del
  Inventario, este Dockerfile no corre `collectstatic` todavía (el admin
  funciona, pero sin su hoja de estilos — no afecta al frontend React, que
  es la interfaz principal). Replicar el patrón de `static_data` del
  Inventario si se necesita el admin con su estilo completo.
- Migrar `db.sqlite3` de Riesgos a PostgreSQL si más de un analista empieza
  a editar simultáneamente (mismo razonamiento que la sección 10 para el
  Inventario).

## 12. "Matriz RBAC" fallaba intermitente con un ícono de archivo roto (2026-08-26)

Hallazgo real, con dos capturas del usuario. Con sesión de administrador
activa, el panel embebido de Matriz RBAC a veces cargaba perfecto y a veces
mostraba un ícono de archivo roto en vez del contenido — intermitente, no
en una pestaña específica (se confirmó navegando Inicio→Roles→Sistemas→
Usuarios→Excepciones→Auditoría varias veces: unas rondas todas cargaban
bien, otras fallaban a mitad de camino).

**Diagnóstico, paso a paso, con evidencia real en cada uno:**
1. Se descartó que fuera el código en sí — reproducido con navegador real,
   sesión de administrador (tanto `is_superuser` como por Grupo de Django,
   las dos formas reales de tener el rol), y RBAC cargó perfecto las dos
   veces en un entorno de prueba limpio.
2. Se descartó `SESSION_COOKIE_SECURE` (HTTPS vs HTTP) — el `.env` real
   tenía `DJANGO_SSL_REDIRECT=False` explícito, confirmado por el usuario.
3. Se descartó que RBAC mismo generara la redirección — ninguno de sus
   `redirect()` internos apunta a `/login/`.
4. **La pista real**: los logs de nginx mostraron que la petición que fallaba
   (`GET /rbac/matriz?embed=1` → 302) sí había llegado hasta RBAC (el log de
   *errores* de nginx mostró un aviso de "upstream response buffered to a
   temporary file" para esa misma petición) — pero el Inventario no tenía
   **ningún** registro de haber recibido la verificación de autorización
   (`/api/auth-rbac/`) en ese momento, ni exitosa ni fallida.
5. Se confirmó que el Inventario ya corre con `gunicorn --workers 3` (no el
   servidor de desarrollo de un solo hilo) — pero **3 procesos separados,
   cada uno con su propia conexión al mismo `db.sqlite3`**, sobre el modo
   de journaling por defecto de SQLite (rollback journal), que bloquea
   lecturas mientras hay una escritura en curso.
6. `auth_check_rbac` (la vista que decide si se puede entrar a RBAC) *lee*
   la sesión de Django desde esa misma base de datos — si en ese instante
   otro worker está *escribiendo* algo en ella (ej. actualizando la sesión
   en otra petición concurrente, algo común bajo uso simultáneo real de
   Inventario + Riesgos + RBAC), esa lectura puede toparse con un bloqueo.

**Verificado de forma directa, no solo en teoría**: una prueba con 8
escritores y 10 lectores concurrentes sobre SQLite, sin el modo WAL,
produjo **0 de 500 lecturas exitosas** (3205 errores de "database is
locked"). La misma prueba, con el modo WAL activado, produjo **500 de 500
lecturas exitosas** — las lecturas dejan de bloquearse por las escrituras
concurrentes, que es exactamente el mecanismo que necesitaba
`auth_check_rbac` para no fallar bajo tráfico simultáneo real.

**Corrección aplicada** en `inventario/config/settings.py` y
`riesgos/backend/suiin_riesgos_config/settings.py` (mismo patrón en los
dos — riesgos corre igual, `gunicorn --workers 3` + SQLite, expuesto al
mismo riesgo aunque el síntoma reportado fuera específico de RBAC):

```python
'OPTIONS': {
    'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;',
    'timeout': 20,
}
```

Confirmado con la base de datos real de ambos proyectos: `PRAGMA
journal_mode` devuelve `wal` tras el cambio. 84 pruebas del Inventario y
258 de Riesgos siguen pasando sin cambios (esta corrección no toca ninguna
lógica de negocio, solo cómo SQLite maneja el acceso concurrente).

No se tocó nginx — su `proxy_read_timeout` por defecto (60s) ya da margen
de sobra sobre el `timeout: 20` configurado arriba.

**Esto no reemplaza la recomendación de PostgreSQL** si en algún momento
hay escritura pesada y sostenida (varios analistas editando a la vez, todo
el tiempo) — WAL resuelve bien el patrón real de esta plataforma (muchas
lecturas, escrituras cortas y esporádicas), pero PostgreSQL sigue siendo la
opción más robusta si ese patrón cambia.

## 13. La misma falla, un segundo hallazgo real y complementario (no redundante)

Con la corrección de la sección 12 (modo WAL) aplicada, la causa raíz de la
falla *intermitente* de autorización queda resuelta. Pero investigando el
mismo síntoma desde otro ángulo — el mensaje exacto de la consola del
navegador, no los logs del servidor — apareció un segundo problema real,
independiente: **incluso cuando la verificación de sesión falla por
cualquier otro motivo** (no solo el bloqueo de SQLite ya corregido — podría
ser una sesión genuinamente vencida, un problema de red pasajero, etc.), lo
que el usuario veía no era una pantalla de login clara, sino un ícono de
archivo roto, sin ningún mensaje.

**El hallazgo, confirmado con el error exacto de la consola:**
```
Refused to display 'http://127.0.0.1/' in a frame because it set
'X-Frame-Options' to 'deny'.
```

RBAC ya tenía `X-Frame-Options: SAMEORIGIN` puesto correctamente desde
antes (con un comentario que anticipaba exactamente este escenario: "el
módulo ahora se incrusta en un `<iframe>` del Inventario"). Pero el
**Inventario mismo** seguía en `DENY`. Cuando la verificación de sesión de
RBAC falla, nginx redirige a `/login/?next=/rbac/` del Inventario como
respaldo — y esa página, con `DENY`, el navegador se niega a mostrarla
dentro de *cualquier* iframe, incluyendo el suyo propio. El resultado visual
es justo el ícono roto reportado.

**Corrección** en `inventario/config/settings.py` — mismo criterio que ya
tenía RBAC:
```python
X_FRAME_OPTIONS = 'SAMEORIGIN'  # antes: 'DENY'
```

**Segundo hallazgo, en el camino, sin relación con el anterior:** la
consola también mostraba errores de política CSP bloqueando las fuentes de
Google (Space Grotesk/Inter/IBM Plex Mono) que se habían agregado a RBAC en
el rediseño visual, sin revisar en ese momento que la CSP de `rbac/auth.py`
no las permitía — RBAC caía en silencio a la fuente del sistema. Se
agregaron `fonts.googleapis.com` (a `style-src`) y `fonts.gstatic.com`
(nuevo `font-src`) a la política.

**Por qué esta corrección sigue siendo necesaria aunque el modo WAL ya
resuelva la causa más común de fallo:** es defensa en profundidad — WAL
elimina la intermitencia causada por bloqueos de SQLite, pero cualquier
otro motivo de sesión no sincronizada (uno genuinamente expirado, por
ejemplo) seguiría cayendo en el mismo camino de respaldo a `/login/`. Antes
de esta corrección, ese camino de respaldo estaba roto en sí mismo — ahora
muestra una pantalla de login usable en vez de un ícono sin ningún mensaje.

**Verificado con rigor:**
- Se probó primero con `override_settings(DEBUG=False)` en las pruebas —
  no funcionó, porque `X_FRAME_OPTIONS` vive dentro de un bloque
  `if not DEBUG:` que se evalúa una sola vez al cargar `settings.py`, no en
  cada prueba. Se corrigió usando un subproceso real con las variables de
  entorno reales (incluyendo `DJANGO_SSL_REDIRECT=False`, como en el `.env`
  real confirmado por el usuario — sin esa variable, `SECURE_SSL_REDIRECT`
  devuelve un 301 antes de llegar a la vista, y la prueba falla por un
  motivo distinto al que intenta cubrir).
- Se revirtió cada corrección por separado (`X_FRAME_OPTIONS` de vuelta a
  `DENY`; la CSP sin las fuentes de Google) y se confirmó que las pruebas
  nuevas fallan exactamente como deberían — 2 en el Inventario, 1 en RBAC —
  antes de restaurar la versión correcta.
- 106 pruebas de RBAC (105 + 1 nueva) y 86 del Inventario (84 + 2 nuevas)
  pasando. 258 de Riesgos y 117 de su frontend, sin cambios, confirmadas
  sin afectación.

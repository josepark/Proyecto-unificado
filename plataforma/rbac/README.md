# SUIIN-RBAC v2.1 — Sistematización de la Matriz de Control de Acceso

Sistema de información para gestionar la Matriz de Control de Acceso Basado en
Roles del SUIIN/CRIC, documento fuente **SUIIN-SGSI-MCA-001 v2.0**.

Base normativa: ISO/IEC 27002:2022 (5.15–5.18 y 8.15) · POL-SI-002 ·
MAN-POL-SI-002 · Determinación 7 CRIC-Nacional (Decisión No. 02 / 02-Ene-2025)
· NIST SP 800-63B · Ley 1581 de 2012.

## Arquitectura (v2.0)

| Módulo | Responsabilidad |
|---|---|
| `app.py` | Fábrica de la aplicación Flask (solo API JSON) |
| `api_rest.py` | Endpoints REST bajo `/api/` (consumidos por la SPA React) |
| `negocio.py` | Validaciones y constantes compartidas |
| `db.py` | Conexión SQLite (WAL), **bitácora encadenada por hash**, **vencimientos automáticos** |
| `auth.py` | CSRF por token y encabezados de seguridad |
| `schema.sql` / `seed.py` | Esquema (10 tablas + 3 vistas) y carga inicial con datos reales |
| `tests/` | Suite `pytest` (API REST + integración) |
| `migrar_v2_1.py` | Migración acumulativa desde cualquier versión anterior |
| `catalogo_attack.py` | Sincroniza `static/attack_tecnicas.json` con la tabla `attack_tecnica` |
| `catalogo_attack_actualizar.py` | Regenera el catálogo MITRE ATT&CK desde el Excel oficial |
| `respaldar.py` | Respaldo consistente con retención de 30 copias |
| `run_produccion.sh` / `suiin-rbac.service` | Despliegue con gunicorn + systemd |

## Instalación

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 seed.py        # crea rbac.db con los datos del documento MCA-001
python3 app.py         # http://localhost:5000/api/csrf — solo API (UI en React)
```

## Seguridad (v2.1 — sin inicio de sesión)

La aplicación no exige autenticación: está pensada para uso **local o
monousuario**. IMPORTANTE: no la exponga a la red; manténgala en
127.0.0.1 o restrinja el puerto con firewall, porque cualquiera con
alcance al puerto puede modificar la matriz. La bitácora registra
"operador local" como responsable. Protecciones vigentes:

- **Bitácora encadenada**: cada registro incluye el SHA-256 del anterior;
  el botón «Verificar integridad» en Auditoría detecta cualquier alteración
  hecha por fuera de la aplicación e indica el registro exacto donde se
  rompe la cadena (evidencia 8.15).
- **Vencimientos automáticos**: al usarse la aplicación (a lo sumo una
  revisión por minuto) los usuarios temporales con fecha vencida pasan a
  Suspendido y las excepciones vencidas se retiran, todo con traza. La vista
  de accesos efectivos excluye además cualquier excepción vencida.
- **CSRF por token de sesión** en todos los formularios; encabezados
  X-Frame-Options, CSP, nosniff y Referrer-Policy; cookies HttpOnly/SameSite.

## Catálogo MITRE ATT&CK

El campo «Técnicas ATT&CK» de cada sistema ya no es texto libre: es un
buscador con selección múltiple (chips) contra el catálogo oficial de
MITRE ATT&CK Enterprise (697 técnicas y subtécnicas). El servidor valida
cada código contra la tabla `attack_tecnica` antes de guardar.

Los datos viven en `static/attack_tecnicas.json` (usado también por el
buscador del navegador) y se sincronizan con la base al ejecutar `seed.py`
o `migrar_v2_1.py`. Para actualizar el catálogo cuando MITRE publique una
nueva versión, descargue el Excel oficial desde
https://attack.mitre.org/resources/attack-data-and-tools/ y ejecute:

```bash
pip install openpyxl --break-system-packages   # o vía requirements-dev.txt
python3 catalogo_attack_actualizar.py ruta/enterprise-attack-vXX.xlsx
python3 migrar_v2_1.py                          # recarga el catálogo en rbac.db
```

## Funcionalidad

**Nuevo en interfaz:** páginas de error (404/403/413/500) con la
identidad visual de la aplicación en vez de la página genérica de Flask
o texto plano; favicon con el motivo de anillos institucional; soporte
responsive básico (menú, formularios y tablas se adaptan en pantallas
angostas — la Matriz conserva su scroll horizontal por diseño); la ficha
de cada rol y sistema enlaza a su propio historial de auditoría, igual
que ya hacía la de usuario. De paso corregí un bug real que esto dejó al
descubierto: las fichas de usuario/rol/sistema con un id inexistente
rompían con un error 500 en vez de un 404 claro.

**Nuevo en la Matriz:** cada celda se guarda al instante por AJAX, sin
recargar la página, con un aviso flotante y un botón «Deshacer» que
revierte el cambio con un clic · buscador rápido de sistema (Enter para
desplazarse a la fila) · comparar dos roles lado a lado
(`/matriz/comparar`) para revisiones de mínimo privilegio, resaltando en
qué sistemas difiere el nivel de acceso.

**Nuevo:** certificación periódica de accesos por rol (control 5.18 /
POL-SI-002) — cada rol activo muestra su última revisión y si está vencida
según su periodicidad declarada, con un botón para dejar constancia
(fecha + nota) en la bitácora · clonar un rol existente al crear uno
nuevo, copiando su fila completa de la matriz como punto de partida ·
importar la matriz desde CSV (`/matriz/importar`): analiza el archivo,
muestra un resumen de los cambios y advertencias antes de aplicar nada, y
solo escribe lo que se confirme explícitamente · asignación masiva de
excepciones (`/excepciones/masiva`): aplica la misma excepción de acceso
a varios usuarios a la vez, cada una registrada individualmente en la
bitácora.

Tablero con métricas, panel de gráficos (roles por nivel de riesgo MITRE
ATT&CK y cumplimiento MFA, en CSS/SVG sin dependencias externas), alertas
de cumplimiento MFA y **alertas preventivas de vencimientos próximos**
(usuarios temporales y excepciones que vencen en los próximos 7 días,
antes de que el sistema los suspenda/retire automáticamente) · Matriz
25×29 editable con filtros y CSV · Roles y Sistemas con búsqueda/filtro,
ciclo completo (crear, editar, desactivar, eliminar con salvaguardas —
un rol con usuarios o un sistema con excepciones documentadas no se
puede eliminar, solo desactivar, para no perder la trazabilidad) y
validación de los formularios (código/nombre obligatorios, grupo,
categoría, clasificación y riesgo ATT&CK verificados antes de guardar) ·
Alta de usuario con formulario guiado por secciones (identidad,
cumplimiento, vigencia), ayuda dinámica del requisito de MFA del rol
elegido, fechas de vigencia exigidas solo para acceso Temporal, y
validación de nombre, rol y coherencia de fechas antes de guardar ·
Usuarios con búsqueda y filtro por estado/rol; el alta y la edición
comparten el mismo formulario guiado por secciones (identidad, cumplimiento,
vigencia) con ayuda dinámica del requisito de MFA del rol elegido y
validación de coherencia de fechas; cada ficha enlaza directo a su
historial de auditoría (`/auditoria?q=`) · Asignación de sistemas por
selector (las diferencias con el rol se registran como excepciones
documentadas del 5.18, con motivo obligatorio y vigencia) · Reporte
consolidado de excepciones vigentes y vencidas (`/excepciones`), con
acceso directo para retirarlas, pensado para la revisión periódica del
control 5.18 · Auditoría con filtro por entidad/acción y paginación,
verificable · Exportación de accesos efectivos con marca de excepción y
celdas protegidas contra inyección de fórmulas (CSV/Formula Injection) en
Excel/Sheets.

## Seguridad de aplicación (8.26)

Todo el JavaScript vive en `static/app.js`; las plantillas no usan
atributos `onclick`/`onchange`/`onsubmit` inline, sino `data-confirm` y
`data-auto-submit`, delegados por ese único archivo. Esto permite que la
Content-Security-Policy exija `script-src 'self'` sin `'unsafe-inline'`.
`style-src` conserva `'unsafe-inline'` porque las plantillas usan
atributos `style=""` puntuales para anchos/márgenes; retirarlo implicaría
migrar esos estilos a clases CSS en todas las plantillas.

## Actualización desde versiones anteriores

Copie los archivos nuevos sobre la carpeta (conserve su `rbac.db`) y ejecute
una vez `python3 migrar_v2_1.py`: agrega columnas y tablas faltantes (incluida
`acceso_excepcion`) y calcula la cadena de hashes del histórico. La versión
2.1 no usa inicio de sesión, por lo que no crea ninguna cuenta. No se pierde
ningún dato.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q        # 40 pruebas: acceso, CSRF, encabezados (incluida la CSP
                 # sin 'unsafe-inline' en script-src), negocio, vencimientos,
                 # salvaguardas (roles y sistemas), cadena de auditoría,
                 # validación de alta y edición de usuario, nivel inválido
                 # en la matriz, inyección de fórmulas en CSV, alertas de
                 # vencimiento próximo, catálogo MITRE ATT&CK, búsqueda en
                 # auditoría, detección de duplicados, certificación de
                 # roles, clonado de rol, importación de matriz por CSV,
                 # asignación masiva de excepciones, guardado AJAX de la
                 # matriz, comparación de roles, páginas de error y 404
                 # en fichas inexistentes
```

## Producción

gunicorn con 4 procesos (`run_produccion.sh`), detrás de nginx con TLS en la
VLAN de gestión; unidad systemd de ejemplo incluida. Active
`SESSION_COOKIE_SECURE=True` en `app.py` al servir por HTTPS y defina
`SUIIN_RBAC_SECRET` con un valor aleatorio largo. Programe `respaldar.py`
en cron según la política de copias de respaldo.

— Camino del SUIIN · CRIC

# Frontend — Soluciones SUIIN (Fase 4, en migración)

SPA de React que va reemplazando, módulo por módulo, tanto el JS embebido
del Inventario como las plantillas de RBAC + los iframes del tablero
Django. Ver `README-DESPLIEGUE.md` (raíz del proyecto), sección 9, para el
contexto completo de la migración.

**Estado actual:** Fase 3 cerrada (todas las pantallas de Inventario y RBAC
portadas). Fase 4 en curso: módulo PTR embebido, puerta RBAC por rol, badge
de pendientes, pruebas Vitest ampliadas. Pendiente del corte final (`base`
`'/'`, retirar `dashboard.html`).

## Desarrollo local

Con el Inventario (`127.0.0.1:8000`) y RBAC (`127.0.0.1:5000`) corriendo
por separado (fuera de Docker, como cualquier app Django/Flask normal):

```bash
npm install
npm run dev
```

Abre `http://127.0.0.1:5173/app/`. El proxy de desarrollo (`vite.config.js`)
reenvía `/api` al Inventario y `/rbac` a RBAC, con el mismo recorte de
prefijo que hace nginx en producción — así el mismo código funciona igual
en desarrollo y en producción, sin ninguna URL hardcodeada por entorno.

## Pruebas

```bash
npm test          # corre toda la suite una vez
npm run test:watch  # modo interactivo, vuelve a correr al guardar
```

Vitest + Testing Library + jsdom (antes no había ninguna prueba de
frontend — solo las del backend). Hay un archivo `*.test.jsx` junto a
cada componente que lo cubre, con tres patrones de referencia para
extender la suite:

- **`Riesgos.test.jsx`** — página de solo lectura: simula `fetch()` según
  la URL pedida y verifica que se muestren datos reales de la respuesta.
- **`ActivoForm.test.jsx`** — formulario de escritura: valida que un envío
  inválido muestre el error del backend sin navegar, y que uno válido
  cree el recurso y navegue a su ficha.
- **`Activo.test.jsx`** — guardas de rol: envuelve la ruta en un
  `<Outlet context={...}>` propio para simular `puedeEditar`/
  `puedeEliminar` sin montar todo `Shell.jsx`, y verifica qué botones
  aparecen para cada rol.

Mismo mecanismo en los tres casos: se simula `global.fetch` directamente
(la misma función que ya usa `src/api/client.js`), no los módulos de la
API — así la prueba también verifica que el cliente HTTP real arma bien
la petición y procesa la respuesta.

## Estructura

```
src/
├── theme.css              Paleta e identidad visual (misma que el resto de la plataforma)
├── App.jsx                Rutas de los dos módulos (anidadas, una sub-navegación por módulo)
├── componentes/
│   ├── Shell.jsx              Encabezado + pestañas de módulo + aviso de sesión vencida
│   ├── ModuloInventario.jsx    Sub-navegación del Inventario
│   ├── ModuloRBAC.jsx           Sub-navegación de RBAC (Roles/Usuarios/Matriz/…)
│   ├── PuertaRBAC.jsx           Guardia de rol antes de ModuloRBAC
│   └── ModuloRiesgosPTR.jsx     Iframe del módulo SUIIN-SGSI-RIESGOS (/riesgos/)
├── api/
│   ├── client.js           Fábrica de cliente HTTP con manejo de CSRF y evento de sesión vencida
│   ├── inventario.js        Cliente del Inventario (Django DRF)
│   └── rbac.js               Cliente de la Matriz RBAC (Flask, Fase 1 del README)
├── hooks/
│   ├── useSesion.js         Usuario/rol actual
│   └── useApi.js             Carga de datos genérica (estados de carga/error)
└── paginas/
    ├── inventario/
    │   ├── Dashboard.jsx        KPIs + tabla de activos
    │   ├── PanelEjecutivo.jsx    Madurez del SGSI + KPIs de RBAC consolidados
    │   ├── Alertas.jsx            Grupos de alertas por severidad
    │   ├── Riesgos.jsx            Motor de riesgos del Inventario (no confundir con PTR)
    │   ├── CentroDatos.jsx          Datacenters y diagramas
    │   ├── Bitacora.jsx             Historial de cambios
    │   ├── Activo.jsx / ActivoForm.jsx / ImportarActivos.jsx
    │   └── DatacenterForm.jsx / DiagramaForm.jsx
    └── rbac/
        ├── Inicio.jsx             Tablero de control de acceso
        ├── Roles.jsx / RolForm.jsx
        ├── Usuarios.jsx / UsuarioForm.jsx
        ├── Matriz.jsx / MatrizComparar.jsx
        ├── Sistemas.jsx / SistemaForm.jsx
        ├── Excepciones.jsx / ExcepcionMasiva.jsx
        └── Auditoria.jsx

**Tres módulos en la shell** (igual que `dashboard.html`): Inventario, Matriz
RBAC (React nativo) y Gestión de Riesgos y PTR (iframe a `/riesgos/?embed=1` —
sigue siendo la SPA propia de ese módulo).

Pendiente (Fase 4): ampliar pruebas, decidir si el login se migra a React,
y el corte final (`base: '/'`, retirar tablero Django).

## Cuidado al anidar rutas: el contexto no se propaga solo

`ModuloInventario`/`ModuloRBAC` tienen su propio `<Outlet>` para las
pantallas de su sub-navegación. El contexto que `Shell` le pasa a **su**
`<Outlet>` (`{ autenticado, puedeEditar }`) **no** llega automáticamente a
las rutas anidadas dentro de esos módulos — cada `<Outlet>` intermedio
tiene que leerlo con `useOutletContext()` y reenviarlo explícitamente al
suyo propio, o las páginas hijas verían `undefined`.

## Por qué `base: '/app/'`

Mientras dura la migración, nginx sigue sirviendo la interfaz actual
(Django + iframe de RBAC) en `/`, y este build convive aparte en `/app/`
para poder probarlo sin arriesgar lo que ya funciona. El día del corte
final (fin de la Fase 4 del README), `base` pasa a `'/'` y `nginx.conf` se
actualiza para que el build de React sea la interfaz principal.

## CSRF

Los dos backends usan mecanismos distintos, y `api/client.js` reproduce
los dos (no es un mecanismo nuevo, es la versión en React de lo que cada
backend ya exigía):

- **Inventario**: cookie `csrftoken` (Django), reenviada como encabezado
  `X-CSRFToken`.
- **RBAC**: token de sesión servido por `GET /rbac/api/csrf`, reenviado
  como encabezado `X-CSRF-Token`.

## react-router-dom

Se usa **exclusivamente en modo declarativo** (`<BrowserRouter>`,
`<Routes>`, `<Route>`) — nunca "Framework Mode" ni acciones de servidor.
Esto importa porque la versión instalada (7.18.1, la más reciente
disponible) tiene un aviso de seguridad conocido
(GHSA-qwww-vcr4-c8h2, CSRF en "RSC Mode") que, según el propio aviso, **no
afecta** al modo declarativo — ver `vite.config.js` para el detalle.

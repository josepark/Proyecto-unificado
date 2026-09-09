# Manual técnico — Plataforma SUIIN-SGSI

**Versión:** 1.0 · **Fecha:** septiembre 2026  
**Ámbito:** arquitectura, despliegue, integración, APIs y operaciones  
**Audiencia:** administradores de sistemas, desarrolladores y responsables del SGSI

Para el uso de la interfaz web, consulte [MANUAL-USUARIO.md](MANUAL-USUARIO.md).

---

## Tabla de contenidos

1. [Arquitectura](#1-arquitectura)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Despliegue](#3-despliegue)
4. [Configuración](#4-configuración)
5. [Autenticación y autorización](#5-autenticación-y-autorización)
6. [Integración entre módulos](#6-integración-entre-módulos)
7. [APIs REST](#7-apis-rest)
8. [Bases de datos](#8-bases-de-datos)
9. [Operaciones y mantenimiento](#9-operaciones-y-mantenimiento)
10. [Desarrollo local](#10-desarrollo-local)
11. [Pruebas](#11-pruebas)
12. [Seguridad](#12-seguridad)
13. [Resolución de incidencias](#13-resolución-de-incidencias)

---

## 1. Arquitectura

### 1.1 Visión general

La plataforma unifica tres aplicaciones independientes bajo un **gateway nginx** y una **SPA React** común. Cada módulo conserva su stack, ORM y base de datos; la integración se hace por HTTP servidor-a-servidor y sesión compartida.

```
┌─────────────┐
│  Navegador  │
└──────┬──────┘
       │ HTTP :80
       ▼
┌──────────────────────────────────────────────────────────┐
│  nginx (gateway + build SPA)                              │
│  ├── /, /inventario/*, /rbac/*, /gestion-riesgos/* → SPA│
│  ├── /api/*              → inventario:8000                │
│  ├── /admin/, /login/    → inventario:8000              │
│  ├── /rbac/api/*         → rbac:5000 (+ auth_request)     │
│  ├── /riesgos/api/*      → riesgos-backend:8000         │
│  └── /static/, /media/   → archivos estáticos           │
└──────────────────────────────────────────────────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  Inventario │    │    RBAC     │    │ Riesgos-backend │
│  Django DRF │    │ Flask JSON  │    │   Django DRF    │
│  SQLite/PG  │    │   SQLite    │    │    SQLite/PG    │
└─────────────┘    └─────────────┘    └─────────────────┘
```

### 1.2 Servicios Docker

| Servicio | Contexto | Puerto interno | Healthcheck |
|----------|----------|----------------|-------------|
| `inventario` | `./inventario` | 8000 | `GET /api/sesion/` |
| `riesgos-backend` | `./riesgos/backend` | 8000 | `GET /api/dashboard/resumen/` |
| `rbac` | `./rbac` | 5000 | `GET /api/csrf` |
| `nginx` | `nginx/Dockerfile` | 80 (host) | `GET /healthz` |

**Dependencias de arranque:** `riesgos-backend` espera `inventario` healthy; `nginx` espera los tres backends.

**Volúmenes persistentes:**

| Ruta en contenedor | Contenido |
|--------------------|-----------|
| `inventario/db.sqlite3` | Base Inventario |
| `inventario/media/` | Adjuntos Inventario |
| `riesgos/backend/db.sqlite3` | Base Riesgos |
| `riesgos/backend/media/` | Evidencias PTR |
| `rbac/rbac.db` | Base RBAC |
| `static_data` | collectstatic Django |

### 1.3 Build del frontend

`nginx/Dockerfile` usa build multi-etapa:

1. Compila `frontend/` (React + Vite)
2. Incorpora fuentes de `riesgos/frontend` vía alias `@riesgos`
3. Sirve el bundle en `/` con fallback a `index.html`

---

## 2. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend unificado | React 18, Vite, react-router-dom 7, Vitest |
| Inventario | Django 5, Django REST Framework, django-simple-history, django-axes |
| RBAC | Flask, SQLite WAL, gunicorn |
| Riesgos | Django 5, DRF, React embebido (`@riesgos`) |
| Gateway | nginx (auth_request, rate limit, TLS termination opcional) |
| Contenedores | Docker Compose v2 |

**Documentos normativos:**

- SUIIN-SGSI-INV-001 — Inventario
- SUIIN-SGSI-MCA-001 v2.0 — Matriz RBAC
- SUIIN-SGSI-RIESGOS — Gestión de riesgos y PTR

---

## 3. Despliegue

### 3.1 Requisitos

- Docker y Docker Compose v2
- Python 3.11+ (scripts auxiliares en el host)
- 2 GB RAM mínimo recomendado
- Puertos: 80 (HTTP), opcional 443 (TLS en proxy externo)

### 3.2 Instalación inicial

```bash
cd plataforma
cp .env.example .env
python3 generar_secretos.py          # genera secretos faltantes
./desplegar.sh --purgar --sincronizar  # rebuild limpio + sync activos
```

### 3.3 Script `desplegar.sh`

Ejecuta en orden:

1. Valida `.env` y secretos no placeholder
2. `docker compose build` (multi-etapa nginx)
3. `docker compose up -d`
4. Espera healthchecks de los cuatro servicios
5. Con `--sincronizar`: ejecuta `sincronizar_activos_inventario` y `sincronizar_catalogos_mitre.sh`
6. Con `--purgar`: elimina volúmenes antes del rebuild

### 3.4 Verificación post-despliegue

```bash
curl -sf http://localhost/healthz          # nginx
curl -sf http://localhost/api/sesion/      # inventario
curl -sf http://localhost/rbac/api/csrf    # rbac (requiere sesión para mutaciones)
curl -sf http://localhost/riesgos/api/dashboard/resumen/  # riesgos
```

### 3.5 TLS y producción

- Termine TLS en nginx o en un balanceador delante del stack
- Configure `DJANGO_CSRF_TRUSTED` con el origen HTTPS
- Ajuste `DJANGO_SSL_REDIRECT` según dónde termine TLS (ver comentarios en `.env.example`)
- Cambie contraseñas de usuarios de ejemplo
- Migre a PostgreSQL para producción (ver §8.2)

Documentación ampliada: [README-DESPLIEGUE.md](../README-DESPLIEGUE.md).

---

## 4. Configuración

### 4.1 Variables de entorno (`.env`)

| Variable | Módulo | Descripción |
|----------|--------|-------------|
| `DJANGO_SECRET_KEY` | Inventario | Sesión Django; **única por app** |
| `RIESGOS_SECRET_KEY` | Riesgos | Sesión Django Riesgos; distinta de la anterior |
| `SUIIN_RBAC_SECRET` | RBAC | Sesión Flask |
| `JWT_SHARED_SECRET` | Inventario + Riesgos + RBAC | JWT plataforma y header `X-Plataforma-Secret` |
| `JWT_EXPIRACION_MINUTOS` | Inventario | Vigencia JWT (default 30) |
| `DJANGO_DEBUG` | Inventario | `False` en producción |
| `DJANGO_ALLOWED_HOSTS` | Inventario | Hosts permitidos (coma-separados) |
| `DJANGO_CSRF_TRUSTED` | Inventario | Orígenes CSRF para HTTPS |
| `DJANGO_SSL_REDIRECT` | Inventario | Redirección SSL Django |
| `RBAC_INTERNAL_URL` | Inventario | URL interna RBAC (default `http://rbac:5000`) |
| `RIESGOS_INTERNAL_URL` | Inventario | URL interna Riesgos |
| `INVENTARIO_API_URL` | Riesgos | URL catálogo activos (default `http://inventario:8000/api`) |
| `PLATAFORMA_ACTIVOS_SOLO_INVENTARIO` | Riesgos | Solo activos sincronizados (default `true`) |
| `DJANGO_EMAIL_*` | Inventario | SMTP para alertas semanales |
| `DJANGO_ALERTAS_EMAIL` | Inventario | Destinatarios resumen alertas |
| `RIESGOS_ALERTAS_EMAIL_DESTINATARIOS` | Riesgos | Destinatarios vencimientos PTR |

**PostgreSQL opcional (Inventario):**

```
DJANGO_DB_ENGINE=postgresql
DJANGO_DB_NAME=suiin_inventario
DJANGO_DB_USER=suiin
DJANGO_DB_PASSWORD=...
DJANGO_DB_HOST=postgres
DJANGO_DB_PORT=5432
```

### 4.2 Generación de secretos

```bash
python3 generar_secretos.py
# o manualmente:
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Las aplicaciones **rechazan arrancar** con `DJANGO_DEBUG=False` si detectan valores `defina-*` del ejemplo.

### 4.3 Archivos `.env` por módulo

Para desarrollo standalone (sin Docker):

- `inventario/.env.example`
- `riesgos/backend/.env.example`
- `riesgos/frontend/.env.example` — `VITE_API_BASE_URL`

---

## 5. Autenticación y autorización

### 5.1 Flujo de sesión

```
Usuario → POST /api/auth/login/ (Inventario)
       → Cookie de sesión Django (HttpOnly)
       → GET /api/sesion/ → { autenticado, roles, puede_editar, puede_eliminar }
       → GET /api/token-jwt/ → JWT para Riesgos (firmado con JWT_SHARED_SECRET)
       → Peticiones /rbac/api/* → nginx auth_request → GET /api/auth-rbac/
```

### 5.2 Roles (grupos Django)

Definidos en `inventario/inventario/permisos.py`:

| Rol | Inventario API | RBAC API | Riesgos API |
|-----|----------------|----------|-------------|
| Consultor | GET autenticado | GET permitido | GET autenticado |
| Dinamizador | GET + POST/PUT/PATCH | GET + mutaciones | GET + escritura JWT |
| Administrador | GET + escritura + DELETE | GET + mutaciones | GET + escritura JWT |

**Política `RolPermiso`:** lectura con cualquier usuario autenticado; escritura Dinamizador+; DELETE solo Administrador.

**Excepciones públicas (`AllowAny`):**

- `GET /api/dashboard-ejecutivo/`
- `GET /riesgos/api/dashboard/resumen/`

### 5.3 Protección RBAC (nginx auth_request)

RBAC no tiene login propio. nginx intercepta `/rbac/api/*`:

```nginx
auth_request /api/auth-rbac/;
```

`auth_check_rbac` en `inventario/inventario/views.py`:

- **GET:** Consultor, Dinamizador o Administrador → 204
- **POST/PUT/DELETE:** Dinamizador o Administrador → 204
- Sin sesión o rol insuficiente → 401 (nginx redirige a login)

Header `X-Usuario-SGSI` propagado a RBAC para bitácora con usuario real.

### 5.4 JWT compartido (Riesgos)

`riesgos/backend/riesgos/auth_jwt.py` — clase `EscrituraSegunRolDePlataforma`:

- Token emitido por Inventario (`/api/token-jwt/`)
- Verificación local con `JWT_SHARED_SECRET`
- Escritura exige rol Dinamizador o Administrador en claims JWT
- Modo legacy (token propio Riesgos): cualquier autenticado puede escribir

### 5.5 CSRF dual (frontend)

| Backend | Mecanismo | Header |
|---------|-----------|--------|
| Inventario | Cookie `csrftoken` | `X-CSRFToken` |
| RBAC | `GET /rbac/api/csrf` | `X-CSRF-Token` |

Implementado en `frontend/src/api/client.js`.

### 5.6 Servicio interno

Peticiones con header `X-Plataforma-Secret` (= `JWT_SHARED_SECRET`) permiten lectura servidor-a-servidor en endpoints marcados `RolPermisoOServicioInterno`. Las mutaciones **nunca** se autorizan solo con secreto.

---

## 6. Integración entre módulos

### 6.1 Inventario ↔ Riesgos (sync de activos)

**Fuente canónica:** Inventario (`Activo`).

**Comando:**

```bash
docker compose exec riesgos-backend python manage.py sincronizar_activos_inventario
```

**Lógica** (`inventario/inventario/integracion_riesgos.py`):

1. Correlación por `inventario_id` → `id_activo` exacto → nombre normalizado
2. Crea o actualiza espejo en Riesgos
3. Expone resumen en `GET /api/integracion/vinculacion/`

**APIs relacionadas:**

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/integracion/vinculacion/` | Resumen sync (totales, pendientes) |
| `GET /api/integracion/vinculacion.csv` | Export CSV |
| `GET /api/activos/?sin_espejo_riesgos=true` | Filtro operativo |
| `GET /api/alertas/unificadas/` | Alertas + estado sync |

**UI compartida:** `frontend/src/lib/integracionUi.js`, `PanelVinculacion.jsx`.

**Cron recomendado:** cada 6 horas (`cron/suiin-sgsi.cron.example`).

### 6.2 Inventario ↔ RBAC (cruce de sistemas)

Campo `sistema_rbac_id` / `sistema_mca_equivalente` en activos clase SIS.

- `GET /api/catalogo/sistemas-rbac/` — catálogo para picker en formularios
- Panel ejecutivo consulta RBAC vía `RBAC_INTERNAL_URL`

### 6.3 Alertas unificadas

`GET /api/alertas/unificadas/` agrega:

- Alertas Inventario (`/api/alertas/`)
- Resumen RBAC (`/rbac/api/resumen` vía interno)
- KPIs Riesgos (`RIESGOS_INTERNAL_URL`)
- Estado vinculación sync

Frontend: `ENLACES_ALERTAS_RBAC` en `frontend/src/paginas/rbac/rbacUtil.js`.

### 6.4 Reporte consolidado PDF

`GET /api/reporte-consolidado.pdf` — requiere sesión `RolPermiso`.

Implementación: `inventario/inventario/reporte_consolidado.py`.

### 6.5 Catálogo MITRE

```bash
./sincronizar_catalogos_mitre.sh
```

Propaga técnicas ATT&CK desde Inventario a Riesgos y RBAC. Cron semanal recomendado.

---

## 7. APIs REST

Prefijos públicos vía nginx:

| Módulo | Prefijo |
|--------|---------|
| Inventario | `/api/` |
| RBAC | `/rbac/api/` |
| Riesgos | `/riesgos/api/` |

### 7.1 Inventario — endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/activos/` | Listado y alta |
| GET/PATCH/DELETE | `/api/activos/{id}/` | Detalle CRUD |
| GET | `/api/activos/{id}/historial/` | Bitácora del activo |
| POST | `/api/activos/importar/analizar/` | Análisis import Excel |
| POST | `/api/activos/importar/confirmar/` | Confirmar import |
| GET | `/api/sesion/` | Estado sesión |
| GET/POST | `/api/auth/login/` | Login SPA |
| GET | `/api/auth-rbac/` | Puerta nginx (interna) |
| GET/POST | `/api/token-jwt/` | JWT plataforma |
| GET | `/api/alertas/` | Alertas Inventario |
| GET | `/api/alertas/unificadas/` | Alertas consolidadas |
| GET | `/api/dashboard-ejecutivo/` | Panel ejecutivo |
| GET | `/api/reporte-consolidado.pdf` | PDF consolidado |
| GET | `/api/integracion/vinculacion/` | Estado sync Riesgos |
| GET | `/api/bitacora/` | Bitácora global |
| GET | `/api/accesos/unificado/` | Auditoría cross-módulo (solo Admin) |
| GET | `/api/exportar/inventario.xlsx` | Export Excel |

Referencia completa: [inventario/README.md](../inventario/README.md) §6.

### 7.2 RBAC — endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/csrf` | Token CSRF |
| GET | `/resumen` | KPIs tablero |
| GET/POST | `/roles`, `/roles/{id}` | CRUD roles |
| POST | `/roles/{id}/certificar` | Certificación periódica |
| GET/POST | `/usuarios`, `/usuarios/{id}` | CRUD usuarios |
| GET | `/matriz`, `/matriz/heatmap` | Matriz y heatmap |
| PUT | `/matriz` | Edición de celda |
| GET | `/matriz/comparar` | Comparar dos roles |
| POST | `/matriz/importar/analizar`, `/confirmar` | Import CSV |
| GET/POST | `/sistemas`, `/sistemas/{id}` | CRUD sistemas |
| GET | `/excepciones` | Listado excepciones |
| POST | `/excepciones/masiva` | Excepción masiva |
| POST/DELETE | `/usuarios/{uid}/excepciones` | Alta/baja excepción |
| GET | `/auditoria` | Bitácora (parámetro `limite`) |
| GET | `/auditoria/verificar` | Verificar cadena hash |
| GET | `/export/matriz.csv` | Export matriz |

Referencia completa: [rbac/README.md](../rbac/README.md), código en `rbac/api_rest.py`.

### 7.3 Riesgos — endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/dashboard/resumen/` | KPIs (público) |
| GET | `/alertas/resumen/` | Vencimientos |
| GET/POST | `/activos/` | Activos espejo |
| GET/POST | `/vulnerabilidades/` | Hallazgos |
| POST | `/vulnerabilidades/bulk-actualizar/` | Actualización masiva |
| GET/POST | `/riesgos-activo/` | Riesgos por activo |
| GET/POST | `/riesgos-contextuales/` | Riesgos RC-01..07 |
| GET/POST | `/campanas-red-team/` | Red Team |
| GET/POST | `/planes-tratamiento/` | PTR |
| GET/POST | `/acciones-tratamiento/` | Acciones PTR |
| GET | `/cumplimiento/resumen/` | Cobertura Anexo A |
| POST | `/importar/excel/` | Import Excel |
| GET | `/{recurso}/{id}/historial/` | Auditoría por entidad |

Referencia completa: [riesgos/README.md](../riesgos/README.md) §5.

### 7.4 Clientes JavaScript

| Archivo | Backend |
|---------|---------|
| `frontend/src/api/client.js` | Fábrica HTTP + CSRF |
| `frontend/src/api/inventario.js` | Inventario DRF |
| `frontend/src/api/rbac.js` | RBAC Flask |

---

## 8. Bases de datos

### 8.1 Inventario (Django)

- **Default:** SQLite (`inventario/db.sqlite3`)
- **Producción recomendada:** PostgreSQL
- **Historial:** django-simple-history en modelos principales
- **Integridad:** cadena SHA-256 verificable (`/api/integridad/`)

Modelos clave: `Activo`, `ClaseActivo`, `Datacenter`, `Rack`, `Diagrama`, `Amenaza`, `Control`.

### 8.2 RBAC (Flask + SQLite WAL)

- Archivo: `rbac/rbac.db`
- Esquema: 10 tablas + 3 vistas (`schema.sql`)
- Bitácora encadenada por hash SHA-256
- Migración acumulativa: `python3 migrar_v2_1.py`
- Seed inicial: `python3 seed.py`

### 8.3 Riesgos (Django)

- **Default:** SQLite (`riesgos/backend/db.sqlite3`)
- Activos espejo con campo `inventario_id`
- Evidencias en `media/`

### 8.4 Respaldo unificado

```bash
python3 respaldar_plataforma.py
```

Copia SQLite + media de los tres módulos con retención configurable. Programar en cron (02:00 diario).

---

## 9. Operaciones y mantenimiento

### 9.1 Tareas cron recomendadas

Archivo de referencia: `cron/suiin-sgsi.cron.example`

| Frecuencia | Comando | Propósito |
|------------|---------|-----------|
| Diario 02:00 | `respaldar_plataforma.py` | Respaldo unificado |
| Lunes 07:00 | `enviar_resumen_alertas --solo-si-hay-criticas` | Alertas Inventario+RBAC |
| Lunes 07:30 | `enviar_alertas_vencimiento` | Vencimientos Riesgos |
| Cada 6 h | `sincronizar_activos_inventario` | Sync activos |
| Domingo 03:00 | `sincronizar_catalogos_mitre.sh` | Catálogo MITRE |

### 9.2 Comandos de gestión útiles

```bash
# Estado de servicios
docker compose ps
docker compose logs -f inventario

# Sync manual
docker compose exec riesgos-backend python manage.py sincronizar_activos_inventario

# Alertas por correo (dry-run en logs si no hay SMTP)
docker compose exec inventario python manage.py enviar_resumen_alertas

# Diagnóstico login bloqueado (django-axes)
./diagnostico_login.sh

# Rebuild completo
./desplegar.sh --purgar --sincronizar
```

### 9.3 Logs

```bash
docker compose logs inventario --tail 100
docker compose logs rbac --tail 100
docker compose logs riesgos-backend --tail 100
docker compose logs nginx --tail 100
```

### 9.4 Actualización de versión

1. Respaldo: `python3 respaldar_plataforma.py`
2. Pull del código
3. Revisar cambios en `.env.example`
4. `./desplegar.sh --sincronizar`
5. Verificar healthchecks y suite de pruebas

---

## 10. Desarrollo local

### 10.1 Frontend (Vite)

```bash
cd frontend
npm install
npm run dev    # http://127.0.0.1:5173 — proxy a :8000 y :5000
```

Proxy configurado en `vite.config.js` — mismo recorte de prefijo que nginx.

### 10.2 Inventario (Django standalone)

```bash
cd inventario
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8000
```

### 10.3 RBAC (Flask standalone)

```bash
cd rbac
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 seed.py
python3 app.py    # http://localhost:5000
```

### 10.4 Riesgos (standalone)

Ver [riesgos/README.md](../riesgos/README.md) §3 — backend Django + frontend Vite independiente.

### 10.5 Estructura frontend relevante

```
frontend/src/
├── App.jsx                    Rutas principales
├── componentes/
│   ├── Shell.jsx              Encabezado + badges
│   ├── ModuloInventario.jsx   Sub-nav Inventario
│   ├── ModuloRBAC.jsx         Sub-nav RBAC
│   ├── PuertaRBAC.jsx         Guardia de acceso RBAC
│   ├── PanelVinculacion.jsx   Sync Inventario↔Riesgos
│   └── ModuloRiesgosPTR.jsx   Montaje @riesgos
├── lib/integracionUi.js       Utilidades sync
├── paginas/inventario/        Pantallas Inventario
├── paginas/rbac/              Pantallas RBAC + rbacUtil.js
└── api/                       Clientes HTTP
```

**Nota:** el contexto de `Shell` (`puedeEditar`) debe reenviarse explícitamente por cada `<Outlet>` intermedio.

---

## 11. Pruebas

### 11.1 Frontend (Vitest)

```bash
cd frontend
npm test              # 57 pruebas
npm run test:watch    # modo interactivo
```

Patrones de referencia: `Riesgos.test.jsx`, `ActivoForm.test.jsx`, `Activo.test.jsx`.

### 11.2 Inventario (Django)

```bash
cd inventario
python manage.py test
```

Incluye tests de integración Inventario↔Riesgos (Olas 5–8).

### 11.3 RBAC (pytest)

```bash
cd rbac
DJANGO_DEBUG=True python3 -m pytest -q    # ~40 pruebas
```

Incluye `test_auditoria_respeta_limite`.

### 11.4 Riesgos (Django)

```bash
cd riesgos/backend
python manage.py test
```

---

## 12. Seguridad

### 12.1 Checklist de producción

- [ ] Secretos generados (`generar_secretos.py`); ningún `defina-*`
- [ ] `DJANGO_DEBUG=False`
- [ ] Contraseñas de usuarios de ejemplo cambiadas
- [ ] `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED` configurados
- [ ] TLS activo (nginx o proxy externo)
- [ ] RBAC protegido por `auth_request` (no exponer `:5000` directamente)
- [ ] Respaldos programados
- [ ] Cron de sync y alertas activo
- [ ] PostgreSQL en producción (recomendado)

### 12.2 Rate limiting

nginx limita intentos de login (`/api/auth/login/`) para mitigar fuerza bruta. Bloqueos adicionales vía django-axes en Inventario.

### 12.3 Content-Security-Policy (RBAC)

RBAC aplica CSP estricta (`script-src 'self'`). JavaScript centralizado en `static/app.js` (modo legacy Flask); la SPA React consume la API JSON.

### 12.4 Inyección CSV

Exportaciones RBAC escapan celdas que empiezan con `=`, `+`, `-`, `@` para prevenir formula injection en Excel.

### 12.5 Auditoría

| Módulo | Mecanismo |
|--------|-----------|
| Inventario | django-simple-history + cadena SHA-256 |
| RBAC | Bitácora encadenada + `X-Usuario-SGSI` |
| Riesgos | Historial por entidad |
| Cross-módulo | `/api/accesos/unificado/` (solo Administrador) |

---

## 13. Resolución de incidencias

### 13.1 Login falla o cuenta bloqueada

```bash
./diagnostico_login.sh
docker compose exec inventario python manage.py axes_reset
```

Verificar `DJANGO_ALLOWED_HOSTS`, cookies (SameSite) y CSRF trusted origins.

### 13.2 RBAC devuelve 401 en mutaciones

- Confirmar sesión activa con rol Dinamizador o Administrador
- Revisar logs nginx: `auth_request` contra `/api/auth-rbac/`
- Consultor solo puede GET

### 13.3 Riesgos no sincroniza activos

```bash
docker compose exec riesgos-backend python manage.py sincronizar_activos_inventario -v 2
curl -s http://localhost/api/integracion/vinculacion/ | python3 -m json.tool
```

Verificar `INVENTARIO_API_URL` y conectividad entre contenedores.

### 13.4 Frontend muestra pantalla en blanco

- Revisar consola del navegador (errores JS)
- Confirmar que nginx sirve el build: `curl -I http://localhost/`
- Rebuild: `./desplegar.sh --purgar`

### 13.5 JWT expirado en Riesgos

El frontend renueva JWT vía `/api/token-jwt/` al detectar 401. Si persiste:

- Verificar `JWT_SHARED_SECRET` idéntico en Inventario y Riesgos
- Ajustar `JWT_EXPIRACION_MINUTOS`

### 13.6 Contenedor unhealthy

```bash
docker compose ps
docker compose logs <servicio> --tail 50
```

Healthchecks: inventario `/api/sesion/`, riesgos `/api/dashboard/resumen/`, rbac `/api/csrf`.

---

## Documentos relacionados

| Documento | Contenido |
|-----------|-----------|
| [README.md](../README.md) | Visión general e inicio rápido |
| [MANUAL-USUARIO.md](MANUAL-USUARIO.md) | Guía de uso de la interfaz |
| [README-DESPLIEGUE.md](../README-DESPLIEGUE.md) | Despliegue detallado e historial |
| [frontend/README.md](../frontend/README.md) | Desarrollo frontend |
| [inventario/README.md](../inventario/README.md) | API Inventario |
| [rbac/README.md](../rbac/README.md) | API RBAC y esquema |
| [riesgos/README.md](../riesgos/README.md) | API Riesgos y PTR |

---

## Apéndice A — Mapa de rutas SPA

| Ruta | Componente |
|------|------------|
| `/login` | Login |
| `/inventario/dashboard` | Dashboard |
| `/inventario/activos/nuevo` | ActivoForm |
| `/inventario/activos/:id` | Activo |
| `/inventario/panel-ejecutivo` | PanelEjecutivo |
| `/inventario/alertas` | Alertas |
| `/inventario/riesgos` | Riesgos (inherente) |
| `/inventario/centro-datos` | CentroDatos |
| `/inventario/bitacora` | Bitacora |
| `/inventario/clases` | ClasesActivos |
| `/rbac/inicio` | Inicio RBAC |
| `/rbac/matriz` | Matriz |
| `/rbac/excepciones` | Excepciones |
| `/rbac/auditoria` | Auditoria |
| `/gestion-riesgos/*` | ModuloRiesgosPTR |

Definición canónica: `frontend/src/App.jsx`.

---

## Apéndice B — Scripts operativos

| Script | Ubicación | Función |
|--------|-----------|---------|
| `desplegar.sh` | raíz | Despliegue completo |
| `generar_secretos.py` | raíz | Genera secretos `.env` |
| `respaldar_plataforma.py` | raíz | Respaldo unificado |
| `diagnostico_login.sh` | raíz | Diagnóstico axes/login |
| `sincronizar_catalogos_mitre.sh` | raíz | Sync MITRE |
| `migrar_v2_1.py` | rbac/ | Migración RBAC |
| `respaldar.py` | rbac/ | Respaldo RBAC standalone |

— Camino del SUIIN · CRIC

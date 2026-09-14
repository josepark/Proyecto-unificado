# Plataforma SUIIN-SGSI

Interfaz unificada para el Sistema de Gestión de Seguridad de la Información (SGSI) del SUIIN/CRIC. Una sola aplicación web (React) integra tres módulos que conservan su stack y base de datos propios, coordinados por nginx y llamadas servidor-a-servidor.

| Módulo | Documento | Stack | Interfaz | API |
|--------|-----------|-------|----------|-----|
| **Inventario de activos** | SUIIN-SGSI-INV-001 | Django + DRF | `/inventario/…` | `/api/` |
| **Matriz RBAC** | SUIIN-SGSI-MCA-001 | Flask (JSON) | `/rbac/…` | `/rbac/api/` |
| **Gestión de Riesgos y PTR** | SUIIN-SGSI-RIESGOS | Django + DRF | `/gestion-riesgos/…` | `/riesgos/api/` |

## Arquitectura

```
Navegador → nginx (puerto 80)
              ├── /  ………………… SPA React (frontend/)
              ├── /api/ ………… Inventario (Django)
              ├── /rbac/api/ … RBAC (Flask) + auth_request → Inventario
              └── /riesgos/api/ … Riesgos (Django) + JWT compartido
```

- **Sesión web:** login único en `/login` (cookie Django). RBAC valida cada petición vía `auth_request` contra `/api/auth-rbac/`.
- **Riesgos:** JWT firmado con `JWT_SHARED_SECRET` (`GET /api/token-jwt/`).
- **Integración:** Inventario consulta RBAC y Riesgos en la red interna Docker (`RBAC_INTERNAL_URL`, `RIESGOS_INTERNAL_URL`) sin pasar por el navegador.

## Inicio rápido

```bash
cd plataforma
cp .env.example .env
python3 generar_secretos.py    # reemplace placeholders de .env.example
./desplegar.sh --purgar --sincronizar
```

| Recurso | URL |
|---------|-----|
| Aplicación | `http://localhost/` |
| Login | `http://localhost/login` |
| Admin Django (Inventario) | `http://localhost/admin/` |

**Usuarios de ejemplo** (cámbielos antes de exponer en red):

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `SUIIN2026#` | Administrador |
| `dinamizador` | `Dinamizador2026#` | Dinamizador |
| `consultor` | `Consultor2026#` | Consultor (solo lectura en Inventario y RBAC) |

Documentación operativa detallada: [README-DESPLIEGUE.md](README-DESPLIEGUE.md).

## Módulos y rutas principales

### Inventario (`/inventario/`)

- **Dashboard** — KPIs, listado de activos, exportación Excel, etiquetas en lote.
- **Panel ejecutivo** — madurez SGSI, KPIs consolidados (Inventario + RBAC + Riesgos).
- **Centro de alertas** — señales unificadas de Inventario, RBAC, Riesgos y sincronización Inventario ↔ Riesgos.
- **Valoración inherente** — motor de riesgo del Inventario (distinto del módulo PTR).
- **Centro de datos**, **Clases de activo**, **Bitácora** (cadena SHA-256 verificable).

Clases de activo: Infraestructura (`RED-`), Sistemas (`SIS-`), Equipos de cómputo (`PC-`).

### Matriz RBAC (`/rbac/`)

- **Inicio** — MFA, vencimientos, roles críticos.
- **Roles / Usuarios / Sistemas** — catálogos MCA-001 con certificación periódica.
- **Matriz** — edición por celda, mapa de calor, comparar roles, import/export CSV.
- **Excepciones** — individual y masiva (control 5.18), con motivo obligatorio.
- **Auditoría** — bitácora encadenada + verificación de integridad.

**Permisos:**

| Rol | Inventario | RBAC |
|-----|------------|------|
| Dinamizador / Administrador | Lectura y escritura | Lectura y escritura |
| Consultor | Solo lectura | Solo lectura (fichas en modo consulta) |

Badge de pendientes en la pestaña **Matriz RBAC** cuando hay MFA incumplido, certificaciones vencidas, excepciones vencidas o vencimientos próximos.

### Gestión de Riesgos (`/gestion-riesgos/`)

Matriz de riesgos, vulnerabilidades, plan de tratamiento (PTR), Red Team. Los activos se sincronizan desde el Inventario (`sincronizar_activos_inventario`).

## Integración entre módulos

| Funcionalidad | Descripción |
|---------------|-------------|
| **Alertas unificadas** | `GET /api/alertas/unificadas/` — Inventario + RBAC + Riesgos + sync |
| **Sync Inventario ↔ Riesgos** | Activos espejo, panel de vinculación, filtro `sin_espejo_riesgos`, CSV |
| **Cruce Inventario ↔ RBAC** | `sistema_rbac_id` / `sistema_mca_equivalente` en sistemas de información |
| **Reporte consolidado** | `GET /api/reporte-consolidado.pdf` |
| **Resumen semanal** | `python manage.py enviar_resumen_alertas` |

Sincronización periódica recomendada (ver `cron/suiin-sgsi.cron.example`):

```bash
docker compose exec riesgos-backend python manage.py sincronizar_activos_inventario
./sincronizar_catalogos_mitre.sh
```

## Desarrollo

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173 — proxy a Django :8000 y RBAC :5000
npm test             # 57 pruebas Vitest
```

Ver [frontend/README.md](frontend/README.md).

### Backend

```bash
# Inventario
cd inventario && python3 manage.py test

# RBAC
cd rbac && DJANGO_DEBUG=True python3 -m pytest

# Riesgos
cd riesgos/backend && python3 manage.py test
```

### Variables de entorno clave (`.env`)

| Variable | Uso |
|----------|-----|
| `DJANGO_SECRET_KEY` | Sesión Inventario |
| `RIESGOS_SECRET_KEY` | Sesión Riesgos (distinta a Django) |
| `SUIIN_RBAC_SECRET` | Sesión Flask RBAC |
| `JWT_SHARED_SECRET` | JWT plataforma + endpoints internos |
| `DJANGO_ALLOWED_HOSTS` | Hosts públicos permitidos |
| `RBAC_INTERNAL_URL` | Llamadas Inventario → RBAC (default `http://rbac:5000`) |

## Scripts útiles

| Script | Propósito |
|--------|-----------|
| `./desplegar.sh` | Despliegue completo con healthchecks |
| `./desplegar.sh --purgar --sincronizar` | Rebuild limpio + sync activos |
| `./sincronizar_catalogos_mitre.sh` | MITRE ATT&CK Inventario → RBAC |
| `python3 respaldar_plataforma.py` | Respaldo unificado SQLite + media |
| `python3 generar_secretos.py` | Genera secretos faltantes en `.env` |
| `./diagnostico_login.sh` | Diagnóstico de bloqueos de login |

## Estructura del repositorio

```
plataforma/
├── frontend/           SPA React (interfaz principal)
├── inventario/         Django — activos, alertas, integraciones
├── rbac/               Flask — matriz MCA-001 (solo API JSON)
├── riesgos/            Django + fuentes React (@riesgos en build unificado)
├── nginx/              Gateway + build multi-etapa del frontend
├── docker-compose.yml
├── desplegar.sh
├── README-DESPLIEGUE.md   Guía operativa y historial de integración
└── cron/suiin-sgsi.cron.example
```

## Documentación adicional

- [docs/MANUAL-USUARIO.md](docs/MANUAL-USUARIO.md) — guía de uso de la interfaz web
- [docs/MANUAL-TECNICO.md](docs/MANUAL-TECNICO.md) — arquitectura, despliegue, APIs y operaciones
- [README-DESPLIEGUE.md](README-DESPLIEGUE.md) — despliegue, seguridad, TLS, integraciones históricas
- [inventario/README.md](inventario/README.md) — API Inventario
- [rbac/README.md](rbac/README.md) — API RBAC y esquema MCA
- [riesgos/README.md](riesgos/README.md) — módulo de riesgos y PTR

## Licencia y contexto

Proyecto institucional SUIIN/CRIC — ISO/IEC 27001:2022. Uso interno del SGSI.

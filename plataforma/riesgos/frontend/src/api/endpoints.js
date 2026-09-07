import axios from "axios";
import api, { inventarioBaseURL } from "./client";

function leerCookie(nombre) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export const endpoints = {
  // Auth
  login: (username, password) => api.post("/auth/login/", { username, password }),
  logout: () => api.post("/auth/logout/"),
  me: () => api.get("/auth/me/"),

  // Sesión única de plataforma: le pide un JWT al Inventario usando la
  // cookie de sesión que ya tenga (si hay una) — no pasa por el cliente
  // `api` de arriba porque este request va al Inventario, no a riesgos, y
  // porque necesita enviar cookies entre orígenes/rutas (withCredentials).
  ssoJWT: () => axios.get(`${inventarioBaseURL}/token-jwt/`, { withCredentials: true }),

  // Mismo endpoint del Inventario, pero con usuario/clave en vez de cookie —
  // para el formulario de login manual (ver AuthContext.jsx: se intenta
  // primero, y solo si falla se cae al login propio de riesgos más abajo).
  ssoJWTLogin: async (username, password) => {
    // Asegura cookie csrftoken (mismo patrón que /api/auth/login/ de la SPA).
    await axios.get(`${inventarioBaseURL}/sesion/`, { withCredentials: true });
    return axios.post(
      `${inventarioBaseURL}/token-jwt/`,
      { username, password },
      {
        withCredentials: true,
        headers: { "X-CSRFToken": leerCookie("csrftoken") || "" },
      },
    );
  },

  dashboard: () => api.get("/dashboard/resumen/"),

  // Activos
  activos: (params) => api.get("/activos/", { params }),
  activo: (id) => api.get(`/activos/${id}/`),
  crearActivo: (data) => api.post("/activos/", data),
  actualizarActivo: (id, data) => api.patch(`/activos/${id}/`, data),
  eliminarActivo: (id) => api.delete(`/activos/${id}/`),

  // Vulnerabilidades
  vulnerabilidades: (params) => api.get("/vulnerabilidades/", { params }),
  crearVulnerabilidad: (data) => api.post("/vulnerabilidades/", data),
  actualizarVulnerabilidad: (id, data) => api.patch(`/vulnerabilidades/${id}/`, data),
  eliminarVulnerabilidad: (id) => api.delete(`/vulnerabilidades/${id}/`),
  bulkActualizarVulnerabilidades: (ids, campos) => api.post("/vulnerabilidades/bulk-actualizar/", { ids, campos }),

  // Riesgos por activo
  riesgosActivo: (params) => api.get("/riesgos-activo/", { params }),
  crearRiesgoActivo: (data) => api.post("/riesgos-activo/", data),
  actualizarRiesgoActivo: (id, data) => api.patch(`/riesgos-activo/${id}/`, data),
  eliminarRiesgoActivo: (id) => api.delete(`/riesgos-activo/${id}/`),

  // Riesgos contextuales
  riesgosContextuales: (params) => api.get("/riesgos-contextuales/", { params }),
  crearRiesgoContextual: (data) => api.post("/riesgos-contextuales/", data),
  actualizarRiesgoContextual: (id, data) => api.patch(`/riesgos-contextuales/${id}/`, data),
  eliminarRiesgoContextual: (id) => api.delete(`/riesgos-contextuales/${id}/`),

  // Campañas Red Team
  campanasRedTeam: (params) => api.get("/campanas-red-team/", { params }),
  crearCampanaRedTeam: (data) => api.post("/campanas-red-team/", data),
  actualizarCampanaRedTeam: (id, data) => api.patch(`/campanas-red-team/${id}/`, data),

  // Plan de tratamiento
  planesTratamiento: (params) => api.get("/planes-tratamiento/", { params }),
  planTratamiento: (id) => api.get(`/planes-tratamiento/${id}/`),
  crearPlanTratamiento: (data) => api.post("/planes-tratamiento/", data),
  actualizarPlanTratamiento: (id, data) => api.patch(`/planes-tratamiento/${id}/`, data),

  // Acciones de tratamiento (items del PTR)
  crearAccion: (data) => api.post("/acciones-tratamiento/", data),
  actualizarAccion: (id, data) => api.patch(`/acciones-tratamiento/${id}/`, data),
  eliminarAccion: (id) => api.delete(`/acciones-tratamiento/${id}/`),

  // Historial (auditoría) — recurso ∈ activos | vulnerabilidades | riesgos-activo |
  // riesgos-contextuales | campanas-red-team | planes-tratamiento | acciones-tratamiento
  historial: (recurso, id) => api.get(`/${recurso}/${id}/historial/`),

  // Cumplimiento ISO 27001 (Anexo A)
  cumplimientoResumen: () => api.get("/cumplimiento/resumen/"),
  controlesIso: (params) => api.get("/controles-iso27001/", { params }),
  actualizarControlIso: (id, data) => api.patch(`/controles-iso27001/${id}/`, data),

  // Alertas de vencimiento
  alertasResumen: () => api.get("/alertas/resumen/"),

  // Evidencia (adjuntos genéricos)
  evidencias: (modelo, objectId) => api.get("/evidencias/", { params: { modelo, object_id: objectId } }),
  subirEvidencia: (formData) => api.post("/evidencias/", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  eliminarEvidencia: (id) => api.delete(`/evidencias/${id}/`),

  // Catálogo de valores parametrizable
  catalogo: (categoria) => api.get("/catalogo/", { params: { categoria, page_size: 200 } }),
  catalogoTodos: (categoria) => api.get("/catalogo/", { params: { categoria, activo: "false", page_size: 200 } }),
  catalogoObtenerOCrear: (categoria, valor) => api.post("/catalogo/obtener-o-crear/", { categoria, valor }),
  catalogoActualizar: (id, data) => api.patch(`/catalogo/${id}/`, data),
  catalogoEliminar: (id) => api.delete(`/catalogo/${id}/`),

  // Catálogo MITRE ATT&CK (espejo sincronizado desde el Inventario)
  tecnicasMitre: (busqueda) => api.get("/tecnicas-mitre/", { params: { search: busqueda, page_size: 15 } }),
};

export default endpoints;

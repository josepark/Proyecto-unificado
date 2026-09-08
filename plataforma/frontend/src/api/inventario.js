import { crearCliente } from './client';

const api = crearCliente({
  base: '/api',
  csrf: { tipo: 'cookie', cookie: 'csrftoken', header: 'X-CSRFToken' },
});

export const inventarioApi = {
  // --- Activos ---
  listarActivos: (params) => api.get('/activos/', params),
  obtenerActivo: (id) => api.get(`/activos/${id}/`),
  historialActivo: (id) => api.get(`/activos/${id}/historial/`),
  crearActivo: (datos) => api.post('/activos/', datos),
  editarActivo: (id, datos) => api.patch(`/activos/${id}/`, datos),
  importarAnalizar: (formData) => api.postForm('/activos/importar/analizar/', formData),
  importarConfirmar: (filas) => api.post('/activos/importar/confirmar/', { filas }),
  eliminarActivo: (id) => api.delete(`/activos/${id}/`),
  estadisticas: () => api.get('/activos/estadisticas/'),
  metaInventario: () => api.get('/activos/meta/'),

  listarClasesActivo: () => api.get('/clases-activo/?page_size=100'),
  crearClaseActivo: (datos) => api.post('/clases-activo/', datos),
  editarClaseActivo: (id, datos) => api.patch(`/clases-activo/${id}/`, datos),
  eliminarClaseActivo: (id) => api.delete(`/clases-activo/${id}/`),

  obtenerDatacenter: (id) => api.get(`/datacenters/${id}/`),
  eliminarDatacenter: (id, confirmar = false) =>
    api.delete(confirmar ? `/datacenters/${id}/?confirmar=1` : `/datacenters/${id}/`),

  // --- Hoja de vida ---
  listarHojaVida: (activoId) => api.get('/hojavida/', { activo: activoId }),
  crearEventoHojaVida: (datos) => api.post('/hojavida/', datos),
  crearEventoHojaVidaArchivo: (formData) => api.postForm('/hojavida/', formData),
  eliminarEventoHojaVida: (id) => api.delete(`/hojavida/${id}/`),

  /** Enlaces directos a descargas binarias (sin JSON). */
  exportarInventarioXlsx: () => '/api/exportar/inventario.xlsx',
  etiquetasLotePdf: (ids) => `/api/etiquetas/lote.pdf?ids=${ids.join(',')}`,

  // --- Paneles ---
  panelEjecutivo: () => api.get('/dashboard-ejecutivo/'),
  alertas: () => api.get('/alertas/'),
  bitacora: (params) => api.get('/bitacora/', params),
  accesos: () => api.get('/accesos/'),
  verificarIntegridad: () => api.get('/integridad/verificar/'),

  // --- Riesgos ---
  riesgos: () => api.get('/riesgos/'),
  recalcularRiesgos: () => api.post('/riesgos/recalcular/'),
  cobertura: () => api.get('/cobertura/'),

  // --- Catálogos ---
  amenazas: (params) => api.get('/amenazas/', { page_size: 2000, ...params }),
  controles: (params) => api.get('/controles/', { page_size: 200, ...params }),
  datacenters: () => api.get('/datacenters/?page_size=100'),
  crearDatacenter: (datos) => api.post('/datacenters/', datos),
  editarDatacenter: (id, datos) => api.patch(`/datacenters/${id}/`, datos),
  activosDatacenter: (id) => api.get(`/datacenters/${id}/activos/`),
  diagramas: (params) => api.get('/diagramas/', { page_size: 200, ...params }),
  obtenerDiagrama: (id) => api.get(`/diagramas/${id}/`),
  subirDiagrama: (formData) => api.postForm('/diagramas/', formData),
  editarDiagrama: (id, formData) => api.patchForm(`/diagramas/${id}/`, formData),
  eliminarDiagrama: (id) => api.delete(`/diagramas/${id}/`),
  sugerirActivosDiagrama: (formData) => api.postForm('/diagramas/sugerir_activos/', formData),

  // --- Sesión ---
  sesion: () => api.get('/sesion/'),

  /** Login JSON — no usa peticion() para no disparar 'sesion-vencida' en 401. */
  login: async (username, password) => {
    await fetch('/api/auth/login/', { credentials: 'same-origin' });
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    const csrf = match ? decodeURIComponent(match[1]) : '';
    const respuesta = await fetch('/api/auth/login/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ username, password }),
    });
    let cuerpo = null;
    try {
      cuerpo = await respuesta.json();
    } catch {
      cuerpo = null;
    }
    if (!respuesta.ok) {
      const error = new Error(cuerpo?.detail || respuesta.statusText);
      error.status = respuesta.status;
      error.data = cuerpo;
      throw error;
    }
    return cuerpo;
  },
};

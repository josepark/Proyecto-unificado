import { crearCliente } from './client';

// Bajo /rbac/ en producción (a través del gateway) y en el proxy de
// desarrollo (ver vite.config.js) — Flask ve estas mismas rutas sin el
// prefijo en los dos casos.
const api = crearCliente({
  base: '/rbac/api',
  csrf: { tipo: 'token', endpoint: '/csrf', campo: 'csrf_token', header: 'X-CSRF-Token' },
});

export const rbacApi = {
  catalogos: () => api.get('/catalogos'),
  inicio: () => api.get('/inicio'),

  // --- Roles ---
  listarRoles: (params) => api.get('/roles', params),
  obtenerRol: (id) => api.get(`/roles/${id}`),
  crearRol: (datos) => api.post('/roles', datos),
  editarRol: (id, datos) => api.put(`/roles/${id}`, datos),
  toggleActivoRol: (id) => api.delete(`/roles/${id}/activo`),
  certificarRol: (id, nota) => api.post(`/roles/${id}/certificar`, { nota }),
  eliminarRol: (id) => api.delete(`/roles/${id}`),

  // --- Sistemas ---
  listarSistemas: (params) => api.get('/sistemas', params),
  obtenerSistema: (id) => api.get(`/sistemas/${id}`),
  crearSistema: (datos) => api.post('/sistemas', datos),
  editarSistema: (id, datos) => api.put(`/sistemas/${id}`, datos),
  toggleActivoSistema: (id) => api.delete(`/sistemas/${id}/activo`),
  eliminarSistema: (id) => api.delete(`/sistemas/${id}`),

  // --- Usuarios ---
  listarUsuarios: (params) => api.get('/usuarios', params),
  obtenerUsuario: (id) => api.get(`/usuarios/${id}`),
  crearUsuario: (datos) => api.post('/usuarios', datos),
  editarUsuario: (id, datos) => api.put(`/usuarios/${id}`, datos),
  cambiarEstadoUsuario: (id, estado, motivo) => api.put(`/usuarios/${id}/estado`, { estado, motivo }),
  eliminarUsuario: (id) => api.delete(`/usuarios/${id}`),

  // --- Matriz ---
  matriz: (params) => api.get('/matriz', params),
  heatmapMatriz: () => api.get('/matriz/heatmap'),
  compararRoles: (rolA, rolB) => api.get('/matriz/comparar', { rol_a: rolA, rol_b: rolB }),
  editarCeldaMatriz: (rol_id, sistema_id, nivel) => api.put('/matriz', { rol_id, sistema_id, nivel }),
  importarMatrizAnalizar: (formData) => api.postForm('/matriz/importar/analizar', formData),
  importarMatrizConfirmar: (cambios) => api.post('/matriz/importar/confirmar', { cambios }),

  // --- Excepciones ---
  listarExcepciones: (params) => api.get('/excepciones', params),
  crearExcepcion: (usuarioId, datos) => api.post(`/usuarios/${usuarioId}/excepciones`, datos),
  eliminarExcepcion: (usuarioId, sistemaId) => api.delete(`/usuarios/${usuarioId}/excepciones/${sistemaId}`),
  excepcionesMasiva: (datos) => api.post('/excepciones/masiva', datos),

  // --- Auditoría ---
  auditoria: (params) => api.get('/auditoria', params),
  verificarCadena: () => api.get('/auditoria/verificar'),

  // --- Resumen (ya existía desde la integración inicial) ---
  resumen: () => api.get('/resumen'),
};

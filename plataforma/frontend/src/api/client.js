/**
 * Cliente base compartido por api/inventario.js y api/rbac.js.
 *
 * Los dos backends resuelven CSRF de forma distinta, y este módulo
 * reproduce EXACTAMENTE lo que cada uno ya esperaba de su propio
 * front-end anterior — no es un mecanismo nuevo, solo su versión en
 * React:
 *   - Inventario (Django): cookie `csrftoken` (no HttpOnly, legible por
 *     JS) reenviada como encabezado `X-CSRFToken`.
 *   - Matriz RBAC (Flask): token de sesión servido por `GET /rbac/api/csrf`,
 *     reenviado como encabezado `X-CSRF-Token`. Ver rbac/auth.py.
 */

function leerCookie(nombre) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** Convierte un error de peticion() en un mensaje legible para mostrar en
 * un formulario: si el backend devolvio errores por campo ({campo:
 * [mensajes]}), los lista; si no, usa el mensaje general. Compartido por
 * todos los formularios de escritura (activo, rol, usuario...). */
export function formatearErrorApi(error) {
  const datos = error?.data;
  if (datos && typeof datos === 'object' && !Array.isArray(datos)) {
    const partes = Object.entries(datos)
      .filter(([campo]) => campo !== 'detail')
      .map(([campo, mensajes]) => `${campo}: ${[].concat(mensajes).join(' ')}`);
    if (partes.length) return partes.join(' · ');
  }
  return error?.message || 'Ocurrió un error inesperado.';
}

/** Cualquier página puede escuchar 'sesion-vencida' (Shell.jsx lo hace)
 * para mostrar un aviso único en toda la app. Los 401 de /rbac/api/ vienen
 * de la puerta nginx (auth_request) y pueden significar falta de rol RBAC
 * aunque la sesión del Inventario siga activa — por eso, antes de avisar,
 * se re-consulta GET /api/sesion/ y se emite 'sesion-actualizada' para que
 * el encabezado y PuertaRBAC se sincronicen con el servidor. */
export const eventosApi = new EventTarget();

export async function consultarSesionInventario() {
  try {
    const respuesta = await fetch('/api/sesion/', { credentials: 'same-origin' });
    if (!respuesta.ok) return { autenticado: false };
    return respuesta.json();
  } catch {
    return { autenticado: false };
  }
}

async function notificar401(url) {
  // RBAC solo expone /rbac/api/ protegida por auth_request de nginx — un 401
  // ahí significa "sin rol Dinamizador/Administrador" o un fallo puntual de la
  // subpetición, NO que la sesión Django del Inventario haya muerto. Antes, al
  // navegar dentro de /gestion-riesgos/ se disparaba GET /rbac/api/resumen
  // (badge del tab) y, si fallaba, se consultaba /api/sesion/ en carrera con
  // recargar() del shell — a veces marcaba autenticado:false y cerraba la sesión
  // en toda la SPA aunque el login siguiera válido (hallazgo real del usuario).
  if (url.includes('/rbac/api')) return;

  if (!url.includes('/api/')) return;

  const sesion = await consultarSesionInventario();
  eventosApi.dispatchEvent(new CustomEvent('sesion-actualizada', { detail: sesion }));
  if (!sesion.autenticado) {
    eventosApi.dispatchEvent(new CustomEvent('sesion-vencida', { detail: { url } }));
  }
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function peticion(url, opciones = {}) {
  const esRbac = url.includes('/rbac/api');
  const maxIntentos = esRbac ? 3 : 1;

  for (let intento = 0; intento < maxIntentos; intento += 1) {
    const respuesta = await fetch(url, {
      ...opciones,
      credentials: 'same-origin',
      headers: { ...(opciones.headers || {}) },
    });

    if (
      respuesta.status === 401
      && esRbac
      && intento < maxIntentos - 1
    ) {
      const sesion = await consultarSesionInventario();
      if (!sesion.autenticado || !sesion.puede_editar) break;
      await esperar(250 * (intento + 1));
      continue;
    }

    if (respuesta.status === 401) {
      await notificar401(url);
    }
    if (!respuesta.ok) {
      let cuerpo;
      try {
        cuerpo = await respuesta.json();
      } catch {
        cuerpo = null;
      }
      const error = new Error(cuerpo?.detail || respuesta.statusText);
      error.status = respuesta.status;
      error.data = cuerpo;
      throw error;
    }
    if (respuesta.status === 204) return null;
    const tipo = respuesta.headers.get('content-type') || '';
    return tipo.includes('application/json') ? respuesta.json() : respuesta.text();
  }

  const error = new Error('Unauthorized');
  error.status = 401;
  throw error;
}

/** Fábrica de cliente para un backend dado (base + esquema de CSRF). */
export function crearCliente({ base, csrf }) {
  let csrfCache = null;

  async function token() {
    if (csrf.tipo === 'cookie') return leerCookie(csrf.cookie);
    if (!csrfCache) csrfCache = peticion(`${base}${csrf.endpoint}`).then((d) => d[csrf.campo]);
    return csrfCache;
  }

  async function conCsrf(opciones) {
    const t = await token();
    return { ...opciones, headers: { ...(opciones.headers || {}), [csrf.header]: t } };
  }

  return {
    get: (ruta, params) => {
      const qs = params ? `?${new URLSearchParams(params)}` : '';
      return peticion(`${base}${ruta}${qs}`);
    },
    post: async (ruta, cuerpo) =>
      peticion(`${base}${ruta}`, await conCsrf({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo ?? {}),
      })),
    put: async (ruta, cuerpo) =>
      peticion(`${base}${ruta}`, await conCsrf({
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo ?? {}),
      })),
    patch: async (ruta, cuerpo) =>
      peticion(`${base}${ruta}`, await conCsrf({
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo ?? {}),
      })),
    delete: async (ruta) => peticion(`${base}${ruta}`, await conCsrf({ method: 'DELETE' })),
    /** Para multipart/form-data (subida de diagramas, hojas de vida). */
    postForm: async (ruta, formData) =>
      peticion(`${base}${ruta}`, await conCsrf({ method: 'POST', body: formData })),
    patchForm: async (ruta, formData) =>
      peticion(`${base}${ruta}`, await conCsrf({ method: 'PATCH', body: formData })),
  };
}

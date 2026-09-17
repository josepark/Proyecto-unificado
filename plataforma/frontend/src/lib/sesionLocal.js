/** Limpieza de credenciales locales al cambiar de usuario (JWT Riesgos, etc.). */
const CLAVE_USUARIO = 'suiin_usuario_activo';

/** Alias explícito para enlaces de cierre de sesión en la SPA. */
export function prepararCierreSesion() {
  limpiarCredencialesLocales();
  window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
}

export function limpiarCredencialesLocales() {
  localStorage.removeItem('suiin_token');
  localStorage.removeItem('suiin_auth_scheme');
  localStorage.removeItem('suiin_auth_origen');
  localStorage.removeItem('suiin_refresh_token');
  sessionStorage.removeItem(CLAVE_USUARIO);
}

/** Tras login en la SPA unificada, emite JWT de plataforma para Riesgos/RBAC. */
export async function renovarJwtPlataforma() {
  try {
    const respuesta = await fetch('/api/token-jwt/', { credentials: 'same-origin' });
    if (!respuesta.ok) return false;
    const data = await respuesta.json();
    if (!data.token) return false;
    localStorage.setItem('suiin_token', data.token);
    localStorage.setItem('suiin_auth_scheme', 'Bearer');
    localStorage.setItem('suiin_auth_origen', 'sso');
    if (data.refresh_token) {
      localStorage.setItem('suiin_refresh_token', data.refresh_token);
    }
    window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
    return true;
  } catch {
    return false;
  }
}

/** Si cambió el usuario de la sesión, descarta tokens del anterior. */
export function sincronizarUsuarioActivo(username) {
  if (!username) {
    limpiarCredencialesLocales();
    window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
    return;
  }
  const previo = sessionStorage.getItem(CLAVE_USUARIO);
  if (previo && previo !== username) {
    localStorage.removeItem('suiin_token');
    localStorage.removeItem('suiin_auth_scheme');
    localStorage.removeItem('suiin_auth_origen');
    localStorage.removeItem('suiin_refresh_token');
    window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
  }
  sessionStorage.setItem(CLAVE_USUARIO, username);
}

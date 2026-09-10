/** Limpieza de credenciales locales al cambiar de usuario (JWT Riesgos, etc.). */
const CLAVE_USUARIO = 'suiin_usuario_activo';

/** Alias explícito para enlaces de cierre de sesión en la SPA. */
export function prepararCierreSesion() {
  limpiarCredencialesLocales();
}

export function limpiarCredencialesLocales() {
  localStorage.removeItem('suiin_token');
  localStorage.removeItem('suiin_auth_scheme');
  localStorage.removeItem('suiin_auth_origen');
  sessionStorage.removeItem(CLAVE_USUARIO);
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
    window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
  }
  sessionStorage.setItem(CLAVE_USUARIO, username);
}

/** Mensajes de error contextualizados por pantalla RBAC. */
export function mensajeErrorRbac(pantalla, error) {
  if (error?.status === 401) {
    return 'Su sesión no tiene permisos para ver este módulo. Inicie sesión con rol Dinamizador, Administrador o Consultor (solo lectura).';
  }
  if (error?.message) return error.message;
  return `No se pudo cargar ${pantalla}.`;
}

/** Rutas profundas desde el centro de alertas unificado hacia RBAC. */
export const ENLACES_ALERTAS_RBAC = {
  proximos_vencimientos: '/rbac/inicio#vencimientos',
  alertas_mfa: '/rbac/inicio#mfa',
  roles_certificacion_vencida: '/rbac/roles?cert_vencida=1',
  excepciones_vencidas: '/rbac/excepciones?vencidas=1',
};

export function puedeVerRbac({ autenticado, puedeEditar, roles }) {
  if (puedeEditar) return true;
  return autenticado && (roles ?? []).includes('Consultor');
}

export const NIVEL_COLOR = {
  A: '#b3261e', C: '#0b57a4', M: '#0e7c66', L: '#5f6a64', T: '#6d4ea0', '—': '#c9d0ca',
};

export function descripcionNivel(niveles, codigo) {
  const n = (niveles ?? []).find((x) => x.codigo === codigo);
  if (!n) return codigo;
  return `${n.codigo} — ${n.nombre}: ${n.descripcion || ''}`;
}

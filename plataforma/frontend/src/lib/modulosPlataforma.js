/** Proyectos / módulos de la plataforma unificada. */
export const MODULOS_PLATAFORMA = [
  { id: 'inventario', etiqueta: 'Inventario de activos', ruta: '/inventario/dashboard' },
  { id: 'rbac', etiqueta: 'Matriz RBAC', ruta: '/rbac/inicio' },
  { id: 'riesgos', etiqueta: 'Gestión de Riesgos y PTR', ruta: '/gestion-riesgos' },
];

/**
 * ¿El usuario puede acceder al módulo?
 * - Sin sesión: todos visibles (consulta pública del shell).
 * - Con sesión y lista vacía: ninguno (cuenta sin proyectos asignados).
 */
export function tieneModulo(modulos, id, { autenticado = true } = {}) {
  if (!autenticado) return true;
  if (!modulos?.length) return false;
  return modulos.includes(id);
}

/** Primera ruta accesible tras login o redirección por defecto. */
export function rutaInicioModulos(modulos, { autenticado = true } = {}) {
  if (autenticado && !modulos?.length) return '/';
  const primero = MODULOS_PLATAFORMA.find((m) => tieneModulo(modulos, m.id, { autenticado }));
  return primero?.ruta ?? '/';
}

export function etiquetasModulos(modulos, { efectivos = true } = {}) {
  if (!modulos?.length) {
    return efectivos ? ['Sin proyectos asignados'] : MODULOS_PLATAFORMA.map((m) => m.etiqueta);
  }
  return MODULOS_PLATAFORMA.filter((m) => modulos.includes(m.id)).map((m) => m.etiqueta);
}

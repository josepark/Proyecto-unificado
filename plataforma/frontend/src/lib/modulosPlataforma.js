/** Proyectos / módulos de la plataforma unificada. */
export const MODULOS_PLATAFORMA = [
  { id: 'inventario', etiqueta: 'Inventario de activos', ruta: '/inventario/dashboard' },
  { id: 'rbac', etiqueta: 'Matriz RBAC', ruta: '/rbac/inicio' },
  { id: 'riesgos', etiqueta: 'Gestión de Riesgos y PTR', ruta: '/gestion-riesgos' },
];

export function tieneModulo(modulos, id) {
  if (!modulos?.length) return true;
  return modulos.includes(id);
}

/** Primera ruta accesible tras login o redirección por defecto. */
export function rutaInicioModulos(modulos) {
  const primero = MODULOS_PLATAFORMA.find((m) => tieneModulo(modulos, m.id));
  return primero?.ruta ?? '/inventario/dashboard';
}

export function etiquetasModulos(modulos) {
  if (!modulos?.length) {
    return MODULOS_PLATAFORMA.map((m) => m.etiqueta);
  }
  return MODULOS_PLATAFORMA.filter((m) => modulos.includes(m.id)).map((m) => m.etiqueta);
}

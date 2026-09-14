import { describe, expect, it } from 'vitest';
import { tieneModulo, rutaInicioModulos, etiquetasModulos } from './modulosPlataforma';

describe('modulosPlataforma', () => {
  it('sin sesión muestra todos los módulos', () => {
    expect(tieneModulo([], 'rbac', { autenticado: false })).toBe(true);
  });

  it('con sesión y lista vacía no concede acceso', () => {
    expect(tieneModulo([], 'rbac', { autenticado: true })).toBe(false);
  });

  it('filtra módulos explícitos', () => {
    expect(tieneModulo(['rbac'], 'inventario')).toBe(false);
    expect(tieneModulo(['rbac'], 'rbac')).toBe(true);
  });

  it('rutaInicioModulos respeta acceso', () => {
    expect(rutaInicioModulos(['riesgos'])).toBe('/gestion-riesgos');
    expect(rutaInicioModulos(['inventario', 'rbac'])).toBe('/inventario/dashboard');
    expect(rutaInicioModulos([], { autenticado: true })).toBe('/');
    expect(rutaInicioModulos(['rbac'])).toBe('/rbac/inicio');
  });

  it('etiquetasModulos', () => {
    expect(etiquetasModulos(['rbac'])).toEqual(['Matriz RBAC']);
    expect(etiquetasModulos([])).toEqual(['Sin proyectos asignados']);
  });
});

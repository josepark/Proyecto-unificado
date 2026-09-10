import { describe, expect, it } from 'vitest';
import { tieneModulo, rutaInicioModulos, etiquetasModulos } from './modulosPlataforma';

describe('modulosPlataforma', () => {
  it('tieneModulo acepta lista vacía como todos', () => {
    expect(tieneModulo([], 'rbac')).toBe(true);
  });

  it('filtra módulos explícitos', () => {
    expect(tieneModulo(['rbac'], 'inventario')).toBe(false);
    expect(tieneModulo(['rbac'], 'rbac')).toBe(true);
  });

  it('rutaInicioModulos respeta acceso', () => {
    expect(rutaInicioModulos(['riesgos'])).toBe('/gestion-riesgos');
    expect(rutaInicioModulos(['inventario', 'rbac'])).toBe('/inventario/dashboard');
  });

  it('etiquetasModulos', () => {
    expect(etiquetasModulos(['rbac'])).toEqual(['Matriz RBAC']);
  });
});

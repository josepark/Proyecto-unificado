import { describe, it, expect } from 'vitest';
import { claseTagRiesgoMatriz, etiquetaCobertura } from './integracionUi';

describe('integracionUi', () => {
  it('mapea niveles de Riesgos a clases del Inventario', () => {
    expect(claseTagRiesgoMatriz('CRITICO')).toBe('tag t-CRIT');
    expect(claseTagRiesgoMatriz('ALTO')).toBe('tag t-ALTO');
  });

  it('traduce códigos de cobertura', () => {
    expect(etiquetaCobertura('SIN_COBERTURA')).toBe('Sin cobertura');
    expect(etiquetaCobertura('')).toBe('—');
  });
});

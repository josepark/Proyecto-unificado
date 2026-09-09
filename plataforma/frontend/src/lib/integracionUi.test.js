import { describe, it, expect } from 'vitest';
import {
  claseTagRiesgoMatriz,
  claseTagNivelInventario,
  etiquetaCobertura,
  pendientesSync,
} from './integracionUi';

describe('integracionUi', () => {
  it('mapea niveles de Riesgos a clases del Inventario', () => {
    expect(claseTagRiesgoMatriz('CRITICO')).toBe('tag t-CRIT');
    expect(claseTagRiesgoMatriz('ALTO')).toBe('tag t-ALTO');
  });

  it('mapea niveles del Inventario (MED → t-MEDIO)', () => {
    expect(claseTagNivelInventario('MED')).toBe('tag t-MEDIO');
    expect(claseTagNivelInventario('CRIT')).toBe('tag t-CRIT');
  });

  it('traduce códigos de cobertura', () => {
    expect(etiquetaCobertura('SIN_COBERTURA')).toBe('Sin cobertura');
    expect(etiquetaCobertura('')).toBe('—');
  });

  it('suma pendientes de sincronización', () => {
    expect(pendientesSync({ disponible: true, sin_espejo_riesgos: 2, huerfanos_riesgos: 1 })).toBe(3);
    expect(pendientesSync({ disponible: false, sin_espejo_riesgos: 5 })).toBe(0);
  });
});

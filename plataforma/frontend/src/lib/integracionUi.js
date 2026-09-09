/** Mapeo de niveles del módulo Riesgos → clases CSS del Inventario unificado. */
export const NIVEL_RIESGOS_A_TAG = {
  CRITICO: 'CRIT',
  ALTO: 'ALTO',
  MEDIO: 'MED',
  BAJO: 'BAJO',
};

export function claseTagRiesgoMatriz(nivel) {
  if (!nivel) return 'tag';
  const k = NIVEL_RIESGOS_A_TAG[nivel] || nivel;
  return `tag t-${k}`;
}

export function etiquetaCobertura(codigo) {
  const mapa = {
    COMPLETA: 'Completa',
    PARCIAL: 'Parcial',
    SIN_COBERTURA: 'Sin cobertura',
  };
  return mapa[codigo] || codigo || '—';
}

/** Utilidades compartidas — integración Inventario ↔ Riesgos ↔ RBAC (Olas 5–8). */

/** Mapeo de niveles del módulo Riesgos → clases CSS del Inventario unificado. */
export const NIVEL_RIESGOS_A_TAG = {
  CRITICO: 'CRIT',
  ALTO: 'ALTO',
  MEDIO: 'MED',
  BAJO: 'BAJO',
};

/** Códigos de nivel_riesgo del Inventario → clases CSS (theme.css usa t-MEDIO, no t-MED). */
export const NIVEL_INVENTARIO_A_TAG = {
  CRIT: 'CRIT',
  ALTO: 'ALTO',
  MED: 'MEDIO',
  BAJO: 'BAJO',
  SIN: 'BAJO',
};

export const MSG_SYNC_PENDIENTE =
  'Este activo aún no tiene espejo en Gestión de Riesgos. Solicite al administrador del SGSI la sincronización de activos.';

export const MSG_RIESGOS_NO_DISPONIBLE =
  'Gestión de Riesgos no responde en este momento. Intente más tarde o contacte al administrador.';

export const MSG_SYNC_OPERADOR =
  'Ejecute sincronizar_activos_inventario o ./desplegar.sh --sincronizar (ver cron/suiin-sgsi.cron.example).';

export function claseTagRiesgoMatriz(nivel) {
  if (!nivel) return 'tag';
  const k = NIVEL_RIESGOS_A_TAG[nivel] || nivel;
  return `tag t-${k}`;
}

export function claseTagNivelInventario(nivel) {
  if (!nivel) return 'tag';
  const k = NIVEL_INVENTARIO_A_TAG[nivel] || nivel;
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

/** Conteo de pendientes de sincronización Inventario ↔ Riesgos. */
export function pendientesSync(vinculacion) {
  if (!vinculacion?.disponible) return 0;
  return (vinculacion.sin_espejo_riesgos ?? 0) + (vinculacion.huerfanos_riesgos ?? 0);
}

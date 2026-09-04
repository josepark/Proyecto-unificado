export const NIVEL_OPTIONS = [
  { value: "CRITICO", label: "Crítico" },
  { value: "ALTO", label: "Alto" },
  { value: "MEDIO", label: "Medio" },
  { value: "BAJO", label: "Bajo" },
  { value: "SIN_DATO", label: "— Sin dato" },
];

export const CLASIFICACION_SI_OPTIONS = [
  { value: "ALTAMENTE_CONFIDENCIAL", label: "Altamente Confidencial" },
  { value: "CONFIDENCIAL", label: "Confidencial" },
  { value: "PUBLICO", label: "Público" },
  { value: "DESCONOCIDA", label: "Desconocida" },
];

export const COBERTURA_OPTIONS = [
  { value: "COMPLETA", label: "Completa (Nmap+OV)" },
  { value: "PARCIAL", label: "Parcial (solo Nmap)" },
  { value: "SIN_COBERTURA", label: "Sin cobertura" },
];

export const SEVERIDAD_OV_OPTIONS = [
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
  { value: "LOG", label: "Log" },
];

export const TRATAMIENTO_OPTIONS = [
  { value: "MITIGAR_INMEDIATO", label: "Mitigar (inmediato)" },
  { value: "MITIGAR_URGENTE", label: "Mitigar (urgente)" },
  { value: "MITIGAR_PLANIFICADO", label: "Mitigar (planificado)" },
  { value: "ACEPTAR", label: "Aceptar" },
  { value: "TRANSFERIR", label: "Transferir" },
  { value: "ELIMINAR", label: "Eliminar" },
];

export const ESTADO_TRATAMIENTO_OPTIONS = [
  { value: "PENDIENTE", label: "Pendiente" },
  { value: "EN_PROGRESO", label: "En progreso" },
  { value: "CERRADO", label: "Cerrado" },
  { value: "FALSO_POSITIVO", label: "Falso positivo" },
  { value: "ACEPTADO", label: "Aceptado" },
];

export const ESTADO_COMPROMISO_OPTIONS = [
  { value: "COMPROMETIDO", label: "Comprometido" },
  { value: "NO_COMPROMETIDO", label: "No comprometido" },
  { value: "NO_EVALUADO", label: "No evaluado" },
];

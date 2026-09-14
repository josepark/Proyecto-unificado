export const NIVEL_INFO = {
  CRITICO: { label: "Crítico", color: "var(--color-risk-critico)", text: "text-[#e0475a]", bg: "bg-[#e0475a]/15", border: "border-[#e0475a]/40" },
  ALTO: { label: "Alto", color: "var(--color-risk-alto)", text: "text-[#e0812f]", bg: "bg-[#e0812f]/15", border: "border-[#e0812f]/40" },
  MEDIO: { label: "Medio", color: "var(--color-risk-medio)", text: "text-[#e0b559]", bg: "bg-[#e0b559]/15", border: "border-[#e0b559]/40" },
  BAJO: { label: "Bajo", color: "var(--color-risk-bajo)", text: "text-[#4bab7c]", bg: "bg-[#4bab7c]/15", border: "border-[#4bab7c]/40" },
  SIN_DATO: { label: "—", color: "var(--color-risk-sindato)", text: "text-base-300", bg: "bg-base-700/40", border: "border-base-600/40" },
};

export function nivelInfo(nivel) {
  return NIVEL_INFO[nivel] || NIVEL_INFO.SIN_DATO;
}

export const ESTADO_LABELS = {
  PENDIENTE: "Pendiente",
  EN_PROGRESO: "En progreso",
  CERRADO: "Cerrado",
  FALSO_POSITIVO: "Falso positivo",
  ACEPTADO: "Aceptado",
};

export const ESTADO_COLORS = {
  PENDIENTE: "text-base-300 bg-base-700/50 border-base-600/50",
  EN_PROGRESO: "text-[#e0b559] bg-[#e0b559]/15 border-[#e0b559]/40",
  CERRADO: "text-[#4bab7c] bg-[#4bab7c]/15 border-[#4bab7c]/40",
  FALSO_POSITIVO: "text-cric-green-400 bg-cric-green-500/15 border-cric-green-500/40",
  ACEPTADO: "text-base-300 bg-base-700/50 border-base-600/50",
};

export const FASE_LABELS = {
  FASE_1: "Fase 1 — Contención",
  FASE_2: "Fase 2 — Erradicación",
  FASE_3: "Fase 3 — Recuperación",
  FASE_4: "Fase 4 — Lecciones aprendidas",
};

import {
  NIVEL_OPTIONS, CLASIFICACION_SI_OPTIONS, COBERTURA_OPTIONS, SEVERIDAD_OV_OPTIONS,
  TRATAMIENTO_OPTIONS, ESTADO_TRATAMIENTO_OPTIONS, ESTADO_COMPROMISO_OPTIONS,
} from "./choices";

export function activoFields({ campanasOptions = [] } = {}) {
  return [
    { name: "id_activo", label: "ID Activo", required: true, placeholder: "Ej. RED-039", section: "Identificación" },
    { name: "nombre", label: "Nombre", required: true, section: "Identificación" },
    { name: "tipo", label: "Tipo", type: "catalogo", categoria: "TIPO_ACTIVO", placeholder: "Ej. Servidor / Virtualización", section: "Identificación" },
    { name: "ip_principal", label: "IP(s)", placeholder: "192.168.1.x", section: "Identificación" },
    { name: "valor", label: "Valor del activo", type: "number", required: true, min: 0, max: 12, help: "0–12", section: "Identificación" },
    { name: "vlan", label: "VLAN", section: "Identificación" },

    { name: "riesgo_matriz", label: "Riesgo (matriz)", type: "select", options: NIVEL_OPTIONS, help: "se recalcula solo al registrar hallazgos", section: "Clasificación y cobertura" },
    { name: "clasificacion_si", label: "Clasificación SI", type: "select", options: CLASIFICACION_SI_OPTIONS, section: "Clasificación y cobertura" },
    { name: "cobertura", label: "Cobertura de escaneo", type: "select", options: COBERTURA_OPTIONS, section: "Clasificación y cobertura" },
    { name: "en_nmap", label: "Detectado en Nmap", type: "checkbox", section: "Clasificación y cobertura" },
    { name: "puertos_abiertos_resumen", label: "Puertos abiertos (resumen)", placeholder: "Ej. 5 puertos", section: "Clasificación y cobertura" },
    { name: "observacion_critica", label: "Observación crítica", type: "textarea", section: "Clasificación y cobertura" },

    { name: "afectado_red_team", label: "Afectado por Red Team", type: "checkbox", section: "Red Team" },
    { name: "campana_red_team_id", label: "Campaña Red Team", type: "select", options: campanasOptions, fkId: true, section: "Red Team" },
    { name: "estado_ufw_activo", label: "Estado UFW", section: "Red Team" },
    { name: "exfiltracion_confirmada", label: "Exfiltración confirmada", type: "textarea", section: "Red Team" },
    { name: "accion_inmediata_red_team", label: "Acción inmediata Red Team", type: "textarea", section: "Red Team" },
    { name: "mitre_attck", label: "MITRE ATT&CK", type: "mitre", separador: "/", section: "Red Team" },
    { name: "accion_recomendada", label: "Acción recomendada", type: "textarea", section: "Red Team" },
    { name: "estado_operativo", label: "Estado operativo", placeholder: "Ej. Producción / No operación", section: "Red Team" },
  ];
}

export function vulnerabilidadFields({ activosOptions }) {
  return [
    { name: "activo", label: "Activo", type: "select", options: activosOptions, required: true, fkId: true, section: "Identificación" },
    { name: "id_riesgo", label: "ID Riesgo", placeholder: "Ej. RH-045 (opcional)", section: "Identificación" },
    { name: "ip", label: "IP", section: "Identificación" },
    { name: "nombre_vulnerabilidad", label: "Nombre de la vulnerabilidad", required: true, full: true, section: "Identificación" },

    { name: "severidad_ov", label: "Severidad (OpenVAS)", type: "select", options: SEVERIDAD_OV_OPTIONS, section: "Hallazgo técnico" },
    { name: "cvss", label: "CVSS", type: "number", step: 0.1, min: 0, max: 10, section: "Hallazgo técnico" },
    { name: "cves", label: "CVE(s)", placeholder: "CVE-2024-XXXX, CVE-2024-YYYY", section: "Hallazgo técnico" },
    { name: "descripcion_tecnica", label: "Descripción técnica", type: "textarea", section: "Hallazgo técnico" },
    { name: "solucion_recomendada", label: "Solución recomendada", type: "catalogo", categoria: "SOLUCION_VULN", multiline: true, placeholder: "Buscar una solución ya usada, o escribir una nueva…", section: "Hallazgo técnico" },

    { name: "probabilidad", label: "Probabilidad", type: "number", min: 1, max: 5, help: "1–5", section: "Riesgo (ISO 27005)" },
    { name: "impacto", label: "Impacto", type: "number", min: 1, max: 5, help: "1–5", section: "Riesgo (ISO 27005)" },
    { name: "tratamiento", label: "Tratamiento", type: "select", options: TRATAMIENTO_OPTIONS, section: "Riesgo (ISO 27005)" },
    { name: "estado", label: "Estado", type: "select", options: ESTADO_TRATAMIENTO_OPTIONS, section: "Riesgo (ISO 27005)" },

    { name: "evidencia_red_team", label: "Evidencia Red Team", type: "textarea", section: "Correlación Red Team" },
    { name: "explotado_confirmado_rt", label: "Explotado / confirmado por Red Team", section: "Correlación Red Team" },
  ];
}

export function riesgoActivoFields({ activosOptions }) {
  return [
    { name: "activo", label: "Activo", type: "select", options: activosOptions, required: true, fkId: true },
    { name: "id_riesgo", label: "ID Riesgo", required: true, placeholder: "Ej. RA-039" },
    { name: "clasificacion", label: "Clasificación", type: "select", options: NIVEL_OPTIONS },
    { name: "probabilidad", label: "Probabilidad", type: "number", min: 1, max: 5, required: true },
    { name: "impacto", label: "Impacto", type: "number", min: 1, max: 5, required: true },
    { name: "tratamiento", label: "Tratamiento", type: "select", options: TRATAMIENTO_OPTIONS },
    { name: "estado", label: "Estado", type: "select", options: ESTADO_TRATAMIENTO_OPTIONS },
    { name: "responsable_sugerido", label: "Responsable sugerido", type: "catalogo", categoria: "RESPONSABLE_RIESGO" },
    { name: "fecha_objetivo", label: "Fecha objetivo", type: "date" },
    { name: "justificacion", label: "Justificación", type: "textarea", full: true },
    { name: "controles_accion", label: "Controles / acción", type: "textarea", full: true },
  ];
}

export function riesgoContextualFields({ activosOptions, controlesOptions = [] }) {
  return [
    { name: "id_riesgo_contextual", label: "ID", required: true, placeholder: "Ej. RC-08", section: "Identificación" },
    { name: "escenario_amenaza", label: "Escenario de amenaza", required: true, full: true, section: "Identificación" },
    { name: "actor_amenaza", label: "Actor de amenaza", type: "textarea", section: "Identificación" },
    { name: "clasificacion_si", label: "Clasificación SI", type: "select", options: CLASIFICACION_SI_OPTIONS, section: "Identificación" },
    { name: "activos_relacionados", label: "Activos relacionados", type: "multiselect", options: activosOptions, section: "Identificación" },
    { name: "activos_afectados_texto", label: "Activos afectados (texto libre)", type: "textarea", section: "Identificación" },

    { name: "probabilidad", label: "Probabilidad", type: "number", min: 1, max: 5, required: true, section: "Riesgo" },
    { name: "impacto", label: "Impacto", type: "number", min: 1, max: 5, required: true, section: "Riesgo" },
    { name: "datos_especificos_riesgo", label: "Datos específicos en riesgo", type: "textarea", section: "Riesgo" },
    { name: "descripcion_escenario", label: "Descripción del escenario y vector de ataque", type: "textarea", section: "Riesgo" },
    { name: "impacto_cia_misional", label: "Impacto CIA + impacto misional", type: "textarea", section: "Riesgo" },

    { name: "marco_referencia", label: "Marco de referencia", type: "textarea", section: "Controles y marco legal" },
    { name: "controles_iso", label: "Controles ISO 27001 (texto libre, heredado de Excel)", type: "textarea", section: "Controles y marco legal" },
    { name: "controles_iso_vinculados", label: "Controles ISO 27001 — vínculo estructurado", type: "multiselect", options: controlesOptions, full: true, section: "Controles y marco legal" },
    { name: "ley_marco_legal", label: "Ley / marco legal aplicable", type: "textarea", section: "Controles y marco legal" },

    { name: "accion_mitigacion", label: "Acción de mitigación específica CRIC", type: "textarea", full: true, section: "Tratamiento" },
    { name: "plazo", label: "Plazo (texto libre, puede tener varios subplazos)", section: "Tratamiento" },
    { name: "fecha_limite", label: "Fecha límite (real, del ítem más urgente) — habilita alertas de vencimiento", type: "date", section: "Tratamiento" },
    { name: "responsable", label: "Responsable (org. CRIC)", section: "Tratamiento" },
    { name: "estado", label: "Estado", type: "select", options: ESTADO_TRATAMIENTO_OPTIONS, section: "Tratamiento" },
    { name: "estado_actual", label: "Estado (texto libre, heredado de Excel)", placeholder: "Ej. Sin control / En progreso / Controlado", section: "Tratamiento" },
    { name: "observaciones_correlacion", label: "Correlación con riesgos técnicos", type: "textarea", full: true, section: "Tratamiento" },
  ];
}

export const FASE_OPTIONS = [
  { value: "FASE_1", label: "Fase 1 — Contención inmediata" },
  { value: "FASE_2", label: "Fase 2 — Erradicación" },
  { value: "FASE_3", label: "Fase 3 — Recuperación" },
  { value: "FASE_4", label: "Fase 4 — Lecciones aprendidas" },
];

export const OPCION_TRATAMIENTO_OPTIONS = [
  { value: "MITIGAR", label: "Mitigar" },
  { value: "MITIGAR_ELIMINAR", label: "Mitigar / Eliminar" },
  { value: "ACEPTAR", label: "Aceptar" },
  { value: "TRANSFERIR", label: "Transferir" },
  { value: "ELIMINAR", label: "Eliminar" },
];

export const ESTADO_PLAN_OPTIONS = [
  { value: "ACTIVO", label: "Activo" },
  { value: "ARCHIVADO", label: "Archivado" },
  { value: "CERRADO", label: "Cerrado" },
];

export function planTratamientoFields({ campanasOptions }) {
  return [
    { name: "campana_red_team_id", label: "Campaña Red Team", type: "select", options: campanasOptions, required: true, fkId: true },
    { name: "referencia", label: "Referencia", required: true, placeholder: "Ej. SUIIN-SGSI-PTR-002 v1.0" },
    { name: "titulo", label: "Título", required: true, full: true },
    { name: "clasificacion_documento", label: "Clasificación", placeholder: "CONFIDENCIAL — Uso Interno Restringido" },
    { name: "fecha_emision", label: "Fecha de emisión", type: "date", required: true },
    { name: "periodo_campana_inicio", label: "Período — inicio", type: "date" },
    { name: "periodo_campana_fin", label: "Período — fin", type: "date" },
    { name: "herramientas", label: "Herramientas", full: true, placeholder: "MITRE CALDERA · OpenVAS · OWASP ZAP · Nuclei · NMAP" },
    { name: "estado_plan", label: "Estado del plan", type: "select", options: ESTADO_PLAN_OPTIONS },
  ];
}

export function accionTratamientoFields({ planOptions = [], controlesOptions = [] } = {}) {
  return [
    { name: "plan", label: "Plan de tratamiento (PTR)", type: "select", options: planOptions, required: true, fkId: true, section: "Identificación" },
    { name: "id_riesgo", label: "ID", required: true, placeholder: "Ej. R-13", section: "Identificación" },
    { name: "descripcion_riesgo", label: "Descripción del riesgo", required: true, type: "textarea", full: true, section: "Identificación" },
    { name: "fuente", label: "Fuente", type: "catalogo", categoria: "FUENTE_HALLAZGO", placeholder: "Ej. CALDERA – Thief", section: "Identificación" },
    { name: "tecnica_mitre_cwe", label: "Técnica MITRE / CWE", type: "mitre", separador: " · ", placeholder: "Buscar MITRE, o escribir un código CWE (ej. CWE-306)…", section: "Identificación" },

    { name: "probabilidad", label: "Probabilidad", type: "number", min: 1, max: 5, required: true, section: "Riesgo y tratamiento" },
    { name: "impacto", label: "Impacto", type: "number", min: 1, max: 5, required: true, section: "Riesgo y tratamiento" },
    { name: "opcion_tratamiento", label: "Opción de tratamiento", type: "select", options: OPCION_TRATAMIENTO_OPTIONS, section: "Riesgo y tratamiento" },
    { name: "fase", label: "Fase", type: "select", options: FASE_OPTIONS, section: "Riesgo y tratamiento" },
    { name: "control_iso27001", label: "Control ISO 27001 (texto libre, heredado de Excel)", section: "Riesgo y tratamiento" },
    { name: "controles_iso_vinculados", label: "Controles ISO 27001 (Anexo A) — vínculo estructurado", type: "multiselect", options: controlesOptions, full: true, section: "Riesgo y tratamiento" },

    { name: "acciones_tratamiento", label: "Acciones de tratamiento", type: "textarea", full: true, required: true, section: "Ejecución" },
    { name: "kpi_criterio_cierre", label: "KPI / criterio de cierre", type: "textarea", full: true, section: "Ejecución" },
    { name: "herramienta_comando", label: "Herramienta / comando clave", type: "textarea", full: true, section: "Ejecución" },
    { name: "responsable", label: "Responsable", type: "catalogo", categoria: "RESPONSABLE_ACCION", section: "Ejecución" },
    { name: "plazo", label: "Plazo", type: "catalogo", categoria: "PLAZO_ACCION", placeholder: "Ej. 0–4 h", section: "Ejecución" },

    { name: "estado", label: "Estado", type: "select", options: ESTADO_TRATAMIENTO_OPTIONS, section: "Seguimiento" },
    { name: "fecha_limite_texto", label: "Fecha límite (texto libre, heredado de Excel)", placeholder: "Ej. 0–4 h post-incidente", section: "Seguimiento" },
    { name: "fecha_limite", label: "Fecha límite (real) — habilita alertas de vencimiento", type: "date", section: "Seguimiento" },
    { name: "fecha_cierre_real", label: "Fecha de cierre real", type: "date", section: "Seguimiento" },
    { name: "porcentaje_avance", label: "% Avance", type: "number", min: 0, max: 100, section: "Seguimiento" },
  ];
}

export function campanaRedTeamFields() {
  return [
    { name: "nombre", label: "Nombre", required: true, placeholder: "Ej. SUIIN-NUEVA-CAMPANA", section: "Identificación" },
    { name: "host_ip", label: "IP del host objetivo", required: true, placeholder: "192.168.1.x", section: "Identificación" },
    { name: "fecha_inicio", label: "Fecha inicio", type: "date", section: "Identificación" },
    { name: "fecha_fin", label: "Fecha fin", type: "date", section: "Identificación" },
    { name: "estado_compromiso", label: "Estado de compromiso", type: "select", options: ESTADO_COMPROMISO_OPTIONS, section: "Identificación" },

    { name: "estado_ufw", label: "Estado UFW", section: "Hallazgos técnicos" },
    { name: "uptime_sin_reinicio", label: "Uptime sin reinicio", section: "Hallazgos técnicos" },
    { name: "agentes_implantados", label: "Agentes implantados", type: "textarea", section: "Hallazgos técnicos" },
    { name: "servidores_c2", label: "Servidor(es) C2", type: "textarea", section: "Hallazgos técnicos" },
    { name: "datos_exfiltrados", label: "Datos exfiltrados", type: "textarea", full: true, section: "Hallazgos técnicos" },
    { name: "puertos_no_documentados", label: "Puertos no documentados", type: "textarea", full: true, section: "Hallazgos técnicos" },

    { name: "riesgo_maximo_correlacionado", label: "Riesgo máximo correlacionado", section: "Resumen de riesgos" },
    { name: "riesgos_criticos", label: "Riesgos críticos", type: "number", min: 0, section: "Resumen de riesgos" },
    { name: "riesgos_altos", label: "Riesgos altos", type: "number", min: 0, section: "Resumen de riesgos" },
    { name: "riesgos_medios", label: "Riesgos medios", type: "number", min: 0, section: "Resumen de riesgos" },
    { name: "riesgos_bajos", label: "Riesgos bajos", type: "number", min: 0, section: "Resumen de riesgos" },
    { name: "tecnicas_mitre_count", label: "N.º técnicas MITRE", type: "number", min: 0, section: "Resumen de riesgos" },
    { name: "tecnicas_mitre_detalle", label: "Detalle de técnicas MITRE", type: "textarea", full: true, section: "Resumen de riesgos" },
  ];
}

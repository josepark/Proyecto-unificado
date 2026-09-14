import { rutaRiesgos } from "../context/PlataformaContext";

/** Rutas internas del módulo según el origen de una acción PTR. */
export function rutaOrigenAccion(anidado, prefijo, accion) {
  if (accion.origen_vulnerabilidad_id && accion.origen_vulnerabilidad_activo_id) {
    return rutaRiesgos(anidado, prefijo, `activos/${accion.origen_vulnerabilidad_activo_id}`);
  }
  if (accion.origen_riesgo_activo && accion.origen_riesgo_activo_activo_id) {
    return rutaRiesgos(anidado, prefijo, `activos/${accion.origen_riesgo_activo_activo_id}`);
  }
  if (accion.origen_riesgo_contextual) {
    return rutaRiesgos(anidado, prefijo, `riesgos-contextuales?highlight=${accion.origen_riesgo_contextual}`);
  }
  return null;
}

export function etiquetaOrigenAccion(accion) {
  if (accion.origen_vulnerabilidad_nombre) {
    return `Vulnerabilidad: ${accion.origen_vulnerabilidad_nombre}`;
  }
  if (accion.origen_riesgo_activo_id) {
    return `Riesgo activo: ${accion.origen_riesgo_activo_id}`;
  }
  if (accion.origen_riesgo_contextual_id) {
    return `Riesgo contextual: ${accion.origen_riesgo_contextual_id}`;
  }
  return null;
}

export function rutaPlanTratamiento(anidado, prefijo, { planId, accionId } = {}) {
  const params = new URLSearchParams();
  if (planId) params.set("plan", planId);
  if (accionId) params.set("accion", accionId);
  const qs = params.toString();
  return rutaRiesgos(anidado, prefijo, qs ? `plan-tratamiento?${qs}` : "plan-tratamiento");
}

export function rutaAlertaVencimiento(anidado, prefijo, item) {
  if (item.tipo === "accion") {
    return rutaPlanTratamiento(anidado, prefijo, { planId: item.plan, accionId: item.id });
  }
  if (item.tipo === "riesgo") {
    return rutaRiesgos(anidado, prefijo, `riesgos-activo?highlight=${item.id}`);
  }
  if (item.tipo === "contextual") {
    return rutaRiesgos(anidado, prefijo, `riesgos-contextuales?highlight=${item.id}`);
  }
  return rutaRiesgos(anidado, prefijo, "plan-tratamiento");
}

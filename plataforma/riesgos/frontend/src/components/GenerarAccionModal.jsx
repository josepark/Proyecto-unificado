import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import Modal from "./Modal";
import EntityForm from "./EntityForm";
import { accionTratamientoFields } from "../lib/entitySchemas";

/** origen: { tipo: 'vulnerabilidad' | 'riesgo_activo' | 'riesgo_contextual', objeto: {...} } */
export default function GenerarAccionModal({ open, onClose, origen, onCreated }) {
  const { data: planesData } = useApiData(
    () => (open ? endpoints.planesTratamiento({ page_size: 100 }) : Promise.resolve({ data: null })),
    [open]
  );
  const planes = planesData?.results ?? planesData ?? [];
  const planOptions = planes.map((p) => ({ value: p.id, label: p.referencia }));

  const { data: controlesData } = useApiData(
    () => (open ? endpoints.controlesIso({ page_size: 100 }) : Promise.resolve({ data: null })),
    [open]
  );
  const controlesOptions = (controlesData?.results ?? controlesData ?? [])
    .map((c) => ({ value: c.id, label: `${c.codigo} — ${c.nombre}` }));

  if (!open || !origen) return null;

  const tipo = origen.tipo; // 'vulnerabilidad' | 'riesgo_activo' | 'riesgo_contextual'
  const CAMPOS_POR_TIPO = {
    vulnerabilidad: {
      descripcion_riesgo: origen.objeto.nombre_vulnerabilidad,
      acciones_tratamiento: origen.objeto.solucion_recomendada || "",
      responsable: "",
      etiquetaOrigen: origen.objeto.nombre_vulnerabilidad,
    },
    riesgo_activo: {
      descripcion_riesgo: origen.objeto.justificacion || `Riesgo agregado ${origen.objeto.id_riesgo}`,
      acciones_tratamiento: origen.objeto.controles_accion || "",
      responsable: origen.objeto.responsable_sugerido || "",
      etiquetaOrigen: origen.objeto.id_riesgo,
    },
    riesgo_contextual: {
      descripcion_riesgo: origen.objeto.escenario_amenaza || `Riesgo contextual ${origen.objeto.id_riesgo_contextual}`,
      acciones_tratamiento: origen.objeto.accion_mitigacion || "",
      responsable: origen.objeto.responsable || "",
      etiquetaOrigen: origen.objeto.id_riesgo_contextual,
    },
  };
  const c = CAMPOS_POR_TIPO[tipo];
  const valoresIniciales = {
    descripcion_riesgo: c.descripcion_riesgo,
    probabilidad: origen.objeto.probabilidad || "",
    impacto: origen.objeto.impacto || "",
    acciones_tratamiento: c.acciones_tratamiento,
    responsable: c.responsable,
    // Mismos valores por defecto que ya tiene el modelo (AccionTratamiento en
    // models.py) — sin esto, los tres quedaban en la opción "—" en blanco del
    // desplegable, y el formulario rechazaba el guardado con "no es una
    // elección válida" hasta que alguien los seleccionara a mano, para los
    // tres orígenes por igual (no era un problema nuevo de riesgo contextual,
    // se hizo evidente al probar este flujo de punta a punta).
    opcion_tratamiento: "MITIGAR",
    fase: "FASE_1",
    estado: "PENDIENTE",
    porcentaje_avance: 0,
  };

  async function guardar(values) {
    const payload = {
      ...values,
      plan: Number(values.plan),
      origen_vulnerabilidad: tipo === "vulnerabilidad" ? origen.objeto.id : null,
      origen_riesgo_activo: tipo === "riesgo_activo" ? origen.objeto.id : null,
      origen_riesgo_contextual: tipo === "riesgo_contextual" ? origen.objeto.id : null,
    };
    await endpoints.crearAccion(payload);
    onCreated();
    onClose();
  }

  if (planes.length === 0) {
    return (
      <Modal open={open} onClose={onClose} title="Generar acción de tratamiento" width="max-w-md">
        <p className="text-[13px] leading-relaxed text-base-300">
          Aún no hay ningún Plan de Tratamiento de Riesgos (PTR) creado. Cree uno primero
          desde <strong className="text-base-100">Plan de tratamiento → Nuevo PTR</strong>,
          y vuelva aquí para generar la acción con este origen ya enlazado.
        </p>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Generar acción de tratamiento"
      subtitle={`Origen: ${c.etiquetaOrigen} — quedará enlazada a este hallazgo`}
      width="max-w-2xl"
    >
      <EntityForm
        fields={accionTratamientoFields({ planOptions, controlesOptions })}
        initialValues={valoresIniciales}
        onSubmit={guardar}
        onCancel={onClose}
        submitLabel="Crear acción de tratamiento"
      />
    </Modal>
  );
}

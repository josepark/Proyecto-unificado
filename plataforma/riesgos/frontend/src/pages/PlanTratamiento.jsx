import { useState } from "react";
import { CalendarClock, Wrench, Target, Plus, Pencil, Trash2, Link2, AlertTriangle } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { accionTratamientoFields, planTratamientoFields } from "../lib/entitySchemas";
import PageHeader from "../components/PageHeader";
import NivelBadge from "../components/NivelBadge";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import ConfirmDialog from "../components/ConfirmDialog";
import HistorialPanel from "../components/HistorialPanel";
import EvidenciaUploader from "../components/EvidenciaUploader";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { ESTADO_LABELS, ESTADO_COLORS, FASE_LABELS } from "../lib/risk";

export default function PlanTratamiento() {
  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const { data: planes, loading: loadingPlanes, reload: reloadPlanes } = useApiData(() => endpoints.planesTratamiento());
  const listaPlanes = planes?.results ?? planes ?? [];
  const [planId, setPlanId] = useState(null);
  const idActivo = planId ?? listaPlanes[0]?.id;

  const { data: plan, loading, error, reload } = useApiData(
    () => (idActivo ? endpoints.planTratamiento(idActivo) : Promise.resolve({ data: null })),
    [idActivo]
  );
  const { data: campanasData } = useApiData(() => endpoints.campanasRedTeam());
  const campanasOptions = (campanasData?.results ?? campanasData ?? []).map((c) => ({ value: c.id, label: c.nombre }));
  const { data: controlesData } = useApiData(() => endpoints.controlesIso({ page_size: 100 }));
  const controlesOptions = (controlesData?.results ?? controlesData ?? [])
    .map((c) => ({ value: c.id, label: `${c.codigo} — ${c.nombre}` }));

  const [nuevoPlanOpen, setNuevoPlanOpen] = useState(false);
  const [formAccionOpen, setFormAccionOpen] = useState(false);
  const [editandoAccion, setEditandoAccion] = useState(null);
  const [faseNuevaAccion, setFaseNuevaAccion] = useState("FASE_1");
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  async function crearPlan(values) {
    const res = await endpoints.crearPlanTratamiento(values);
    setNuevoPlanOpen(false);
    await reloadPlanes();
    setPlanId(res.data.id);
  }

  async function guardarAccion(values) {
    const payload = { ...values, plan: Number(idActivo) };
    if (editandoAccion) await endpoints.actualizarAccion(editandoAccion.id, payload);
    else await endpoints.crearAccion(payload);
    setFormAccionOpen(false);
    setEditandoAccion(null);
    reload();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarAccion(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  if (loadingPlanes || (idActivo && loading)) return <PageShell><LoadingState /></PageShell>;

  if (!listaPlanes.length) {
    return (
      <PageShell>
        <PageHeader
          eyebrow="PTR"
          title="Plan de tratamiento de riesgos"
          actions={<NuevoPTRButton guard={guard} onClick={() => setNuevoPlanOpen(true)} />}
        />
        <EmptyState label="Aún no hay ningún Plan de Tratamiento de Riesgos. Cree el primero, o impórtelo desde Excel (ver README)." />
        <ModalNuevoPlan open={nuevoPlanOpen} onClose={() => setNuevoPlanOpen(false)} campanasOptions={campanasOptions} onSubmit={crearPlan} />
        <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow={plan?.clasificacion_documento}
        title={plan?.titulo || "Plan de tratamiento de riesgos"}
        description={plan && `${plan.referencia} · ${plan.campana_red_team?.nombre} (${plan.campana_red_team?.host_ip}) · Emitido ${plan.fecha_emision} · Herramientas: ${plan.herramientas}`}
        actions={
          <div className="flex items-center gap-2">
            {listaPlanes.length > 1 && (
              <select
                value={idActivo || ""}
                onChange={(e) => setPlanId(Number(e.target.value))}
                className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100"
              >
                {listaPlanes.map((p) => (
                  <option key={p.id} value={p.id}>{p.referencia}</option>
                ))}
              </select>
            )}
            <NuevoPTRButton guard={guard} onClick={() => setNuevoPlanOpen(true)} />
          </div>
        }
      />

      {idActivo && loading ? (
        <LoadingState />
      ) : error || !plan ? (
        <ErrorState />
      ) : (
        <>
          <ProgresoGlobal plan={plan} />
          <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
            {["FASE_1", "FASE_2", "FASE_3", "FASE_4"].map((fase) => (
              <FaseColumna
                key={fase}
                fase={fase}
                acciones={plan.acciones.filter((a) => a.fase === fase)}
                guard={guard}
                onNueva={() => { setFaseNuevaAccion(fase); setEditandoAccion(null); setFormAccionOpen(true); }}
                onEditar={(a) => { setEditandoAccion(a); setFormAccionOpen(true); }}
                onEliminar={setBorrando}
                onChanged={reload}
              />
            ))}
          </div>
        </>
      )}

      <Modal
        open={formAccionOpen}
        onClose={() => setFormAccionOpen(false)}
        title={editandoAccion ? `Editar ${editandoAccion.id_riesgo}` : "Nueva acción de tratamiento"}
        width="max-w-2xl"
      >
        <EntityForm
          fields={accionTratamientoFields({ planOptions: [{ value: idActivo, label: plan?.referencia }], controlesOptions })}
          initialValues={editandoAccion || { plan: idActivo, fase: faseNuevaAccion }}
          onSubmit={guardarAccion}
          onCancel={() => setFormAccionOpen(false)}
          submitLabel={editandoAccion ? "Guardar cambios" : "Crear acción"}
        />
      </Modal>

      <ConfirmDialog
        open={!!borrando}
        onClose={() => setBorrando(null)}
        onConfirm={confirmarEliminar}
        loading={eliminando}
        title={`¿Eliminar ${borrando?.id_riesgo}?`}
      />

      <ModalNuevoPlan open={nuevoPlanOpen} onClose={() => setNuevoPlanOpen(false)} campanasOptions={campanasOptions} onSubmit={crearPlan} />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </PageShell>
  );
}

function NuevoPTRButton({ guard, onClick }) {
  return (
    <button
      onClick={guard(onClick)}
      className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
    >
      <Plus className="h-4 w-4" /> Nuevo PTR
    </button>
  );
}

function ModalNuevoPlan({ open, onClose, campanasOptions, onSubmit }) {
  return (
    <Modal open={open} onClose={onClose} title="Nuevo Plan de Tratamiento de Riesgos" width="max-w-xl">
      <EntityForm
        fields={planTratamientoFields({ campanasOptions })}
        initialValues={{}}
        onSubmit={onSubmit}
        onCancel={onClose}
        submitLabel="Crear PTR"
      />
    </Modal>
  );
}

function ProgresoGlobal({ plan }) {
  const total = plan.acciones.length;
  // Usa el porcentaje que ya calcula el backend (plan.porcentaje_avance_global)
  // en vez de recalcularlo aquí — este componente tenía su propia cuenta
  // aparte que excluía "Aceptado" del avance, el mismo bug que ya se había
  // corregido del lado del backend pero nunca llegó a usarse en esta vista.
  // "cerradas" se muestra solo como conteo visual (ESTADOS_CERRADOS del
  // backend: Cerrado, Falso positivo, Aceptado).
  const ESTADOS_CERRADOS = ["CERRADO", "FALSO_POSITIVO", "ACEPTADO"];
  const cerradas = plan.acciones.filter((a) => ESTADOS_CERRADOS.includes(a.estado)).length;
  const pct = plan.porcentaje_avance_global ?? (total ? Math.round((cerradas / total) * 100) : 0);
  return (
    <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
      <div className="flex items-center justify-between text-sm">
        <p className="font-medium text-base-100">Progreso global del plan</p>
        <p className="font-mono-data text-cric-green-400">{cerradas} / {total} acciones · {pct}%</p>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-base-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cric-green-600 to-cric-green-400 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function FaseColumna({ fase, acciones, guard, onNueva, onEditar, onEliminar, onChanged }) {
  return (
    <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-base-100">
          {FASE_LABELS[fase] || fase}
          <span className="ml-2 font-mono-data text-xs font-normal text-base-300">({acciones.length})</span>
        </h3>
        <button onClick={guard(onNueva)} className="flex items-center gap-1 text-[11px] font-medium text-cric-green-400 hover:underline">
          <Plus className="h-3 w-3" /> Nueva
        </button>
      </div>
      {acciones.length === 0 ? (
        <p className="py-4 text-center text-[12px] text-base-300/60">Sin acciones en esta fase.</p>
      ) : (
        <div className="space-y-3">
          {acciones.map((accion) => (
            <AccionCard key={accion.id} accion={accion} guard={guard} onEditar={() => onEditar(accion)} onEliminar={() => onEliminar(accion)} onChanged={onChanged} />
          ))}
        </div>
      )}
    </div>
  );
}

function AccionCard({ accion, guard, onEditar, onEliminar, onChanged }) {
  const [guardando, setGuardando] = useState(false);

  async function cambiarEstado(nuevoEstado) {
    setGuardando(true);
    try {
      await endpoints.actualizarAccion(accion.id, { estado: nuevoEstado });
      onChanged();
    } finally {
      setGuardando(false);
    }
  }

  const origenLabel = accion.origen_vulnerabilidad_nombre || accion.origen_riesgo_activo_id;

  return (
    <div className={`rounded-xl border p-4 ${
      accion.esta_vencida ? "border-[#e0475a]/50 bg-[#e0475a]/5" : "border-base-700/60 bg-base-850/60"
    }`}>
      {(accion.esta_vencida || accion.por_vencer) && (
        <div className={`mb-2 flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium ${
          accion.esta_vencida ? "bg-[#e0475a]/15 text-[#e0475a]" : "bg-[#e0b559]/15 text-[#e0b559]"
        }`}>
          <AlertTriangle className="h-3 w-3" />
          {accion.esta_vencida
            ? `Vencida hace ${Math.abs(accion.dias_para_vencer)} día(s)`
            : `Vence en ${accion.dias_para_vencer} día(s)`}
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-mono-data text-[13px] font-semibold text-cric-gold-400">{accion.id_riesgo}</span>
          <NivelBadge nivel={accion.nivel_riesgo} size="sm" />
        </div>
        <div className="flex items-center gap-1">
          <span className="font-mono-data text-[11px] text-base-300">P{accion.probabilidad}×I{accion.impacto}={accion.score}</span>
          <button onClick={guard(onEditar)} className="rounded p-1 text-base-300 hover:bg-base-800 hover:text-cric-green-400">
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button onClick={guard(onEliminar)} className="rounded p-1 text-base-300 hover:bg-base-800 hover:text-[#e0475a]">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {origenLabel && (
        <p className="mt-1.5 flex items-center gap-1 text-[11px] text-cric-gold-400/90">
          <Link2 className="h-3 w-3" /> Generada desde: {origenLabel}
        </p>
      )}

      <p className="mt-2 text-[13px] leading-relaxed text-base-100">{accion.descripcion_riesgo}</p>

      {accion.acciones_tratamiento && (
        <p className="mt-2 whitespace-pre-line text-[12px] leading-relaxed text-base-300">
          {accion.acciones_tratamiento}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-base-300">
        {accion.plazo && (
          <span className="flex items-center gap-1"><CalendarClock className="h-3 w-3" /> {accion.plazo}</span>
        )}
        {accion.responsable && (
          <span className="flex items-center gap-1"><Target className="h-3 w-3" /> {accion.responsable}</span>
        )}
        {accion.control_iso27001 && (
          <span className="flex items-center gap-1"><Wrench className="h-3 w-3" /> {accion.control_iso27001}</span>
        )}
      </div>

      {accion.herramienta_comando && (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-base-950/80 px-3 py-2 font-mono-data text-[11px] text-cric-green-400">
          {accion.herramienta_comando}
        </pre>
      )}

      <div className="mt-3 flex items-center justify-between border-t border-base-700/50 pt-3">
        <select
          value={accion.estado}
          disabled={guardando}
          onChange={(e) => cambiarEstado(e.target.value)}
          className={`rounded-md border px-2 py-1 text-[11px] font-medium outline-none ${ESTADO_COLORS[accion.estado]}`}
        >
          {Object.entries(ESTADO_LABELS).map(([value, label]) => (
            <option key={value} value={value} className="bg-base-900 text-base-100">{label}</option>
          ))}
        </select>
        <span className="font-mono-data text-[11px] text-base-300">{accion.porcentaje_avance}%</span>
      </div>

      <div className="mt-3 space-y-2">
        <EvidenciaUploader modelo="acciontratamiento" objectId={accion.id} />
        <HistorialPanel recurso="acciones-tratamiento" id={accion.id} />
      </div>
    </div>
  );
}

function PageShell({ children }) {
  return <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>;
}

import { useState } from "react";
import { ChevronDown, Scale, Users2, Landmark, Plus, Pencil, Trash2, AlertTriangle, ClipboardPlus } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { riesgoContextualFields } from "../lib/entitySchemas";
import PageHeader from "../components/PageHeader";
import NivelBadge from "../components/NivelBadge";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import ConfirmDialog from "../components/ConfirmDialog";
import EvidenciaUploader from "../components/EvidenciaUploader";
import GenerarAccionModal from "../components/GenerarAccionModal";
import HistorialPanel from "../components/HistorialPanel";
import EnlacesAccionesPtr from "../components/EnlacesAccionesPtr";
import Paginador from "../components/Paginador";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

const PAGE_SIZE = 50;

export default function RiesgosContextuales() {
  const highlightId = new URLSearchParams(window.location.search).get("highlight");
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useApiData(
    () => endpoints.riesgosContextuales({ ordering: "-score", page: page, page_size: PAGE_SIZE }),
    [page]
  );
  const { data: activosData } = useApiData(() => endpoints.activos({ page_size: 200, ordering: "id_activo" }));
  const riesgos = data?.results ?? data ?? [];
  const activosOptions = (activosData?.results ?? activosData ?? []).map((a) => ({ value: a.id, label: `${a.id_activo} — ${a.nombre}` }));
  const { data: controlesData } = useApiData(() => endpoints.controlesIso({ page_size: 100 }));
  const controlesOptions = (controlesData?.results ?? controlesData ?? [])
    .map((c) => ({ value: c.id, label: `${c.codigo} — ${c.nombre}` }));

  const { guard, loginOpen, setLoginOpen, puedeEditar } = useAuthGuard();
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);
  const [origenAccion, setOrigenAccion] = useState(null);

  async function guardar(values) {
    const payload = {
      ...values,
      activos_relacionados: (values.activos_relacionados || []).map(Number),
    };
    if (editando) await endpoints.actualizarRiesgoContextual(editando.id, payload);
    else await endpoints.crearRiesgoContextual(payload);
    setFormOpen(false);
    reload();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarRiesgoContextual(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  function valoresEdicion(r) {
    if (!r) return {};
    return { ...r, activos_relacionados: (r.activos_relacionados_ids || r.activos_relacionados || []) };
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <PageHeader
        eyebrow="Contexto organizacional · ISO 27001 cláusula 4.1/4.2"
        title="Riesgos contextuales"
        description="Escenarios de amenaza no detectables por escáneres técnicos: derivan del perfil de CRIC como organización indígena en zonas de operación con alta exposición. Escala propia 1–5, independiente del CVSS."
        actions={puedeEditar && (
          <button
            onClick={guard(() => { setEditando(null); setFormOpen(true); })}
            className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
          >
            <Plus className="h-4 w-4" /> Nuevo riesgo
          </button>
        )}
      />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState />
      ) : riesgos.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {riesgos.map((r) => (
            <RiesgoContextualCard
              key={r.id}
              riesgo={r}
              resaltado={highlightId && String(r.id) === highlightId}
              puedeEditar={puedeEditar}
              onEditar={guard(() => { setEditando(r); setFormOpen(true); })}
              onEliminar={guard(() => setBorrando(r))}
              onGenerarAccion={guard(() => setOrigenAccion({ tipo: "riesgo_contextual", objeto: r }))}
            />
          ))}
        </div>
      )}

      <Paginador data={data} page={page} onPageChange={setPage} pageSize={PAGE_SIZE} />

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editando ? `Editar ${editando.id_riesgo_contextual}` : "Nuevo riesgo contextual"} width="max-w-3xl">
        <EntityForm
          fields={riesgoContextualFields({ activosOptions, controlesOptions })}
          initialValues={valoresEdicion(editando)}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear riesgo contextual"}
        />
      </Modal>

      <ConfirmDialog open={!!borrando} onClose={() => setBorrando(null)} onConfirm={confirmarEliminar} loading={eliminando}
        title={`¿Eliminar ${borrando?.id_riesgo_contextual}?`} />

      <GenerarAccionModal
        open={!!origenAccion}
        onClose={() => setOrigenAccion(null)}
        origen={origenAccion}
        onCreated={reload}
      />

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

function RiesgoContextualCard({ riesgo, resaltado, puedeEditar, onEditar, onEliminar, onGenerarAccion }) {
  const [abierto, setAbierto] = useState(!!resaltado);

  return (
    <div
      id={`riesgo-contextual-${riesgo.id}`}
      className={`overflow-hidden rounded-2xl border ${
      resaltado ? "border-cric-green-500/50 ring-1 ring-cric-green-500/30"
        : riesgo.esta_vencido ? "border-[#e0475a]/50 bg-[#e0475a]/5" : "border-base-700/60 bg-base-900/60"
    }`}>
      {(riesgo.esta_vencido || riesgo.por_vencer) && (
        <div className={`flex items-center gap-1.5 px-5 pt-3 text-[11px] font-medium ${
          riesgo.esta_vencido ? "text-[#e0475a]" : "text-[#e0b559]"
        }`}>
          <AlertTriangle className="h-3 w-3" />
          {riesgo.esta_vencido
            ? `Vencido hace ${Math.abs(riesgo.dias_para_vencer)} día(s)`
            : `Vence en ${riesgo.dias_para_vencer} día(s)`}
        </div>
      )}
      <div className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left">
        <button onClick={() => setAbierto((v) => !v)} className="flex flex-1 items-center gap-4 text-left">
          <span className="font-mono-data text-sm font-semibold text-cric-gold-400">
            {riesgo.id_riesgo_contextual}
          </span>
          <div>
            <p className="text-sm font-medium text-base-100">{riesgo.escenario_amenaza}</p>
            <p className="mt-0.5 text-[12px] text-base-300">{riesgo.actor_amenaza}</p>
          </div>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono-data text-[11px] text-base-300">
            P{riesgo.probabilidad}×I{riesgo.impacto}={riesgo.score}
          </span>
          <NivelBadge nivel={riesgo.nivel_riesgo} size="sm" />
          {puedeEditar && (
            <>
              <button onClick={onGenerarAccion} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-gold-400" title="Generar acción de tratamiento">
                <ClipboardPlus className="h-3.5 w-3.5" />
              </button>
              <button onClick={onEditar} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={onEliminar} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-[#e0475a]">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          <button onClick={() => setAbierto((v) => !v)}>
            <ChevronDown className={`h-4 w-4 text-base-300 transition-transform ${abierto ? "rotate-180" : ""}`} />
          </button>
        </div>
      </div>

      {abierto && (
        <div className="space-y-4 border-t border-base-700/60 px-5 py-4 text-[13px]">
          <Field icon={Users2} label="Datos específicos en riesgo" value={riesgo.datos_especificos_riesgo} />
          <Field label="Descripción del escenario y vector de ataque" value={riesgo.descripcion_escenario} />
          <Field label="Impacto CIA + impacto misional" value={riesgo.impacto_cia_misional} />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field icon={Scale} label="Controles ISO 27001 / marcos" value={riesgo.controles_iso} />
            <Field icon={Landmark} label="Marco legal aplicable (Colombia)" value={riesgo.ley_marco_legal} />
          </div>
          <Field label="Acción de mitigación específica CRIC" value={riesgo.accion_mitigacion} highlight />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <MiniField label="Plazo" value={riesgo.plazo} />
            <MiniField label="Responsable" value={riesgo.responsable} />
            <MiniField label="Estado actual" value={riesgo.estado_actual} />
          </div>
          {riesgo.observaciones_correlacion && (
            <Field label="Correlación con riesgos técnicos" value={riesgo.observaciones_correlacion} muted />
          )}
          {riesgo.activos_relacionados_resumen?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {riesgo.activos_relacionados_resumen.map((a) => (
                <span key={a} className="rounded-md bg-base-800 px-2 py-0.5 font-mono-data text-[11px] text-cric-green-400">
                  {a}
                </span>
              ))}
            </div>
          )}
          <EvidenciaUploader modelo="riesgocontextual" objectId={riesgo.id} />
          <EnlacesAccionesPtr acciones={riesgo.acciones_ptr} />
          <HistorialPanel recurso="riesgos-contextuales" id={riesgo.id} />
        </div>
      )}
    </div>
  );
}

function Field({ icon: Icon, label, value, highlight, muted }) {
  if (!value) return null;
  return (
    <div>
      <p className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-base-300">
        {Icon && <Icon className="h-3 w-3" />}
        {label}
      </p>
      <p className={`whitespace-pre-line leading-relaxed ${
        highlight ? "text-cric-green-400" : muted ? "text-base-300/80" : "text-base-100"
      }`}>
        {value}
      </p>
    </div>
  );
}

function MiniField({ label, value }) {
  return (
    <div className="rounded-lg bg-base-850/60 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-base-300">{label}</p>
      <p className="mt-0.5 text-[13px] text-base-100">{value || "—"}</p>
    </div>
  );
}

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Plus, Pencil, Trash2, Bug, Network, Gauge, ClipboardPlus, Paperclip, FileDown } from "lucide-react";
import endpoints from "../api/endpoints";
import { apiBaseURL } from "../api/client";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { vulnerabilidadFields, riesgoActivoFields } from "../lib/entitySchemas";
import { useRiesgosTo } from "../context/PlataformaContext";
import PageHeader from "../components/PageHeader";
import NivelBadge from "../components/NivelBadge";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import ConfirmDialog from "../components/ConfirmDialog";
import GenerarAccionModal from "../components/GenerarAccionModal";
import HistorialPanel from "../components/HistorialPanel";
import EvidenciaUploader from "../components/EvidenciaUploader";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function ActivoDetalle() {
  const { id } = useParams();
  const rutaActivos = useRiesgosTo("activos");
  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const [origenAccion, setOrigenAccion] = useState(null);

  const { data: activo, loading, error, reload: reloadActivo } = useApiData(() => endpoints.activo(id), [id]);
  const { data: vulnsData, reload: reloadVulns } = useApiData(
    () => endpoints.vulnerabilidades({ activo: id, ordering: "-score", page_size: 200 }), [id]
  );
  const { data: riesgosData, reload: reloadRiesgos } = useApiData(
    () => endpoints.riesgosActivo({ activo: id, page_size: 50 }), [id]
  );

  const activoOptions = activo ? [{ value: activo.id, label: `${activo.id_activo} — ${activo.nombre}` }] : [];

  if (loading) return <PageShell><LoadingState /></PageShell>;
  if (error || !activo) return <PageShell><ErrorState /></PageShell>;

  return (
    <PageShell>
      <Link to={rutaActivos} className="mb-4 flex items-center gap-1.5 text-[12px] text-base-300 hover:text-cric-green-400">
        <ArrowLeft className="h-3.5 w-3.5" /> Volver a Activos
      </Link>

      <PageHeader
        eyebrow={activo.tipo || "Activo"}
        title={`${activo.id_activo} — ${activo.nombre}`}
        description={activo.ip_principal || "Sin IP registrada"}
        actions={
          <>
            <a
              href={`${apiBaseURL}/activos/${activo.id}/hoja-riesgo.pdf/`}
              className="flex items-center gap-1.5 rounded-lg border border-base-700/60 px-3 py-1.5 text-[12px] font-medium text-base-300 hover:border-cric-green-500/60 hover:text-cric-green-400"
              title="Descargar hoja de riesgo (PDF): vulnerabilidades, riesgos, acciones de tratamiento y evidencia de este activo"
            >
              <FileDown className="h-3.5 w-3.5" /> Hoja de riesgo (PDF)
            </a>
            <NivelBadge nivel={activo.riesgo_matriz} />
          </>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat label="Valor" value={`${activo.valor}/12`} />
        <MiniStat label="Clasificación SI" value={activo.clasificacion_si_display} />
        <MiniStat label="Cobertura" value={activo.cobertura} />
        <MiniStat label="Red Team" value={activo.afectado_red_team ? "Comprometido" : "No afectado"}
          accent={activo.afectado_red_team ? "critico" : undefined} />
      </div>

      {activo.observacion_critica && (
        <div className="mb-6 rounded-xl border border-[#e0475a]/30 bg-[#e0475a]/5 px-4 py-3 text-[13px] text-base-100">
          <span className="font-semibold text-[#e0475a]">Observación crítica: </span>
          {activo.observacion_critica}
        </div>
      )}

      <SeccionRiesgosAgregados
        activoId={id}
        activoOptions={activoOptions}
        riesgos={riesgosData?.results ?? riesgosData ?? []}
        onChanged={() => { reloadRiesgos(); reloadActivo(); }}
        guard={guard}
        onGenerarAccion={(r) => setOrigenAccion({ tipo: "riesgo_activo", objeto: r })}
      />

      <SeccionVulnerabilidades
        activoId={id}
        activoOptions={activoOptions}
        vulnerabilidades={vulnsData?.results ?? vulnsData ?? []}
        onChanged={() => { reloadVulns(); reloadActivo(); }}
        guard={guard}
        onGenerarAccion={(v) => setOrigenAccion({ tipo: "vulnerabilidad", objeto: v })}
      />

      {activo.puertos?.length > 0 && (
        <div className="mb-6 rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
          <h3 className="mb-3 flex items-center gap-2 font-display text-sm font-semibold text-base-100">
            <Network className="h-4 w-4 text-cric-green-400" /> Puertos / servicios (Nmap)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                  <th className="pb-2 pr-4 font-medium">Puerto</th>
                  <th className="pb-2 pr-4 font-medium">Servicio</th>
                  <th className="pb-2 pr-4 font-medium">Producto/Versión</th>
                  <th className="pb-2 font-medium">Observación</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {activo.puertos.map((p) => (
                  <tr key={p.id}>
                    <td className="py-2 pr-4 font-mono-data text-cric-green-400">{p.puerto}/{p.protocolo}</td>
                    <td className="py-2 pr-4 text-base-100">{p.servicio || "—"}</td>
                    <td className="py-2 pr-4 text-base-300">{p.producto_version || "—"}</td>
                    <td className="py-2 text-base-300">{p.observacion || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <HistorialPanel recurso="activos" id={id} />

      <GenerarAccionModal
        open={!!origenAccion}
        onClose={() => setOrigenAccion(null)}
        origen={origenAccion}
        onCreated={() => { reloadActivo(); }}
      />

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </PageShell>
  );
}

function SeccionRiesgosAgregados({ activoId, activoOptions, riesgos, onChanged, guard, onGenerarAccion }) {
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  async function guardar(values) {
    const payload = { ...values, activo: Number(values.activo) || Number(activoId) };
    if (editando) await endpoints.actualizarRiesgoActivo(editando.id, payload);
    else await endpoints.crearRiesgoActivo(payload);
    setFormOpen(false);
    onChanged();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarRiesgoActivo(borrando.id);
      setBorrando(null);
      onChanged();
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div className="mb-6 rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-sm font-semibold text-base-100">
          <Gauge className="h-4 w-4 text-cric-gold-400" /> Riesgo agregado del activo
        </h3>
        <button
          onClick={guard(() => { setEditando(null); setFormOpen(true); })}
          className="flex items-center gap-1 text-[12px] font-medium text-cric-green-400 hover:underline"
        >
          <Plus className="h-3.5 w-3.5" /> Nuevo riesgo
        </button>
      </div>

      {riesgos.length === 0 ? (
        <p className="text-[13px] text-base-300/70">Sin riesgo agregado registrado para este activo.</p>
      ) : (
        <div className="space-y-2">
          {riesgos.map((r) => (
            <div key={r.id} className="group flex items-center justify-between rounded-xl bg-base-850/60 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="font-mono-data text-[12px] font-semibold text-cric-gold-400">{r.id_riesgo}</span>
                <NivelBadge nivel={r.nivel_riesgo} size="sm" />
                <span className="font-mono-data text-[11px] text-base-300">P{r.probabilidad}×I{r.impacto}={r.score}</span>
                {r.responsable_sugerido && <span className="text-[12px] text-base-300">{r.responsable_sugerido}</span>}
              </div>
              <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <EvidenciaBoton modelo="riesgoactivo" objectId={r.id} etiqueta={r.id_riesgo} />
                <button onClick={guard(() => onGenerarAccion(r))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-gold-400" title="Generar acción de tratamiento">
                  <ClipboardPlus className="h-3.5 w-3.5" />
                </button>
                <button onClick={guard(() => { setEditando(r); setFormOpen(true); })} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400">
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button onClick={guard(() => setBorrando(r))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-[#e0475a]">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editando ? `Editar ${editando.id_riesgo}` : "Nuevo riesgo agregado"} width="max-w-xl">
        <EntityForm
          fields={riesgoActivoFields({ activosOptions: activoOptions })}
          initialValues={editando || { activo: Number(activoId) }}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear riesgo"}
        />
      </Modal>

      <ConfirmDialog open={!!borrando} onClose={() => setBorrando(null)} onConfirm={confirmarEliminar} loading={eliminando}
        title={`¿Eliminar ${borrando?.id_riesgo}?`} />
    </div>
  );
}

function SeccionVulnerabilidades({ activoId, activoOptions, vulnerabilidades, onChanged, guard, onGenerarAccion }) {
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  async function guardar(values) {
    const payload = {
      ...values,
      activo: Number(values.activo) || Number(activoId),
      probabilidad: values.probabilidad === "" ? null : values.probabilidad,
      impacto: values.impacto === "" ? null : values.impacto,
      cvss: values.cvss === "" ? null : values.cvss,
    };
    if (editando) await endpoints.actualizarVulnerabilidad(editando.id, payload);
    else await endpoints.crearVulnerabilidad(payload);
    setFormOpen(false);
    onChanged();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarVulnerabilidad(borrando.id);
      setBorrando(null);
      onChanged();
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div className="mb-6 rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-sm font-semibold text-base-100">
          <Bug className="h-4 w-4 text-[#e0475a]" /> Vulnerabilidades ({vulnerabilidades.length})
        </h3>
        <button
          onClick={guard(() => { setEditando(null); setFormOpen(true); })}
          className="flex items-center gap-1 text-[12px] font-medium text-cric-green-400 hover:underline"
        >
          <Plus className="h-3.5 w-3.5" /> Nueva vulnerabilidad
        </button>
      </div>

      {vulnerabilidades.length === 0 ? (
        <EmptyState label="Sin vulnerabilidades registradas para este activo." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                <th className="pb-2 pr-4 font-medium">Vulnerabilidad</th>
                <th className="pb-2 pr-4 font-medium">Severidad</th>
                <th className="pb-2 pr-4 font-medium">CVSS</th>
                <th className="pb-2 pr-4 font-medium">Riesgo</th>
                <th className="pb-2 pr-4 font-medium">Estado</th>
                <th className="pb-2 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-base-700/40">
              {vulnerabilidades.map((v) => (
                <tr key={v.id} className="group">
                  <td className="max-w-xs py-2.5 pr-4 text-base-100">{v.nombre_vulnerabilidad}</td>
                  <td className="py-2.5 pr-4 text-base-300">{v.severidad_ov_display || "—"}</td>
                  <td className="py-2.5 pr-4 font-mono-data text-base-300">{v.cvss ?? "—"}</td>
                  <td className="py-2.5 pr-4"><NivelBadge nivel={v.nivel_riesgo} size="sm" /></td>
                  <td className="py-2.5 pr-4 text-base-300">{v.estado_display}</td>
                  <td className="py-2.5">
                    <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <EvidenciaBoton modelo="vulnerabilidad" objectId={v.id} etiqueta={v.nombre_vulnerabilidad} />
                      <button onClick={guard(() => onGenerarAccion(v))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-gold-400" title="Generar acción de tratamiento">
                        <ClipboardPlus className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={guard(() => { setEditando(v); setFormOpen(true); })} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={guard(() => setBorrando(v))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-[#e0475a]">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editando ? "Editar vulnerabilidad" : "Nueva vulnerabilidad"} width="max-w-2xl">
        <EntityForm
          fields={vulnerabilidadFields({ activosOptions: activoOptions })}
          initialValues={editando || { activo: Number(activoId) }}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear vulnerabilidad"}
        />
      </Modal>

      <ConfirmDialog open={!!borrando} onClose={() => setBorrando(null)} onConfirm={confirmarEliminar} loading={eliminando}
        title="¿Eliminar esta vulnerabilidad?" />
    </div>
  );
}

function MiniStat({ label, value, accent }) {
  return (
    <div className="rounded-xl border border-base-700/60 bg-base-900/60 px-4 py-3">
      <p className="text-[11px] text-base-300">{label}</p>
      <p className={`mt-0.5 text-sm font-medium ${accent === "critico" ? "text-[#e0475a]" : "text-base-100"}`}>{value}</p>
    </div>
  );
}

/** Botón compacto de clip que abre un modal con el uploader de evidencia — para
 * filas de tabla o listas planas donde no hay espacio para un panel colapsable inline. */
function EvidenciaBoton({ modelo, objectId, etiqueta }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <>
      <button onClick={() => setAbierto(true)} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-gold-400" title="Evidencia">
        <Paperclip className="h-3.5 w-3.5" />
      </button>
      <Modal open={abierto} onClose={() => setAbierto(false)} title="Evidencia" subtitle={etiqueta} width="max-w-lg">
        <EvidenciaUploader modelo={modelo} objectId={objectId} collapsedByDefault={false} />
      </Modal>
    </>
  );
}

function PageShell({ children }) {
  return <div className="mx-auto max-w-5xl px-8 py-8">{children}</div>;
}

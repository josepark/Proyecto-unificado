import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Plus, Pencil, Trash2, ClipboardPlus, AlertTriangle } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { riesgoActivoFields } from "../lib/entitySchemas";
import { usePlataforma, rutaRiesgos } from "../context/PlataformaContext";
import PageHeader from "../components/PageHeader";
import NivelBadge from "../components/NivelBadge";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import GenerarAccionModal from "../components/GenerarAccionModal";
import ConfirmDialog from "../components/ConfirmDialog";
import HistorialPanel from "../components/HistorialPanel";
import EnlacesAccionesPtr from "../components/EnlacesAccionesPtr";
import Paginador from "../components/Paginador";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

const NIVELES = ["CRITICO", "ALTO", "MEDIO", "BAJO"];
const PAGE_SIZE = 50;

export default function RiesgosActivo() {
  const plataforma = usePlataforma();
  const enlaceActivo = (id) => rutaRiesgos(plataforma.anidado, plataforma.prefijo, `activos/${id}`);
  const paramsUrl = new URLSearchParams(window.location.search);
  const highlightId = paramsUrl.get("highlight");

  const [busqueda, setBusqueda] = useState("");
  const [nivel, setNivel] = useState("");
  const [page, setPage] = useState(1);
  const { guard, loginOpen, setLoginOpen, puedeEditar } = useAuthGuard();
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);
  const [origenAccion, setOrigenAccion] = useState(null);
  const [expandido, setExpandido] = useState(null);

  const params = {
    search: busqueda || undefined,
    nivel_riesgo: nivel || undefined,
    ordering: "-score",
    page,
    page_size: PAGE_SIZE,
  };

  const { data, loading, error, reload } = useApiData(
    () => endpoints.riesgosActivo(params),
    [busqueda, nivel, page]
  );
  const { data: activosData } = useApiData(() => endpoints.activos({ page_size: 200, ordering: "id_activo" }));
  const riesgos = data?.results ?? data ?? [];
  const activosOptions = (activosData?.results ?? activosData ?? [])
    .map((a) => ({ value: a.id, label: `${a.id_activo} — ${a.nombre}` }));

  async function guardar(values) {
    if (editando) await endpoints.actualizarRiesgoActivo(editando.id, values);
    else await endpoints.crearRiesgoActivo(values);
    setFormOpen(false);
    reload();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarRiesgoActivo(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-8 py-8">
      <PageHeader
        eyebrow="Riesgos agregados por activo"
        title="Riesgos por activo"
        description="Vista global de la matriz de riesgos técnicos (RA-XX) — complementa el detalle por activo."
        actions={puedeEditar && (
          <button
            onClick={guard(() => { setEditando(null); setFormOpen(true); })}
            className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 hover:bg-cric-green-500"
          >
            <Plus className="h-4 w-4" /> Nuevo riesgo
          </button>
        )}
      />

      <div className="mb-5 flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-base-300" />
          <input
            value={busqueda}
            onChange={(e) => { setBusqueda(e.target.value); setPage(1); }}
            placeholder="Buscar por ID de riesgo o activo…"
            className="w-full rounded-lg border border-base-700/60 bg-base-900/60 py-2 pl-9 pr-3 text-sm text-base-100 outline-none focus:border-cric-green-500"
          />
        </div>
        <select
          value={nivel}
          onChange={(e) => { setNivel(e.target.value); setPage(1); }}
          className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100"
        >
          <option value="">Todos los niveles</option>
          {NIVELES.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>

      <div className="rounded-2xl border border-base-700/60 bg-base-900/60">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState />
        ) : riesgos.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                  <th className="px-5 py-3 font-medium">ID</th>
                  <th className="px-3 py-3 font-medium">Activo</th>
                  <th className="px-3 py-3 font-medium">Score</th>
                  <th className="px-3 py-3 font-medium">Nivel</th>
                  <th className="px-3 py-3 font-medium">Estado</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {riesgos.map((r) => (
                  <Fragment key={r.id}>
                    <tr
                      id={`riesgo-${r.id}`}
                      className={`hover:bg-base-800/40 ${
                        highlightId && String(r.id) === highlightId ? "bg-cric-green-900/20 ring-1 ring-inset ring-cric-green-500/40" : ""
                      } ${(r.esta_vencido || r.por_vencer) ? "bg-[#e0475a]/5" : ""}`}
                    >
                      <td className="px-5 py-2.5 font-mono-data text-cric-gold-400">{r.id_riesgo}</td>
                      <td className="px-3 py-2.5">
                        <Link to={enlaceActivo(r.activo)} className="font-mono-data text-cric-green-400 hover:underline">
                          {r.activo_id_activo}
                        </Link>
                        <p className="text-[11px] text-base-300/70">{r.activo_nombre}</p>
                      </td>
                      <td className="px-3 py-2.5 font-mono-data text-base-300">P{r.probabilidad}×I{r.impacto}={r.score}</td>
                      <td className="px-3 py-2.5"><NivelBadge nivel={r.nivel_riesgo} size="sm" /></td>
                      <td className="px-3 py-2.5 text-base-300">{r.estado_display}</td>
                      <td className="px-5 py-2.5">
                        {puedeEditar && (
                          <div className="flex justify-end gap-1">
                            <button onClick={() => setExpandido(expandido === r.id ? null : r.id)} className="rounded p-1.5 text-base-300 hover:bg-base-800" title="Detalle">
                              {(r.esta_vencido || r.por_vencer) && <AlertTriangle className="inline h-3 w-3 text-[#e0475a] mr-1" />}
                              Detalle
                            </button>
                            <button onClick={guard(() => setOrigenAccion({ tipo: "riesgo_activo", objeto: r }))} className="rounded p-1.5 text-base-300 hover:text-cric-gold-400">
                              <ClipboardPlus className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={guard(() => { setEditando(r); setFormOpen(true); })} className="rounded p-1.5 text-base-300 hover:text-cric-green-400">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={guard(() => setBorrando(r))} className="rounded p-1.5 text-base-300 hover:text-[#e0475a]">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        )}
                        {!puedeEditar && (
                          <button onClick={() => setExpandido(expandido === r.id ? null : r.id)} className="rounded p-1.5 text-base-300 hover:bg-base-800 text-[12px]">
                            Detalle
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandido === r.id && (
                      <tr>
                        <td colSpan={6} className="bg-base-850/40 px-5 py-4 text-[12px] text-base-300">
                          <p className="whitespace-pre-line text-base-100">{r.justificacion || "—"}</p>
                          <EnlacesAccionesPtr acciones={r.acciones_ptr} />
                          <div className="mt-3">
                            <HistorialPanel recurso="riesgos-activo" id={r.id} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Paginador data={data} page={page} onPageChange={setPage} pageSize={PAGE_SIZE} />

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editando ? `Editar ${editando.id_riesgo}` : "Nuevo riesgo por activo"} width="max-w-2xl">
        <EntityForm
          fields={riesgoActivoFields({ activosOptions })}
          initialValues={editando || {}}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear riesgo"}
        />
      </Modal>

      <ConfirmDialog open={!!borrando} onClose={() => setBorrando(null)} onConfirm={confirmarEliminar} loading={eliminando}
        title={`¿Eliminar ${borrando?.id_riesgo}?`} />

      <GenerarAccionModal open={!!origenAccion} onClose={() => setOrigenAccion(null)} origen={origenAccion} onCreated={reload} />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Plus, Pencil, Trash2, ClipboardPlus, X } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { vulnerabilidadFields } from "../lib/entitySchemas";
import { TRATAMIENTO_OPTIONS, ESTADO_TRATAMIENTO_OPTIONS } from "../lib/choices";
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
import { usePlataforma, rutaRiesgos } from "../context/PlataformaContext";

const NIVELES = ["CRITICO", "ALTO", "MEDIO", "BAJO"];
const SEVERIDADES_OV = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const ESTADOS = ["PENDIENTE", "EN_PROGRESO", "CERRADO", "FALSO_POSITIVO", "ACEPTADO"];

const PAGE_SIZE = 50;

export default function Vulnerabilidades() {
  const plataforma = usePlataforma();
  const enlaceActivo = (id) => rutaRiesgos(plataforma.anidado, plataforma.prefijo, `activos/${id}`);
  const [busqueda, setBusqueda] = useState("");
  const [nivel, setNivel] = useState("");
  const [severidad, setSeveridad] = useState("");
  const [estado, setEstado] = useState("");

  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);
  const [origenAccion, setOrigenAccion] = useState(null);
  const [seleccionados, setSeleccionados] = useState(new Set());
  const [aplicandoLote, setAplicandoLote] = useState(false);
  const [page, setPage] = useState(1);

  const params = {
    search: busqueda || undefined,
    nivel_riesgo: nivel || undefined,
    severidad_ov: severidad || undefined,
    estado: estado || undefined,
    ordering: "-score",
    page,
    page_size: PAGE_SIZE,
  };

  const { data, loading, error, reload } = useApiData(
    () => endpoints.vulnerabilidades(params),
    [busqueda, nivel, severidad, estado, page]
  );
  const { data: activosData } = useApiData(() => endpoints.activos({ page_size: 200 }));

  const vulnerabilidades = data?.results ?? data ?? [];
  const activosOptions = (activosData?.results ?? activosData ?? [])
    .map((a) => ({ value: a.id, label: `${a.id_activo} — ${a.nombre}` }));

  useEffect(() => {
    setSeleccionados(new Set());
  }, [busqueda, nivel, severidad, estado]);

  function abrirCreacion() {
    setEditando(null);
    setFormOpen(true);
  }

  function abrirEdicion(v) {
    setEditando({ ...v });
    setFormOpen(true);
  }

  async function guardar(values) {
    if (editando) {
      await endpoints.actualizarVulnerabilidad(editando.id, values);
    } else {
      await endpoints.crearVulnerabilidad(values);
    }
    setFormOpen(false);
    reload();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarVulnerabilidad(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  function alternarSeleccion(id) {
    setSeleccionados((prev) => {
      const nuevo = new Set(prev);
      if (nuevo.has(id)) nuevo.delete(id); else nuevo.add(id);
      return nuevo;
    });
  }

  function alternarSeleccionTodos() {
    setSeleccionados((prev) =>
      prev.size === vulnerabilidades.length ? new Set() : new Set(vulnerabilidades.map((v) => v.id))
    );
  }

  async function aplicarEnLote(campo, valor) {
    if (!valor || seleccionados.size === 0) return;
    setAplicandoLote(true);
    try {
      await endpoints.bulkActualizarVulnerabilidades([...seleccionados], { [campo]: valor });
      setSeleccionados(new Set());
      reload();
    } finally {
      setAplicandoLote(false);
    }
  }

  const totalCriticas = vulnerabilidades.filter((v) => v.nivel_riesgo === "CRITICO").length;

  return (
    <div className="mx-auto max-w-7xl px-8 py-8">
      <PageHeader
        eyebrow="Hallazgos técnicos"
        title="Vulnerabilidades"
        description={`${vulnerabilidades.length} hallazgo(s)${totalCriticas ? ` · ${totalCriticas} crítico(s)` : ""} — de los 38 activos, sin tener que entrar uno por uno.`}
        actions={
          <button
            onClick={guard(abrirCreacion)}
            className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
          >
            <Plus className="h-4 w-4" /> Nueva vulnerabilidad
          </button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-base-300" />
          <input
            value={busqueda}
            onChange={(e) => { setBusqueda(e.target.value); setPage(1); }}
            placeholder="Buscar por nombre, CVE, o activo…"
            className="w-full rounded-lg border border-base-700/60 bg-base-900/60 py-2 pl-9 pr-3 text-sm text-base-100 placeholder:text-base-300/60 outline-none focus:border-cric-green-500"
          />
        </div>

        <select value={nivel} onChange={(e) => { setNivel(e.target.value); setPage(1); }}
          className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500">
          <option value="">Todos los niveles</option>
          {NIVELES.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>

        <select value={severidad} onChange={(e) => { setSeveridad(e.target.value); setPage(1); }}
          className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500">
          <option value="">Toda severidad OV</option>
          {SEVERIDADES_OV.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={estado} onChange={(e) => { setEstado(e.target.value); setPage(1); }}
          className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500">
          <option value="">Todo estado</option>
          {ESTADOS.map((e) => <option key={e} value={e}>{e.replace("_", " ")}</option>)}
        </select>
      </div>

      {seleccionados.size > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-cric-green-500/40 bg-cric-green-900/20 px-4 py-2.5">
          <span className="text-[13px] font-medium text-cric-green-400">
            {seleccionados.size} seleccionada{seleccionados.size > 1 ? "s" : ""}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-base-300">Cambiar estado a:</span>
            <select
              disabled={aplicandoLote}
              defaultValue=""
              onChange={(e) => { aplicarEnLote("estado", e.target.value); e.target.value = ""; }}
              className="rounded-lg border border-base-700/60 bg-base-900/60 px-2.5 py-1.5 text-[12px] text-base-100 outline-none focus:border-cric-green-500 disabled:opacity-50"
            >
              <option value="" disabled>elegir…</option>
              {ESTADO_TRATAMIENTO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-base-300">Cambiar tratamiento a:</span>
            <select
              disabled={aplicandoLote}
              defaultValue=""
              onChange={(e) => { aplicarEnLote("tratamiento", e.target.value); e.target.value = ""; }}
              className="rounded-lg border border-base-700/60 bg-base-900/60 px-2.5 py-1.5 text-[12px] text-base-100 outline-none focus:border-cric-green-500 disabled:opacity-50"
            >
              <option value="" disabled>elegir…</option>
              {TRATAMIENTO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <button
            onClick={() => setSeleccionados(new Set())}
            className="ml-auto flex items-center gap-1 text-[12px] text-base-300 hover:text-base-100"
          >
            <X className="h-3.5 w-3.5" /> Quitar selección
          </button>
        </div>
      )}

      <div className="rounded-2xl border border-base-700/60 bg-base-900/60">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState />
        ) : vulnerabilidades.length === 0 ? (
          <EmptyState label="Ninguna vulnerabilidad coincide con los filtros seleccionados." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                  <th className="px-5 py-3 font-medium">
                    <input
                      type="checkbox"
                      checked={seleccionados.size > 0 && seleccionados.size === vulnerabilidades.length}
                      onChange={alternarSeleccionTodos}
                      className="h-3.5 w-3.5 rounded border-base-600 accent-cric-green-500"
                    />
                  </th>
                  <th className="px-3 py-3 font-medium">Activo</th>
                  <th className="px-3 py-3 font-medium">Hallazgo</th>
                  <th className="px-3 py-3 font-medium">Severidad OV</th>
                  <th className="px-3 py-3 font-medium">Score</th>
                  <th className="px-3 py-3 font-medium">Nivel</th>
                  <th className="px-3 py-3 font-medium">Estado</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {vulnerabilidades.map((v) => (
                  <tr key={v.id} className={`group hover:bg-base-800/40 ${seleccionados.has(v.id) ? "bg-cric-green-900/10" : ""}`}>
                    <td className="px-5 py-2.5">
                      <input
                        type="checkbox"
                        checked={seleccionados.has(v.id)}
                        onChange={() => alternarSeleccion(v.id)}
                        className="h-3.5 w-3.5 rounded border-base-600 accent-cric-green-500"
                      />
                    </td>
                    <td className="px-3 py-2.5">
                      <Link to={enlaceActivo(v.activo)} className="font-mono-data text-cric-green-400 hover:underline">
                        {v.activo_id_activo}
                      </Link>
                      <p className="text-[11px] text-base-300/70">{v.activo_nombre}</p>
                    </td>
                    <td className="px-3 py-2.5 max-w-md text-base-100">{v.nombre_vulnerabilidad}</td>
                    <td className="px-3 py-2.5 text-base-300">{v.severidad_ov_display || "—"}</td>
                    <td className="px-3 py-2.5 font-mono-data text-base-300">
                      {v.probabilidad && v.impacto ? `${v.probabilidad}×${v.impacto}=${v.score}` : "—"}
                    </td>
                    <td className="px-3 py-2.5"><NivelBadge nivel={v.nivel_riesgo} size="sm" /></td>
                    <td className="px-3 py-2.5 text-base-300">{v.estado_display}</td>
                    <td className="px-5 py-2.5">
                      <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button onClick={guard(() => setOrigenAccion({ tipo: "vulnerabilidad", objeto: v }))}
                          className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-gold-400" title="Generar acción de tratamiento">
                          <ClipboardPlus className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={guard(() => abrirEdicion(v))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400" title="Editar">
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={guard(() => setBorrando(v))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-[#e0475a]" title="Eliminar">
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
      </div>

      <Paginador data={data} page={page} onPageChange={setPage} pageSize={PAGE_SIZE} />

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editando ? "Editar hallazgo" : "Nueva vulnerabilidad"}
        width="max-w-2xl"
      >
        <EntityForm
          fields={vulnerabilidadFields({ activosOptions })}
          initialValues={editando || {}}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear vulnerabilidad"}
        />
        {editando && (
          <div className="mt-4 space-y-3 border-t border-base-700/60 pt-4">
            <EnlacesAccionesPtr acciones={editando.acciones_ptr} />
            <HistorialPanel recurso="vulnerabilidades" id={editando.id} collapsedByDefault={false} />
          </div>
        )}
      </Modal>

      <GenerarAccionModal
        open={!!origenAccion}
        onClose={() => setOrigenAccion(null)}
        origen={origenAccion}
        onCreated={reload}
      />

      <ConfirmDialog
        open={!!borrando}
        onClose={() => setBorrando(null)}
        onConfirm={confirmarEliminar}
        loading={eliminando}
        title="¿Eliminar esta vulnerabilidad?"
        description="Esta acción no se puede deshacer."
      />

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

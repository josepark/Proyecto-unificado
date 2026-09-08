import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, ShieldOff, Radar as RadarIcon, Plus, Pencil, Trash2 } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { activoFields } from "../lib/entitySchemas";
import PageHeader from "../components/PageHeader";
import NivelBadge from "../components/NivelBadge";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import ConfirmDialog from "../components/ConfirmDialog";
import Paginador from "../components/Paginador";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { usePlataforma, rutaRiesgos } from "../context/PlataformaContext";

const NIVELES = ["CRITICO", "ALTO", "MEDIO", "BAJO"];
const PAGE_SIZE = 50;

export default function Activos() {
  const plataforma = usePlataforma();
  const enlaceActivo = (id) => rutaRiesgos(plataforma.anidado, plataforma.prefijo, `activos/${id}`);
  const [busqueda, setBusqueda] = useState("");
  const [nivel, setNivel] = useState("");
  const [soloSinCobertura, setSoloSinCobertura] = useState(false);
  const [soloRedTeam, setSoloRedTeam] = useState(false);

  const { guard, loginOpen, setLoginOpen, puedeEditar } = useAuthGuard();
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null); // null = creando
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  const params = {
    search: busqueda || undefined,
    riesgo_matriz: nivel || undefined,
    cobertura: soloSinCobertura ? "SIN_COBERTURA" : undefined,
    afectado_red_team: soloRedTeam ? true : undefined,
    ordering: "-valor",
    page,
    page_size: PAGE_SIZE,
  };

  const { data, loading, error, reload } = useApiData(
    () => endpoints.activos(params),
    [busqueda, nivel, soloSinCobertura, soloRedTeam, page]
  );
  const { data: campanasData } = useApiData(() => endpoints.campanasRedTeam());

  const activos = data?.results ?? data ?? [];
  const campanasOptions = (campanasData?.results ?? campanasData ?? []).map((c) => ({ value: c.id, label: c.nombre }));

  function abrirCreacion() {
    setEditando(null);
    setFormOpen(true);
  }

  async function abrirEdicion(activoFila) {
    // La fila de la tabla usa un serializer "ligero" (sin todos los campos); se pide
    // el detalle completo para no perder datos que el formulario no vería y sobrescribiría.
    const { data: detalle } = await endpoints.activo(activoFila.id);
    setEditando({ ...detalle, campana_red_team_id: detalle.campana_red_team?.id ?? "" });
    setFormOpen(true);
  }

  async function guardar(values) {
    if (editando) {
      await endpoints.actualizarActivo(editando.id, values);
    } else {
      await endpoints.crearActivo(values);
    }
    setFormOpen(false);
    reload();
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarActivo(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-8 py-8">
      <PageHeader
        eyebrow="Inventario técnico"
        title="Activos"
        description="Correlación Matriz de Activos × OpenVAS × Nmap × Red Team."
        actions={puedeEditar && (
          <button
            onClick={guard(abrirCreacion)}
            className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
          >
            <Plus className="h-4 w-4" /> Nuevo activo
          </button>
        )}
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-base-300" />
          <input
            value={busqueda}
            onChange={(e) => { setBusqueda(e.target.value); setPage(1); }}
            placeholder="Buscar por ID, nombre o IP…"
            className="w-full rounded-lg border border-base-700/60 bg-base-900/60 py-2 pl-9 pr-3 text-sm text-base-100 placeholder:text-base-300/60 outline-none focus:border-cric-green-500"
          />
        </div>

        <select
          value={nivel}
          onChange={(e) => { setNivel(e.target.value); setPage(1); }}
          className="rounded-lg border border-base-700/60 bg-base-900/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500"
        >
          <option value="">Todos los niveles</option>
          {NIVELES.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>

        <ToggleChip active={soloSinCobertura} onClick={() => { setSoloSinCobertura((v) => !v); setPage(1); }} icon={ShieldOff} label="Sin cobertura" />
        <ToggleChip active={soloRedTeam} onClick={() => { setSoloRedTeam((v) => !v); setPage(1); }} icon={RadarIcon} label="Comprometidos (Red Team)" />
      </div>

      <div className="rounded-2xl border border-base-700/60 bg-base-900/60">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState />
        ) : activos.length === 0 ? (
          <EmptyState label="Ningún activo coincide con los filtros seleccionados." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                  <th className="px-5 py-3 font-medium">ID</th>
                  <th className="px-3 py-3 font-medium">Nombre</th>
                  <th className="px-3 py-3 font-medium">Tipo</th>
                  <th className="px-3 py-3 font-medium">IP</th>
                  <th className="px-3 py-3 font-medium">Valor</th>
                  <th className="px-3 py-3 font-medium">Cobertura</th>
                  <th className="px-3 py-3 font-medium">Vulns.</th>
                  <th className="px-3 py-3 font-medium">Red Team</th>
                  <th className="px-3 py-3 font-medium">Riesgo</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-base-700/40">
                {activos.map((a) => (
                  <tr key={a.id} className="group hover:bg-base-800/40">
                    <td className="px-5 py-2.5">
                      <Link to={enlaceActivo(a.id)} className="font-mono-data text-cric-green-400 hover:underline">
                        {a.id_activo}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5 text-base-100">{a.nombre}</td>
                    <td className="px-3 py-2.5 text-base-300">{a.tipo || "—"}</td>
                    <td className="px-3 py-2.5 font-mono-data text-base-300">{a.ip_principal || "—"}</td>
                    <td className="px-3 py-2.5 font-mono-data text-base-300">{a.valor}/12</td>
                    <td className="px-3 py-2.5"><CoberturaTag cobertura={a.cobertura} label={a.cobertura_display} /></td>
                    <td className="px-3 py-2.5">
                      <span className="font-mono-data text-base-300">{a.total_vulnerabilidades}</span>
                      {a.vulnerabilidades_criticas > 0 && (
                        <span className="ml-1.5 font-mono-data text-[11px] text-[#e0475a]">({a.vulnerabilidades_criticas} crít.)</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {a.afectado_red_team ? (
                        <span className="text-[11px] font-medium text-[#e0475a]">{a.campana_red_team_nombre}</span>
                      ) : (
                        <span className="text-base-300/50">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5"><NivelBadge nivel={a.riesgo_matriz} size="sm" /></td>
                    <td className="px-5 py-2.5">
                      {puedeEditar && (
                        <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <button onClick={guard(() => abrirEdicion(a))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400" title="Editar">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={guard(() => setBorrando(a))} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-[#e0475a]" title="Eliminar">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
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
        title={editando ? `Editar ${editando.id_activo}` : "Nuevo activo"}
        width="max-w-2xl"
      >
        <EntityForm
          fields={activoFields({ campanasOptions })}
          initialValues={editando || {}}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear activo"}
        />
      </Modal>

      <ConfirmDialog
        open={!!borrando}
        onClose={() => setBorrando(null)}
        onConfirm={confirmarEliminar}
        loading={eliminando}
        title={`¿Eliminar ${borrando?.id_activo}?`}
        description="Se eliminarán también sus vulnerabilidades, puertos y riesgos asociados. Esta acción no se puede deshacer."
      />

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

function ToggleChip({ active, onClick, icon: Icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[13px] font-medium transition-colors ${
        active
          ? "border-cric-green-500/60 bg-cric-green-600/20 text-cric-green-400"
          : "border-base-700/60 bg-base-900/60 text-base-300 hover:text-base-100"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function CoberturaTag({ cobertura, label }) {
  const styles = {
    COMPLETA: "text-cric-green-400",
    PARCIAL: "text-cric-gold-400",
    SIN_COBERTURA: "text-[#e0475a]",
  };
  return <span className={`text-[12px] ${styles[cobertura] || "text-base-300"}`}>{label}</span>;
}

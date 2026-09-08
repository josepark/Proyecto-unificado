import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ChevronDown } from "lucide-react";
import endpoints from "../api/endpoints";
import { usePlataforma, rutaRiesgos } from "../context/PlataformaContext";
import { rutaPlanTratamiento } from "../lib/rutasOrigen";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import PageHeader from "../components/PageHeader";
import LoginModal from "../components/LoginModal";
import { LoadingState, ErrorState } from "../components/StatusStates";

const CATEGORIA_ORDEN = ["ORGANIZACIONAL", "PERSONAS", "FISICO", "TECNOLOGICO"];

const ESTADO_IMPL_OPTIONS = [
  { value: "NO_IMPLEMENTADO", label: "No implementado" },
  { value: "PARCIAL", label: "Implementación parcial" },
  { value: "IMPLEMENTADO", label: "Implementado" },
  { value: "NO_APLICA", label: "No aplica" },
];

const ESTADO_IMPL_COLOR = {
  NO_IMPLEMENTADO: "text-[#e0475a]",
  PARCIAL: "text-[#e0b559]",
  IMPLEMENTADO: "text-[#4bab7c]",
  NO_APLICA: "text-base-300",
};

function ordenNatural(codigo) {
  return codigo.split(".").map(Number);
}

function compararCodigos(a, b) {
  const pa = ordenNatural(a.codigo);
  const pb = ordenNatural(b.codigo);
  return pa[0] - pb[0] || pa[1] - pb[1];
}

export default function Cumplimiento() {
  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const { data: resumen, loading: loadingResumen, error, reload: reloadResumen } = useApiData(() => endpoints.cumplimientoResumen());
  const { data: controlesData, reload: reloadControles } = useApiData(() => endpoints.controlesIso({ page_size: 100 }));
  const controles = [...(controlesData?.results ?? controlesData ?? [])].sort(compararCodigos);
  const detallePorControl = Object.fromEntries(
    (resumen?.controles_con_detalle ?? []).map((c) => [c.id, c])
  );
  const controlesConDetalle = controles.map((c) => ({ ...c, _detalle: detallePorControl[c.id] }));

  const [categoriaFiltro, setCategoriaFiltro] = useState("");
  const controlesFiltrados = categoriaFiltro
    ? controlesConDetalle.filter((c) => c.categoria === categoriaFiltro)
    : controlesConDetalle;

  async function actualizarControl(id, cambios) {
    await endpoints.actualizarControlIso(id, cambios);
    reloadControles();
    reloadResumen();
  }

  if (loadingResumen) return <PageShell><LoadingState /></PageShell>;
  if (error || !resumen) return <PageShell><ErrorState /></PageShell>;

  return (
    <PageShell>
      <PageHeader
        eyebrow="ISO/IEC 27001:2022 · Anexo A"
        title="Cumplimiento"
        description="Cobertura real del catálogo de 93 controles: un control 'con evidencia' tiene al menos una acción de tratamiento o riesgo contextual vinculado en el sistema."
      />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-5">
        <div className="rounded-2xl border border-cric-green-600/40 bg-cric-green-600/10 p-5 sm:col-span-1">
          <p className="text-[11px] font-medium text-base-300">Cobertura global</p>
          <p className="mt-2 font-display text-3xl font-semibold text-cric-green-400">
            {resumen.porcentaje_cobertura_global}%
          </p>
          <p className="mt-1 text-[11px] text-base-300">
            {resumen.total_con_evidencia} de {resumen.total_aplicables} aplicables
          </p>
        </div>
        {resumen.por_categoria.map((cat) => (
          <div key={cat.categoria} className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
            <p className="text-[11px] font-medium text-base-300">{cat.categoria_display}</p>
            <p className="mt-2 font-display text-2xl font-semibold text-base-100">{cat.porcentaje_cobertura}%</p>
            <p className="mt-1 text-[11px] text-base-300">{cat.con_evidencia} / {cat.aplicables} aplicables</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-base-800">
              <div className="h-full rounded-full bg-cric-green-500" style={{ width: `${cat.porcentaje_cobertura}%` }} />
            </div>
          </div>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FiltroChip active={categoriaFiltro === ""} onClick={() => setCategoriaFiltro("")} label="Todas" />
        {CATEGORIA_ORDEN.map((cat) => (
          <FiltroChip
            key={cat}
            active={categoriaFiltro === cat}
            onClick={() => setCategoriaFiltro(cat)}
            label={resumen.por_categoria.find((c) => c.categoria === cat)?.categoria_display || cat}
          />
        ))}
      </div>

      <div className="overflow-hidden rounded-2xl border border-base-700/60 bg-base-900/60">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
              <th className="px-5 py-3 font-medium">Control</th>
              <th className="px-3 py-3 font-medium">Aplicable</th>
              <th className="px-3 py-3 font-medium">Estado de implementación</th>
              <th className="px-3 py-3 font-medium">Evidencia</th>
              <th className="px-5 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-base-700/40">
            {controlesFiltrados.map((c) => (
              <ControlRow key={c.id} control={c} guard={guard} onGuardar={actualizarControl} />
            ))}
          </tbody>
        </table>
      </div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </PageShell>
  );
}

function ControlRow({ control, guard, onGuardar }) {
  const [abierto, setAbierto] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const evidencias = control.acciones_count + control.riesgos_contextuales_count;

  async function cambiar(campo, valor) {
    setGuardando(true);
    try {
      await onGuardar(control.id, { [campo]: valor });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <tr className="hover:bg-base-800/40">
        <td className="px-5 py-2.5">
          <span className="font-mono-data text-cric-gold-400">{control.codigo}</span>
          <span className="ml-2 text-base-100">{control.nombre}</span>
        </td>
        <td className="px-3 py-2.5">
          <input
            type="checkbox"
            checked={control.aplicable}
            disabled={guardando}
            onChange={guard((e) => cambiar("aplicable", e.target.checked))}
            className="h-4 w-4 rounded border-base-600 bg-base-850 accent-cric-green-500"
          />
        </td>
        <td className="px-3 py-2.5">
          <select
            value={control.estado_implementacion}
            disabled={guardando}
            onChange={guard((e) => cambiar("estado_implementacion", e.target.value))}
            className={`rounded-md border border-base-700/60 bg-base-850/60 px-2 py-1 text-[12px] outline-none ${ESTADO_IMPL_COLOR[control.estado_implementacion]}`}
          >
            {ESTADO_IMPL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-base-900 text-base-100">{opt.label}</option>
            ))}
          </select>
        </td>
        <td className="px-3 py-2.5">
          {evidencias > 0 ? (
            <span className="rounded-full bg-cric-green-600/15 px-2 py-0.5 text-[11px] font-medium text-cric-green-400">
              {evidencias} vínculo{evidencias !== 1 ? "s" : ""}
            </span>
          ) : (
            <span className="rounded-full bg-[#e0475a]/15 px-2 py-0.5 text-[11px] font-medium text-[#e0475a]">
              Sin evidencia
            </span>
          )}
        </td>
        <td className="px-5 py-2.5 text-right">
          <button onClick={() => setAbierto((v) => !v)} className="text-base-300 hover:text-base-100">
            <ChevronDown className={`h-4 w-4 transition-transform ${abierto ? "rotate-180" : ""}`} />
          </button>
        </td>
      </tr>
      {abierto && (
        <tr>
          <td colSpan={5} className="bg-base-850/40 px-5 py-3">
            <ControlDetalle control={control} />
          </td>
        </tr>
      )}
    </>
  );
}

function ControlDetalle({ control }) {
  const plataforma = usePlataforma();
  const detalle = control._detalle;

  return (
    <div className="text-[12px] text-base-300">
      <p>
        <span className="font-medium text-base-100">Justificación de aplicabilidad: </span>
        {control.justificacion_aplicabilidad || "—"}
      </p>
      {control.politica_referencia && (
        <p className="mt-1">
          <span className="font-medium text-base-100">Política asociada: </span>
          <span className="font-mono-data">{control.politica_referencia}</span>
        </p>
      )}
      {control.observaciones && (
        <p className="mt-1">
          <span className="font-medium text-base-100">Observaciones: </span>
          {control.observaciones}
        </p>
      )}
      <p className="mt-1 text-base-300/70">
        Vincule este control desde una acción de tratamiento (Plan de tratamiento) o un riesgo contextual — el
        campo "Controles ISO 27001 (Anexo A)" en sus formularios.
      </p>
      {detalle && (detalle.acciones?.length > 0 || detalle.riesgos_contextuales?.length > 0) && (
        <div className="mt-3 space-y-2">
          {detalle.acciones?.length > 0 && (
            <div>
              <p className="mb-1 font-medium text-base-100">Acciones PTR vinculadas</p>
              <div className="flex flex-wrap gap-1.5">
                {detalle.acciones.map((a) => (
                  <Link
                    key={a.id}
                    to={rutaPlanTratamiento(plataforma.anidado, plataforma.prefijo, { planId: a.plan_id, accionId: a.id })}
                    className="rounded-md bg-base-800 px-2 py-0.5 font-mono-data text-[11px] text-cric-gold-400 hover:underline"
                  >
                    {a.id_riesgo} · {a.plan_referencia}
                  </Link>
                ))}
              </div>
            </div>
          )}
          {detalle.riesgos_contextuales?.length > 0 && (
            <div>
              <p className="mb-1 font-medium text-base-100">Riesgos contextuales vinculados</p>
              <div className="flex flex-wrap gap-1.5">
                {detalle.riesgos_contextuales.map((r) => (
                  <Link
                    key={r.id}
                    to={rutaRiesgos(plataforma.anidado, plataforma.prefijo, `riesgos-contextuales?highlight=${r.id}`)}
                    className="rounded-md bg-base-800 px-2 py-0.5 font-mono-data text-[11px] text-cric-green-400 hover:underline"
                  >
                    {r.id_riesgo_contextual}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FiltroChip({ active, onClick, label }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors ${
        active
          ? "border-cric-green-500/60 bg-cric-green-600/20 text-cric-green-400"
          : "border-base-700/60 bg-base-900/60 text-base-300 hover:text-base-100"
      }`}
    >
      {label}
    </button>
  );
}

function PageShell({ children }) {
  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <div className="mb-2 flex items-center gap-2 text-cric-green-400">
        <ShieldCheck className="h-4 w-4" />
      </div>
      {children}
    </div>
  );
}

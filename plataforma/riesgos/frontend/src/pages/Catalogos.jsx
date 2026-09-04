import { useState } from "react";
import { ListChecks, Plus, Trash2, RotateCcw } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import PageHeader from "../components/PageHeader";
import LoginModal from "../components/LoginModal";
import { LoadingState, ErrorState } from "../components/StatusStates";

const CATEGORIAS = [
  { value: "TIPO_ACTIVO", label: "Tipo de activo", usadoEn: "Activos → Tipo" },
  { value: "RESPONSABLE_RIESGO", label: "Responsable sugerido (riesgo)", usadoEn: "Riesgos por activo → Responsable sugerido" },
  { value: "RESPONSABLE_ACCION", label: "Responsable (acción)", usadoEn: "Plan de tratamiento → Responsable" },
  { value: "FUENTE_HALLAZGO", label: "Fuente del hallazgo", usadoEn: "Plan de tratamiento → Fuente" },
  { value: "PLAZO_ACCION", label: "Plazo (acción)", usadoEn: "Plan de tratamiento → Plazo" },
];

export default function Catalogos() {
  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const [categoriaActiva, setCategoriaActiva] = useState(CATEGORIAS[0].value);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Configuración"
        title="Catálogos de valores"
        description="Las listas que alimentan los combos de Tipo, Responsable, Fuente y Plazo en los formularios — agrega o desactiva valores aquí para que se sugieran en toda la aplicación, sin depender de escribirlos cada vez."
      />

      <div className="mb-5 flex flex-wrap gap-2">
        {CATEGORIAS.map((c) => (
          <button
            key={c.value}
            onClick={() => setCategoriaActiva(c.value)}
            className={`rounded-lg px-3 py-1.5 text-[12px] font-medium transition-colors ${
              categoriaActiva === c.value
                ? "bg-cric-green-600 text-white"
                : "bg-base-850/60 text-base-300 hover:bg-base-800"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <PanelCategoria
        categoria={CATEGORIAS.find((c) => c.value === categoriaActiva)}
        guard={guard}
      />

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </PageShell>
  );
}

function PanelCategoria({ categoria, guard }) {
  const { data, loading, error, reload } = useApiData(
    () => endpoints.catalogoTodos(categoria.value), [categoria.value]
  );
  const [nuevoValor, setNuevoValor] = useState("");
  const [guardando, setGuardando] = useState(false);

  const valores = data?.results ?? data ?? [];
  const activos = valores.filter((v) => v.activo);
  const desactivados = valores.filter((v) => !v.activo);

  async function agregar(e) {
    e.preventDefault();
    const limpio = nuevoValor.trim();
    if (!limpio) return;
    setGuardando(true);
    try {
      await endpoints.catalogoObtenerOCrear(categoria.value, limpio);
      setNuevoValor("");
      reload();
    } finally {
      setGuardando(false);
    }
  }

  async function alternarActivo(valor) {
    await endpoints.catalogoActualizar(valor.id, { activo: !valor.activo });
    reload();
  }

  if (loading) return <LoadingState label="Cargando catálogo…" />;
  if (error) return <ErrorState />;

  return (
    <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
      <p className="mb-4 text-[12px] text-base-300">
        Usado en: <span className="text-base-100">{categoria.usadoEn}</span> · {activos.length} valor(es) activo(s)
      </p>

      <form onSubmit={guard(agregar)} className="mb-5 flex gap-2">
        <input
          value={nuevoValor}
          onChange={(e) => setNuevoValor(e.target.value)}
          placeholder="Agregar un valor nuevo…"
          className="flex-1 rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500"
        />
        <button
          type="submit"
          disabled={guardando || !nuevoValor.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3 py-2 text-[12px] font-medium text-white hover:bg-cric-green-500 disabled:opacity-50"
        >
          <Plus className="h-3.5 w-3.5" /> Agregar
        </button>
      </form>

      {activos.length === 0 && (
        <p className="py-4 text-center text-[12px] text-base-300/70">Sin valores activos todavía.</p>
      )}

      <ul className="space-y-1.5">
        {activos.map((v) => (
          <li key={v.id} className="flex items-center justify-between rounded-lg bg-base-850/60 px-3 py-2">
            <span className="text-[13px] text-base-100">{v.valor}</span>
            <button
              onClick={guard(() => alternarActivo(v))}
              title="Desactivar (deja de sugerirse, no borra lo ya usado)"
              className="rounded p-1 text-base-300 hover:bg-base-800 hover:text-[#e0475a]"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </li>
        ))}
      </ul>

      {desactivados.length > 0 && (
        <>
          <p className="mb-2 mt-5 text-[11px] font-medium uppercase tracking-wide text-base-300/70">
            Desactivados ({desactivados.length})
          </p>
          <ul className="space-y-1.5">
            {desactivados.map((v) => (
              <li key={v.id} className="flex items-center justify-between rounded-lg bg-base-850/30 px-3 py-2 opacity-70">
                <span className="text-[13px] text-base-300 line-through">{v.valor}</span>
                <button
                  onClick={guard(() => alternarActivo(v))}
                  title="Reactivar"
                  className="rounded p-1 text-base-300 hover:bg-base-800 hover:text-cric-green-400"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function PageShell({ children }) {
  return <div className="mx-auto max-w-3xl px-8 py-8">{children}</div>;
}

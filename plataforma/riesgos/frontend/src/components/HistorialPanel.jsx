import { useState } from "react";
import { History, ChevronDown, User } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";

const CAMPO_LABELS = {
  estado: "Estado", porcentaje_avance: "% Avance", nivel_riesgo: "Nivel de riesgo",
  riesgo_matriz: "Riesgo (matriz)", probabilidad: "Probabilidad", impacto: "Impacto",
  observacion_critica: "Observación crítica", responsable: "Responsable",
  responsable_sugerido: "Responsable sugerido", fase: "Fase", tratamiento: "Tratamiento",
};

function etiquetaCampo(campo) {
  return CAMPO_LABELS[campo] || campo.replace(/_/g, " ");
}

function formatearFecha(iso) {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

/** recurso ∈ activos | vulnerabilidades | riesgos-activo | riesgos-contextuales |
 *  campanas-red-team | planes-tratamiento | acciones-tratamiento */
export default function HistorialPanel({ recurso, id, collapsedByDefault = true }) {
  const [abierto, setAbierto] = useState(!collapsedByDefault);
  const { data, loading } = useApiData(
    () => (abierto ? endpoints.historial(recurso, id) : Promise.resolve({ data: null })),
    [recurso, id, abierto]
  );

  return (
    <div className="rounded-xl border border-base-700/60 bg-base-850/40">
      <button
        onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left"
      >
        <span className="flex items-center gap-2 text-[12px] font-medium text-base-300">
          <History className="h-3.5 w-3.5" /> Historial de cambios
        </span>
        <ChevronDown className={`h-3.5 w-3.5 text-base-300 transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      {abierto && (
        <div className="border-t border-base-700/60 px-4 py-3">
          {loading || !data ? (
            <p className="text-[12px] text-base-300/70">Cargando…</p>
          ) : data.length === 0 ? (
            <p className="text-[12px] text-base-300/70">Sin cambios registrados aún.</p>
          ) : (
            <ul className="space-y-3">
              {data.map((entrada, i) => (
                <li key={i} className="border-l-2 border-cric-green-600/40 pl-3">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-base-300">
                    <span className="font-medium text-base-100">{entrada.tipo}</span>
                    <span>·</span>
                    <span className="flex items-center gap-1"><User className="h-3 w-3" />{entrada.usuario}</span>
                    <span>·</span>
                    <span className="font-mono-data">{formatearFecha(entrada.fecha)}</span>
                  </div>
                  {entrada.cambios.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {entrada.cambios.map((c, j) => (
                        <li key={j} className="text-[12px] text-base-300">
                          <span className="text-base-100">{etiquetaCampo(c.campo)}</span>
                          {": "}
                          <span className="text-[#e0475a] line-through decoration-1">{c.antes || "(vacío)"}</span>
                          {" → "}
                          <span className="text-cric-green-400">{c.despues || "(vacío)"}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

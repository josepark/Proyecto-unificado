function nivelDeScore(score) {
  if (score >= 20) return "CRITICO";
  if (score >= 12) return "ALTO";
  if (score >= 6) return "MEDIO";
  return "BAJO";
}

const NIVEL_BG = {
  CRITICO: "bg-[#e0475a]",
  ALTO: "bg-[#e0812f]",
  MEDIO: "bg-[#e0b559]",
  BAJO: "bg-[#4bab7c]",
};

export default function RiskHeatmap({ cells = [] }) {
  const lookup = new Map(cells.map((c) => [`${c.probabilidad}-${c.impacto}`, c.total]));
  const probabilidades = [5, 4, 3, 2, 1]; // fila superior = más probable
  const impactos = [1, 2, 3, 4, 5];
  const maxTotal = Math.max(1, ...cells.map((c) => c.total));

  return (
    <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <h3 className="font-display text-sm font-semibold text-base-100">
          Mapa de calor · Probabilidad × Impacto
        </h3>
        <span className="text-[11px] text-base-300">ISO/IEC 27005</span>
      </div>

      <div className="flex gap-2">
        <div className="flex flex-col justify-between py-1 text-[11px] text-base-300">
          <span className="rotate-0">Prob.</span>
        </div>
        <div className="flex-1">
          <div className="grid grid-cols-5 gap-1.5">
            {probabilidades.map((p) =>
              impactos.map((i) => {
                const total = lookup.get(`${p}-${i}`) || 0;
                const score = p * i;
                const nivel = nivelDeScore(score);
                const intensity = total === 0 ? 0.18 : 0.35 + 0.65 * (total / maxTotal);
                return (
                  <div
                    key={`${p}-${i}`}
                    className={`group relative flex aspect-square flex-col items-center justify-center rounded-lg ${NIVEL_BG[nivel]} transition-transform hover:scale-[1.04]`}
                    style={{ opacity: intensity }}
                    title={`Probabilidad ${p} × Impacto ${i} = ${score} · ${total} hallazgo(s)`}
                  >
                    <span className="font-mono-data text-sm font-bold text-base-950">
                      {total > 0 ? total : ""}
                    </span>
                    <span className="absolute bottom-0.5 right-1 font-mono-data text-[9px] text-base-950/60">
                      {score}
                    </span>
                  </div>
                );
              })
            )}
          </div>
          <div className="mt-2 grid grid-cols-5 gap-1.5 text-center text-[11px] text-base-300">
            {impactos.map((i) => (
              <span key={i}>{i}</span>
            ))}
          </div>
          <p className="mt-1 text-center text-[11px] text-base-300">Impacto</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-base-700/60 pt-3 text-[11px] text-base-300">
        {[
          ["CRITICO", "Crítico ≥20"],
          ["ALTO", "Alto 12–19"],
          ["MEDIO", "Medio 6–11"],
          ["BAJO", "Bajo 1–5"],
        ].map(([key, label]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-sm ${NIVEL_BG[key]}`} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

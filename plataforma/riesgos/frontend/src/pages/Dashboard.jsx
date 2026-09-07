import { Link } from "react-router-dom";
import {
  ServerCog, ShieldAlert, Bug, ClipboardCheck, Radar, ArrowUpRight, AlertTriangle,
} from "lucide-react";
import endpoints from "../api/endpoints";
import { useRiesgosTo } from "../context/PlataformaContext";
import { useApiData } from "../lib/useApiData";
import PageHeader from "../components/PageHeader";
import KpiCard from "../components/KpiCard";
import RiskHeatmap from "../components/RiskHeatmap";
import NivelBadge from "../components/NivelBadge";
import { LoadingState, ErrorState } from "../components/StatusStates";

export default function Dashboard() {
  const rutaRedTeam = useRiesgosTo("red-team");
  const rutaActivos = useRiesgosTo("activos");
  const rutaPlan = useRiesgosTo("plan-tratamiento");
  const { data, loading, error } = useApiData(() => endpoints.dashboard());
  const { data: alertas } = useApiData(() => endpoints.alertasResumen());

  if (loading) return <PageShell><LoadingState label="Calculando panel de riesgos…" /></PageShell>;
  if (error || !data) {
    const detalle =
      error?.response?.data?.detail
      || (error?.message && !error.message.includes("Network Error") ? error.message : null);
    return <PageShell><ErrorState detail={detalle} /></PageShell>;
  }

  const { kpis, heatmap_probabilidad_impacto, campanas_red_team, activos_criticos_top } = data;
  const avancePtr = kpis.acciones_total > 0
    ? Math.round((kpis.acciones_cerradas / kpis.acciones_total) * 100)
    : 0;

  return (
    <PageShell>
      <PageHeader
        eyebrow="SUIIN / CRIC "
        title="Panel general de riesgos"
        description="Vista consolidada de activos, hallazgos técnicos, campañas de Red Team y avance del plan de tratamiento."
      />

      {alertas && (alertas.total_vencidas > 0 || alertas.total_por_vencer > 0) && (
        <AlertaVencimientos alertas={alertas} rutaPlan={rutaPlan} />
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="Activos inventariados" value={kpis.total_activos} icon={ServerCog}
          sub={`${kpis.activos_sin_cobertura} sin cobertura de escaneo`} accent="green" />
        <KpiCard label="Vulnerabilidades" value={kpis.total_vulnerabilidades} icon={Bug}
          sub={`${kpis.vulnerabilidades_criticas} críticas (OpenVAS)`} accent="critico" />
        <KpiCard label="Activos comprometidos" value={kpis.activos_comprometidos} icon={Radar}
          sub="Confirmado por Red Team" accent="alto" />
        <KpiCard label="Avance plan de tratamiento" value={`${avancePtr}%`} icon={ClipboardCheck}
          sub={`${kpis.acciones_cerradas} de ${kpis.acciones_total} acciones cerradas`} accent="gold" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <RiskHeatmap cells={heatmap_probabilidad_impacto} />
        </div>

        <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold text-base-100">Campañas Red Team</h3>
            <Link to={rutaRedTeam} className="flex items-center gap-1 text-[11px] text-cric-green-400 hover:underline">
              Ver detalle <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {campanas_red_team.map((c) => (
              <div key={c.nombre} className="rounded-xl border border-base-700/60 bg-base-850/60 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-mono-data text-[13px] font-semibold text-base-100">{c.nombre}</p>
                  <span className="flex items-center gap-1.5 text-[11px] font-medium text-[#e0475a]">
                    <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-[#e0475a]" />
                    Comprometido
                  </span>
                </div>
                <p className="mt-0.5 font-mono-data text-[11px] text-base-300">{c.host_ip} · {c.num_activos} activo(s)</p>
                <div className="mt-3 flex gap-2 text-[11px]">
                  <span className="rounded bg-[#e0475a]/15 px-1.5 py-0.5 text-[#e0475a]">C {c.riesgos_criticos}</span>
                  <span className="rounded bg-[#e0812f]/15 px-1.5 py-0.5 text-[#e0812f]">A {c.riesgos_altos}</span>
                  <span className="rounded bg-[#e0b559]/15 px-1.5 py-0.5 text-[#e0b559]">M {c.riesgos_medios}</span>
                  <span className="rounded bg-[#4bab7c]/15 px-1.5 py-0.5 text-[#4bab7c]">B {c.riesgos_bajos}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-base-700/60 bg-base-900/60 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-sm font-semibold text-base-100">Activos en riesgo crítico</h3>
          <Link to={rutaActivos} className="flex items-center gap-1 text-[11px] text-cric-green-400 hover:underline">
            Ver todos los activos <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-base-700/60 text-[11px] uppercase tracking-wide text-base-300">
                <th className="pb-2 pr-4 font-medium">ID</th>
                <th className="pb-2 pr-4 font-medium">Activo</th>
                <th className="pb-2 pr-4 font-medium">Tipo</th>
                <th className="pb-2 pr-4 font-medium">Valor</th>
                <th className="pb-2 pr-4 font-medium">Vulns. críticas</th>
                <th className="pb-2 font-medium">Nivel</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-base-700/40">
              {activos_criticos_top.map((a) => (
                <tr key={a.id} className="hover:bg-base-800/40">
                  <td className="py-2.5 pr-4 font-mono-data text-cric-green-400">{a.id_activo}</td>
                  <td className="py-2.5 pr-4 text-base-100">{a.nombre}</td>
                  <td className="py-2.5 pr-4 text-base-300">{a.tipo || "—"}</td>
                  <td className="py-2.5 pr-4 font-mono-data text-base-300">{a.valor}/12</td>
                  <td className="py-2.5 pr-4">
                    {a.vulnerabilidades_criticas > 0 ? (
                      <span className="font-mono-data text-[#e0475a]">{a.vulnerabilidades_criticas}</span>
                    ) : (
                      <span className="text-base-300/60">0</span>
                    )}
                  </td>
                  <td className="py-2.5"><NivelBadge nivel={a.riesgo_matriz} size="sm" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageShell>
  );
}

function AlertaVencimientos({ alertas, rutaPlan }) {
  const items = [
    ...alertas.acciones_vencidas.map((a) => ({ ...a, tipo: "accion", vencida: true })),
    ...alertas.riesgos_activo_vencidos.map((r) => ({ ...r, tipo: "riesgo", vencida: true })),
    ...(alertas.riesgos_contextuales_vencidos ?? []).map((r) => (
      { ...r, id_riesgo: r.id_riesgo_contextual, tipo: "contextual", vencida: true })),
    ...alertas.acciones_por_vencer.map((a) => ({ ...a, tipo: "accion", vencida: false })),
    ...alertas.riesgos_activo_por_vencer.map((r) => ({ ...r, tipo: "riesgo", vencida: false })),
    ...(alertas.riesgos_contextuales_por_vencer ?? []).map((r) => (
      { ...r, id_riesgo: r.id_riesgo_contextual, tipo: "contextual", vencida: false })),
  ];

  return (
    <div className="mb-5 rounded-2xl border border-[#e0475a]/30 bg-[#e0475a]/5 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-sm font-semibold text-base-100">
          <AlertTriangle className="h-4 w-4 text-[#e0475a]" />
          Vencimientos
          <span className="font-mono-data text-xs font-normal text-base-300">
            ({alertas.total_vencidas} vencido{alertas.total_vencidas !== 1 ? "s" : ""}, {alertas.total_por_vencer} por vencer)
          </span>
        </h3>
        <Link to={rutaPlan} className="flex items-center gap-1 text-[11px] text-cric-green-400 hover:underline">
          Ir al plan de tratamiento <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {items.slice(0, 6).map((item, i) => (
          <div key={i} className={`flex items-center justify-between rounded-lg px-3 py-2 text-[12px] ${
            item.vencida ? "bg-[#e0475a]/10" : "bg-[#e0b559]/10"
          }`}>
            <span className="font-mono-data font-medium text-base-100">
              {item.id_riesgo} <span className="text-base-300/70">· {item.tipo === "accion" ? "acción" : item.tipo === "contextual" ? "riesgo contextual" : "riesgo"}</span>
            </span>
            <span className={item.vencida ? "text-[#e0475a]" : "text-[#e0b559]"}>
              {item.vencida ? `venció hace ${Math.abs(item.dias_para_vencer)} d.` : `vence en ${item.dias_para_vencer} d.`}
            </span>
          </div>
        ))}
      </div>
      {items.length > 6 && (
        <p className="mt-2 text-[11px] text-base-300">y {items.length - 6} más…</p>
      )}
    </div>
  );
}

function PageShell({ children }) {
  return <div className="mx-auto max-w-7xl px-8 py-8">{children}</div>;
}

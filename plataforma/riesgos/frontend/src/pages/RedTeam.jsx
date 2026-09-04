import { useState } from "react";
import { Server, Zap, FileWarning, Bug, Fingerprint, Plus, Pencil } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import { campanaRedTeamFields } from "../lib/entitySchemas";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import LoginModal from "../components/LoginModal";
import EntityForm from "../components/EntityForm";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function RedTeam() {
  const { data, loading, error, reload } = useApiData(() => endpoints.campanasRedTeam());
  const campanas = data?.results ?? data ?? [];

  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const [formOpen, setFormOpen] = useState(false);
  const [editando, setEditando] = useState(null);

  async function guardar(values) {
    if (editando) await endpoints.actualizarCampanaRedTeam(editando.id, values);
    else await endpoints.crearCampanaRedTeam(values);
    setFormOpen(false);
    reload();
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <PageHeader
        eyebrow="MITRE CALDERA · OpenVAS · OWASP ZAP · Nuclei · NMAP"
        title="Campañas Red Team"
        description="Detalle técnico de cada engagement: compromiso confirmado, agentes implantados, servidores C2 y datos exfiltrados."
        actions={
          <button
            onClick={guard(() => { setEditando(null); setFormOpen(true); })}
            className="flex items-center gap-1.5 rounded-lg bg-cric-green-600 px-3.5 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
          >
            <Plus className="h-4 w-4" /> Nueva campaña
          </button>
        }
      />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState />
      ) : campanas.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-5">
          {campanas.map((c) => (
            <CampanaCard key={c.id} campana={c} onEditar={guard(() => { setEditando(c); setFormOpen(true); })} />
          ))}
        </div>
      )}

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editando ? `Editar ${editando.nombre}` : "Nueva campaña Red Team"} width="max-w-2xl">
        <EntityForm
          fields={campanaRedTeamFields()}
          initialValues={editando || {}}
          onSubmit={guardar}
          onCancel={() => setFormOpen(false)}
          submitLabel={editando ? "Guardar cambios" : "Crear campaña"}
        />
      </Modal>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

function CampanaCard({ campana, onEditar }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#e0475a]/25 bg-base-900/60">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-base-700/60 bg-base-850/60 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e0475a]/15">
            <Server className="h-4 w-4 text-[#e0475a]" />
          </span>
          <div>
            <p className="font-mono-data text-sm font-semibold text-base-100">{campana.nombre}</p>
            <p className="font-mono-data text-[11px] text-base-300">
              {campana.host_ip}
              {campana.fecha_inicio && ` · ${campana.fecha_inicio}${campana.fecha_fin && campana.fecha_fin !== campana.fecha_inicio ? ` – ${campana.fecha_fin}` : ""}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-[#e0475a]/40 bg-[#e0475a]/15 px-3 py-1 text-[11px] font-medium text-[#e0475a]">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-[#e0475a]" />
            {campana.estado_compromiso_display}
          </span>
          <button onClick={onEditar} className="rounded p-1.5 text-base-300 hover:bg-base-800 hover:text-cric-green-400" title="Editar">
            <Pencil className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="px-5 pt-4">
        <p className="text-[11px] font-medium uppercase tracking-wide text-base-300/70">
          Al momento de la campaña (foto congelada, no se actualiza sola)
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 p-5 pt-2 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Riesgos críticos" value={campana.riesgos_criticos} color="text-[#e0475a]" />
        <Stat label="Riesgos altos" value={campana.riesgos_altos} color="text-[#e0812f]" />
        <Stat label="Riesgos medios" value={campana.riesgos_medios} color="text-[#e0b559]" />
        <Stat label="Riesgos bajos" value={campana.riesgos_bajos} color="text-[#4bab7c]" />
      </div>

      {campana.riesgos_actuales_por_nivel && (
        <div className="px-5 pb-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-cric-green-400">
            Ahora mismo, entre los activos vinculados a esta campaña
          </p>
        </div>
      )}
      {campana.riesgos_actuales_por_nivel && (
        <div className="grid grid-cols-1 gap-4 px-5 pb-5 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Riesgos críticos" value={campana.riesgos_actuales_por_nivel.CRITICO} color="text-[#e0475a]" />
          <Stat label="Riesgos altos" value={campana.riesgos_actuales_por_nivel.ALTO} color="text-[#e0812f]" />
          <Stat label="Riesgos medios" value={campana.riesgos_actuales_por_nivel.MEDIO} color="text-[#e0b559]" />
          <Stat label="Riesgos bajos" value={campana.riesgos_actuales_por_nivel.BAJO} color="text-[#4bab7c]" />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 border-t border-base-700/60 p-5 md:grid-cols-2">
        <DetailBlock icon={Zap} label="Estado UFW" value={campana.estado_ufw} />
        <DetailBlock icon={Fingerprint} label="Uptime sin reinicio" value={campana.uptime_sin_reinicio} />
        <DetailBlock icon={Bug} label="Agentes implantados" value={campana.agentes_implantados} />
        <DetailBlock icon={Server} label="Servidor(es) C2" value={campana.servidores_c2} mono />
        <DetailBlock icon={FileWarning} label="Datos exfiltrados" value={campana.datos_exfiltrados} full highlight />
        {campana.puertos_no_documentados && (
          <DetailBlock icon={Server} label="Puertos no documentados" value={campana.puertos_no_documentados} full mono />
        )}
      </div>

      {campana.tecnicas_mitre_count != null && (
        <div className="border-t border-base-700/60 px-5 py-3 text-[12px] text-base-300">
          <span className="font-mono-data text-cric-gold-400">{campana.tecnicas_mitre_count}</span> técnicas MITRE ATT&CK identificadas
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="rounded-xl bg-base-850/60 p-3 text-center">
      <p className={`font-mono-data text-xl font-bold ${color}`}>{value}</p>
      <p className="mt-0.5 text-[11px] text-base-300">{label}</p>
    </div>
  );
}

function DetailBlock({ icon: Icon, label, value, full, mono, highlight }) {
  if (!value) return null;
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <p className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-base-300">
        <Icon className="h-3 w-3" />
        {label}
      </p>
      <p className={`whitespace-pre-line text-[13px] leading-relaxed ${mono ? "font-mono-data" : ""} ${
        highlight ? "text-[#e0475a]" : "text-base-100"
      }`}>
        {value}
      </p>
    </div>
  );
}

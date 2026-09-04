import { Loader2, AlertTriangle, Inbox } from "lucide-react";

export function LoadingState({ label = "Cargando datos…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-base-300">
      <Loader2 className="h-6 w-6 animate-spin text-cric-green-400" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({ message = "No fue posible cargar los datos." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-[#e0475a]/30 bg-[#e0475a]/5 py-16 text-center">
      <AlertTriangle className="h-6 w-6 text-[#e0475a]" />
      <p className="max-w-md text-sm text-base-300">{message}</p>
      <p className="text-xs text-base-300/70">
        Verifique que el backend Django esté corriendo en <code className="font-mono-data">localhost:8000</code>.
      </p>
    </div>
  );
}

export function EmptyState({ label = "No hay registros para mostrar." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-base-300/70">
      <Inbox className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

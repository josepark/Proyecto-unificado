import { AlertTriangle } from "lucide-react";
import Modal from "./Modal";

export default function ConfirmDialog({ open, onClose, onConfirm, title = "¿Eliminar este registro?", description, loading }) {
  return (
    <Modal open={open} onClose={onClose} title={title} width="max-w-sm">
      <div className="flex gap-3">
        <AlertTriangle className="h-5 w-5 shrink-0 text-[#e0475a]" />
        <p className="text-[13px] leading-relaxed text-base-300">
          {description || "Esta acción no se puede deshacer."}
        </p>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-base-300 hover:text-base-100">
          Cancelar
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="rounded-lg bg-[#e0475a] px-4 py-2 text-sm font-medium text-base-100 transition-colors hover:bg-[#c93d4e] disabled:opacity-60"
        >
          {loading ? "Eliminando…" : "Eliminar"}
        </button>
      </div>
    </Modal>
  );
}

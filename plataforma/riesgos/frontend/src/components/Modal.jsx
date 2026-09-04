import { useEffect } from "react";
import { X } from "lucide-react";

export default function Modal({ open, onClose, title, subtitle, children, width = "max-w-lg" }) {
  useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-base-950/70 px-4 py-10 backdrop-blur-sm">
      <div className={`w-full ${width} rounded-2xl border border-base-700/60 bg-base-900 shadow-2xl`}>
        <div className="flex items-start justify-between border-b border-base-700/60 px-5 py-4">
          <div>
            <h2 className="font-display text-base font-semibold text-base-100">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[12px] text-base-300">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-base-300 transition-colors hover:bg-base-800 hover:text-base-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[75vh] overflow-y-auto px-5 py-5">{children}</div>
      </div>
    </div>
  );
}

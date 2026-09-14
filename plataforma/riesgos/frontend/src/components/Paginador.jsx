import { ChevronLeft, ChevronRight } from "lucide-react";

/** Paginador para respuestas DRF paginadas { count, next, previous, results }. */
export default function Paginador({ data, page, onPageChange, pageSize = 50 }) {
  if (!data || data.count == null) return null;
  const total = data.count;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) {
    return (
      <p className="mt-3 text-[11px] text-base-300">
        {total} registro{total !== 1 ? "s" : ""}
      </p>
    );
  }

  return (
    <div className="mt-4 flex items-center justify-between text-[12px] text-base-300">
      <p>
        Página {page} de {totalPages} · {total} registro{total !== 1 ? "s" : ""}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="flex items-center gap-1 rounded-lg border border-base-700/60 px-2.5 py-1.5 disabled:opacity-40 hover:bg-base-800"
        >
          <ChevronLeft className="h-3.5 w-3.5" /> Anterior
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="flex items-center gap-1 rounded-lg border border-base-700/60 px-2.5 py-1.5 disabled:opacity-40 hover:bg-base-800"
        >
          Siguiente <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

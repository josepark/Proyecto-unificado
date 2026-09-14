import { useState, useRef } from "react";
import { Paperclip, ChevronDown, Upload, Trash2, FileText, Image as ImageIcon, File, Loader2 } from "lucide-react";
import endpoints from "../api/endpoints";
import { useApiData } from "../lib/useApiData";
import { useAuthGuard } from "../lib/useAuthGuard";
import LoginModal from "./LoginModal";
import ConfirmDialog from "./ConfirmDialog";

const ICONO_POR_TIPO = { IMAGEN: ImageIcon, PDF: FileText, DOCUMENTO: File, OTRO: File };
const EXTENSIONES_ACEPTADAS = ".jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx";

function formatearTamano(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** modelo ∈ activo | vulnerabilidad | riesgoactivo | riesgocontextual | acciontratamiento */
export default function EvidenciaUploader({ modelo, objectId, collapsedByDefault = true }) {
  const [abierto, setAbierto] = useState(!collapsedByDefault);
  const { guard, loginOpen, setLoginOpen } = useAuthGuard();
  const inputRef = useRef(null);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState(null);
  const [borrando, setBorrando] = useState(null);
  const [eliminando, setEliminando] = useState(false);

  const { data, loading, reload } = useApiData(
    () => (abierto ? endpoints.evidencias(modelo, objectId) : Promise.resolve({ data: null })),
    [modelo, objectId, abierto]
  );
  const evidencias = data?.results ?? data ?? [];

  async function subirArchivo(archivo) {
    setSubiendo(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("modelo", modelo);
      formData.append("object_id", objectId);
      formData.append("archivo", archivo);
      await endpoints.subirEvidencia(formData);
      reload();
    } catch (err) {
      const data = err?.response?.data;
      const msg = data?.archivo?.[0] || data?.detail || "No se pudo subir el archivo.";
      setError(msg);
    } finally {
      setSubiendo(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function confirmarEliminar() {
    setEliminando(true);
    try {
      await endpoints.eliminarEvidencia(borrando.id);
      setBorrando(null);
      reload();
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div className="rounded-xl border border-base-700/60 bg-base-850/40">
      <button
        onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-left"
      >
        <span className="flex items-center gap-2 text-[12px] font-medium text-base-300">
          <Paperclip className="h-3.5 w-3.5" />
          Evidencia {evidencias.length > 0 && `(${evidencias.length})`}
        </span>
        <ChevronDown className={`h-3.5 w-3.5 text-base-300 transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      {abierto && (
        <div className="border-t border-base-700/60 px-4 py-3">
          {loading ? (
            <p className="text-[12px] text-base-300/70">Cargando…</p>
          ) : evidencias.length === 0 ? (
            <p className="mb-3 text-[12px] text-base-300/70">Sin evidencia adjunta aún.</p>
          ) : (
            <ul className="mb-3 space-y-1.5">
              {evidencias.map((ev) => {
                const Icono = ICONO_POR_TIPO[ev.tipo_archivo] || File;
                return (
                  <li key={ev.id} className="flex items-center justify-between gap-2 rounded-lg bg-base-900/60 px-3 py-2">
                    <a
                      href={ev.archivo_url} target="_blank" rel="noreferrer"
                      className="flex min-w-0 items-center gap-2 text-[12px] text-base-100 hover:text-cric-green-400"
                    >
                      <Icono className="h-3.5 w-3.5 shrink-0 text-cric-green-400" />
                      <span className="truncate">{ev.nombre_original}</span>
                      <span className="shrink-0 font-mono-data text-[10px] text-base-300">{formatearTamano(ev.tamano_bytes)}</span>
                    </a>
                    <button
                      onClick={guard(() => setBorrando(ev))}
                      className="shrink-0 rounded p-1 text-base-300 hover:bg-base-800 hover:text-[#e0475a]"
                      title="Eliminar"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <label
            className={`flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed px-3 py-2 text-[12px] font-medium transition-colors ${
              subiendo ? "border-base-600 text-base-300" : "border-base-600 text-base-300 hover:border-cric-green-500/60 hover:text-cric-green-400"
            }`}
          >
            {subiendo ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
            {subiendo ? "Subiendo…" : "Adjuntar foto, PDF o documento (máx. 10 MB)"}
            <input
              ref={inputRef}
              type="file"
              accept={EXTENSIONES_ACEPTADAS}
              disabled={subiendo}
              className="hidden"
              onChange={guard((e) => {
                const archivo = e.target.files?.[0];
                if (archivo) subirArchivo(archivo);
              })}
            />
          </label>
          {error && <p className="mt-2 text-[11px] text-[#e0475a]">{error}</p>}
        </div>
      )}

      <ConfirmDialog
        open={!!borrando}
        onClose={() => setBorrando(null)}
        onConfirm={confirmarEliminar}
        loading={eliminando}
        title="¿Eliminar esta evidencia?"
        description={borrando ? `Se eliminará "${borrando.nombre_original}" permanentemente.` : ""}
      />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

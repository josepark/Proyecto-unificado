import { useState } from "react";
import { FileSpreadsheet, Upload, CheckCircle2, AlertTriangle } from "lucide-react";
import endpoints from "../api/endpoints";
import { useAuthGuard } from "../lib/useAuthGuard";
import PageHeader from "../components/PageHeader";
import LoginModal from "../components/LoginModal";

export default function ImportarExcel() {
  const { guard, loginOpen, setLoginOpen, isAuthenticated } = useAuthGuard();
  const [matriz, setMatriz] = useState(null);
  const [ptrFiles, setPtrFiles] = useState([]);
  const [forzar, setForzar] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  async function enviar(e) {
    e.preventDefault();
    if (!matriz && ptrFiles.length === 0) {
      setError("Seleccione al menos un archivo Excel.");
      return;
    }
    setCargando(true);
    setError(null);
    setResultado(null);
    try {
      const fd = new FormData();
      if (matriz) fd.append("matriz_riesgos", matriz);
      ptrFiles.forEach((f) => fd.append("ptr", f));
      if (forzar) fd.append("forzar_sobrescritura", "true");
      const res = await endpoints.importarExcel(fd);
      setResultado(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Error al importar");
      if (err.response?.data) setResultado(err.response.data);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-8 py-8">
      <PageHeader
        eyebrow="Carga inicial / actualización masiva"
        title="Importar desde Excel"
        description="Equivalente a manage.py importar_matrices — idempotente y con protección de registros editados manualmente."
      />

      <form onSubmit={guard(enviar)} className="space-y-5 rounded-2xl border border-base-700/60 bg-base-900/60 p-6">
        <CampoArchivo
          label="Matriz de riesgos (.xlsx)"
          hint="SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS — activos, vulnerabilidades, riesgos."
          onChange={setMatriz}
          file={matriz}
        />
        <CampoArchivo
          label="Plan de tratamiento (.xlsx)"
          hint="Puede seleccionar varios PTR. SUIIN_SGSI_*_PlanTratamiento_de_Riesgos."
          multiple
          onChange={(files) => setPtrFiles([...files])}
          count={ptrFiles.length}
        />

        <label className="flex items-start gap-2 text-[13px] text-base-300">
          <input
            type="checkbox"
            checked={forzar}
            onChange={(e) => setForzar(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded accent-cric-green-500"
          />
          <span>
            <strong className="text-base-100">Forzar sobrescritura</strong> — sobrescribe también registros
            editados manualmente desde la última importación (use con precaución).
          </span>
        </label>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-[#e0475a]/40 bg-[#e0475a]/10 px-3 py-2 text-[13px] text-[#e0475a]">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {resultado?.ok && (
          <div className="flex items-start gap-2 rounded-lg border border-cric-green-500/40 bg-cric-green-600/10 px-3 py-2 text-[13px] text-cric-green-400">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            Importación completada
            {resultado.matriz_riesgos ? " · matriz cargada" : ""}
            {resultado.ptr_importados ? ` · ${resultado.ptr_importados} PTR` : ""}
          </div>
        )}

        <button
          type="submit"
          disabled={!isAuthenticated || cargando}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-cric-green-600 py-2.5 text-[13px] font-medium text-base-100 hover:bg-cric-green-500 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          {cargando ? "Importando…" : "Importar archivos"}
        </button>
      </form>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

function CampoArchivo({ label, hint, onChange, file, count = 0, multiple = false }) {
  return (
    <div>
      <label className="mb-2 flex items-center gap-2 text-[13px] font-medium text-base-100">
        <FileSpreadsheet className="h-4 w-4 text-cric-green-400" />
        {label}
      </label>
      <input
        type="file"
        accept=".xlsx,.xls"
        multiple={multiple}
        onChange={(e) => onChange(multiple ? [...e.target.files] : e.target.files[0])}
        className="block w-full text-[12px] text-base-300 file:mr-3 file:rounded-lg file:border-0 file:bg-base-800 file:px-3 file:py-2 file:text-base-100"
      />
      {file && !multiple && <p className="mt-1 text-[11px] text-base-300">{file.name}</p>}
      {multiple && count > 0 && <p className="mt-1 text-[11px] text-base-300">{count} archivo(s) seleccionado(s)</p>}
      <p className="mt-1 text-[11px] text-base-300/70">{hint}</p>
    </div>
  );
}

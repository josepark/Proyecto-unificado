import { useEffect, useRef, useState } from "react";
import { X, Search } from "lucide-react";
import endpoints from "../api/endpoints";

/**
 * Selector de técnicas MITRE ATT&CK respaldado por el catálogo real
 * sincronizado desde el Inventario (712 técnicas/tácticas/subtécnicas). El
 * campo real del formulario sigue siendo texto libre con un separador fijo
 * (ej. "T1190/T1498") — este componente solo arma y desarma esa cadena.
 *
 * No obliga a que todo venga del catálogo: algunos campos (ej.
 * AccionTratamiento.tecnica_mitre_cwe) también llevan códigos CWE, que son
 * un catálogo aparte — cualquier texto que se escriba y no coincida con el
 * catálogo MITRE se agrega igual, como una "ficha" más.
 */
export default function MitreMultiSelect({ value, onChange, separador = "/", placeholder }) {
  const codigos = (value ?? "").split(separador).map((c) => c.trim()).filter(Boolean);
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const contenedorRef = useRef(null);

  useEffect(() => {
    if (!busqueda.trim()) {
      setResultados([]);
      return;
    }
    let cancelado = false;
    const temporizador = setTimeout(() => {
      endpoints.tecnicasMitre(busqueda).then((res) => {
        if (!cancelado) setResultados(res.data.results ?? res.data ?? []);
      });
    }, 200);
    return () => {
      cancelado = true;
      clearTimeout(temporizador);
    };
  }, [busqueda]);

  useEffect(() => {
    function alHacerClicFuera(e) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) setAbierto(false);
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    return () => document.removeEventListener("mousedown", alHacerClicFuera);
  }, []);

  function agregar(codigo) {
    const limpio = codigo.trim();
    if (!limpio || codigos.some((c) => c.toLowerCase() === limpio.toLowerCase())) return;
    onChange([...codigos, limpio].join(separador));
    setBusqueda("");
    setResultados([]);
  }

  function quitar(codigo) {
    onChange(codigos.filter((c) => c !== codigo).join(separador));
  }

  return (
    <div ref={contenedorRef} className="relative">
      {codigos.length > 0 && (
        <div className="mb-1.5 flex flex-wrap gap-1.5">
          {codigos.map((c) => (
            <span
              key={c}
              className="flex items-center gap-1 rounded-md bg-cric-green-900/40 px-2 py-0.5 font-mono-data text-[11px] text-cric-green-300"
            >
              {c}
              <button type="button" onClick={() => quitar(c)} className="hover:text-white">
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-base-300" />
        <input
          type="text"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          onFocus={() => setAbierto(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              agregar(busqueda);
            }
          }}
          placeholder={placeholder || "Buscar por código o nombre (ej. T1190, sniffing)…"}
          className="w-full rounded-lg border border-base-700/60 bg-base-850/60 py-2 pl-8 pr-3 text-sm text-base-100 outline-none focus:border-cric-green-500"
        />
      </div>

      {abierto && busqueda.trim() && (
        <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-base-700/60 bg-base-900 shadow-lg">
          {resultados.map((r) => (
            <button
              key={r.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                agregar(r.codigo);
              }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-base-800"
            >
              <span className="font-mono-data text-[11px] text-cric-gold-400">{r.codigo}</span>
              <span className="truncate text-[12px] text-base-100">{r.nombre}</span>
              <span className="ml-auto shrink-0 text-[10px] text-base-300/70">{r.tipo_display}</span>
            </button>
          ))}
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault();
              agregar(busqueda);
            }}
            className="block w-full border-t border-base-700/60 px-3 py-1.5 text-left text-[12px] text-cric-green-400 hover:bg-base-800"
          >
            + Agregar "{busqueda.trim()}" tal cual (ej. un código CWE)
          </button>
        </div>
      )}
    </div>
  );
}

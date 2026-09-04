import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import endpoints from "../api/endpoints";

/**
 * Combo respaldado por CatalogoValor: sugiere los valores ya usados para esa
 * categoría (ej. "Tipo de activo"), pero nunca bloquea escribir uno nuevo — al
 * salir del campo, si el texto no coincide con nada existente, se registra
 * solo en el catálogo (vía obtener-o-crear) para que aparezca sugerido la
 * próxima vez. El campo real del formulario sigue siendo texto libre; esto
 * es solo una ayuda para no volver a escribir lo mismo cien veces.
 */
export default function CatalogoCombobox({ categoria, value, onChange, placeholder, multiline }) {
  const [opciones, setOpciones] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(true);
  const contenedorRef = useRef(null);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    endpoints
      .catalogo(categoria)
      .then((res) => {
        if (!cancelado) setOpciones(res.data.results ?? res.data ?? []);
      })
      .finally(() => !cancelado && setCargando(false));
    return () => {
      cancelado = true;
    };
  }, [categoria]);

  useEffect(() => {
    function alHacerClicFuera(e) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    return () => document.removeEventListener("mousedown", alHacerClicFuera);
  }, []);

  const texto = value ?? "";
  const filtradas = texto
    ? opciones.filter((o) => o.valor.toLowerCase().includes(texto.toLowerCase()))
    : opciones;
  const coincideExacto = opciones.some((o) => o.valor.toLowerCase() === texto.trim().toLowerCase());

  async function registrarSiEsNuevo() {
    const limpio = texto.trim();
    if (!limpio || coincideExacto) return;
    try {
      const res = await endpoints.catalogoObtenerOCrear(categoria, limpio);
      setOpciones((prev) => (prev.some((o) => o.id === res.data.id) ? prev : [...prev, res.data]));
    } catch {
      // Si falla (ej. sin sesión), no pasa nada grave — el valor igual queda
      // guardado en el campo del formulario, solo no se agrega al catálogo.
    }
  }

  return (
    <div ref={contenedorRef} className="relative">
      <div className="relative">
        {multiline ? (
          <textarea
            value={texto}
            placeholder={placeholder}
            rows={5}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setAbierto(true)}
            onBlur={registrarSiEsNuevo}
            className="w-full resize-y rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 pr-8 text-sm text-base-100 outline-none focus:border-cric-green-500"
          />
        ) : (
          <input
            type="text"
            value={texto}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setAbierto(true)}
            onBlur={registrarSiEsNuevo}
            className="w-full rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 pr-8 text-sm text-base-100 outline-none focus:border-cric-green-500"
          />
        )}
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setAbierto((v) => !v)}
          className={`absolute right-2 text-base-300 hover:text-base-100 ${multiline ? "top-3" : "top-1/2 -translate-y-1/2"}`}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
      </div>

      {abierto && (
        <div className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-base-700/60 bg-base-900 shadow-lg">
          {cargando && <p className="px-3 py-2 text-[12px] text-base-300/70">Cargando…</p>}
          {!cargando && filtradas.length === 0 && (
            <p className="px-3 py-2 text-[12px] text-base-300/70">Sin coincidencias — se guardará como valor nuevo.</p>
          )}
          {filtradas.map((o) => (
            <button
              key={o.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(o.valor);
                setAbierto(false);
              }}
              className="block w-full px-3 py-1.5 text-left text-[13px] text-base-100 hover:bg-base-800"
            >
              {multiline && o.valor.length > 140 ? `${o.valor.slice(0, 140)}…` : o.valor}
            </button>
          ))}
          {texto.trim() && !coincideExacto && (
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                setAbierto(false);
              }}
              className="block w-full border-t border-base-700/60 px-3 py-1.5 text-left text-[13px] text-cric-green-400 hover:bg-base-800"
            >
              + Usar "{multiline && texto.trim().length > 80 ? `${texto.trim().slice(0, 80)}…` : texto.trim()}" (nuevo)
            </button>
          )}
        </div>
      )}
    </div>
  );
}

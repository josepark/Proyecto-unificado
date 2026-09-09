import { useEffect, useId, useMemo, useRef, useState } from 'react';

function codigoDeItem(item) {
  return (item.codigo || item.id || '').toUpperCase();
}

/** Campo de códigos separados (coma o «/») con autocompletado desde un catálogo. */
export function CampoCodigosCatalogo({
  label,
  value,
  onChange,
  items = [],
  cargando = false,
  errorCatalogo = null,
  placeholder = '',
  filtrarItem = null,
  maxSugerencias = 12,
  separador = ',',
}) {
  const id = useId();
  const contenedorRef = useRef(null);
  const [enfocado, setEnfocado] = useState(false);
  const [indiceActivo, setIndiceActivo] = useState(0);
  const esSlash = separador === '/';

  const { completos, incompleto } = useMemo(() => {
    const partes = (value || '').split(separador).map((s) => s.trim());
    return {
      completos: partes.slice(0, -1).filter(Boolean).map((c) => c.toUpperCase()),
      incompleto: (partes[partes.length - 1] || '').trim(),
    };
  }, [value, separador]);

  const sugerencias = useMemo(() => {
    const busqueda = incompleto.toUpperCase();
    if (!enfocado || busqueda.length < 1) return [];

    let lista = items;
    if (filtrarItem) lista = lista.filter(filtrarItem);

    const yaElegidos = new Set(completos);

    const filtradas = lista.filter((item) => {
      const codigo = codigoDeItem(item);
      if (!codigo) return false;
      if (yaElegidos.has(codigo)) return false;
      if (codigo.startsWith(busqueda)) return true;
      const nombre = (item.nombre || item.descripcion || '').toLowerCase();
      return nombre.includes(busqueda.toLowerCase());
    });

    return filtradas.slice(0, maxSugerencias);
  }, [items, incompleto, enfocado, filtrarItem, maxSugerencias, completos]);

  useEffect(() => {
    setIndiceActivo(0);
  }, [incompleto, sugerencias.length]);

  useEffect(() => {
    function cerrarSiClickFuera(ev) {
      if (contenedorRef.current && !contenedorRef.current.contains(ev.target)) {
        setEnfocado(false);
      }
    }
    document.addEventListener('mousedown', cerrarSiClickFuera);
    return () => document.removeEventListener('mousedown', cerrarSiClickFuera);
  }, []);

  function aplicarCodigo(codigo) {
    if (esSlash) {
      const partes = (value || '').split('/').map((s) => s.trim()).filter((s, i, arr) => s || i < arr.length - 1);
      if (!partes.length) {
        onChange(`${codigo}/`);
      } else {
        partes[partes.length - 1] = codigo;
        onChange(`${partes.join('/')}/`);
      }
    } else {
      const partes = (value || '').split(',').map((s) => s.trim()).filter((s, i, arr) => s || i < arr.length - 1);
      if (partes.length === 0) {
        onChange(`${codigo}, `);
      } else {
        partes[partes.length - 1] = codigo;
        onChange(`${partes.join(', ')}, `);
      }
    }
    setEnfocado(true);
  }

  function onKeyDown(ev) {
    if (!sugerencias.length) return;
    if (ev.key === 'ArrowDown') {
      ev.preventDefault();
      setIndiceActivo((i) => (i + 1) % sugerencias.length);
    } else if (ev.key === 'ArrowUp') {
      ev.preventDefault();
      setIndiceActivo((i) => (i - 1 + sugerencias.length) % sugerencias.length);
    } else if (ev.key === 'Enter' && sugerencias[indiceActivo]) {
      ev.preventDefault();
      aplicarCodigo(codigoDeItem(sugerencias[indiceActivo]));
    } else if (ev.key === 'Escape') {
      setEnfocado(false);
    }
  }

  const mostrarLista = enfocado && incompleto.length >= 1 && !cargando;

  return (
    <div ref={contenedorRef} style={{ position: 'relative' }}>
      <label htmlFor={id} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
        {label}
      </label>
      <input
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setEnfocado(true)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        style={{ width: '100%' }}
      />
      {cargando && (
        <p style={{ fontSize: 11, color: 'var(--texto-suave)', margin: '4px 0 0' }}>Cargando catálogo…</p>
      )}
      {errorCatalogo && (
        <p style={{ fontSize: 11, color: 'var(--crit)', margin: '4px 0 0' }}>
          No se pudo cargar el catálogo — escriba los códigos manualmente.
        </p>
      )}
      {!cargando && !errorCatalogo && items.length === 0 && (
        <p style={{ fontSize: 11, color: 'var(--texto-suave)', margin: '4px 0 0' }}>
          Catálogo vacío — ejecute ./desplegar.sh para importar MITRE.
        </p>
      )}
      {mostrarLista && sugerencias.length > 0 && (
        <ul
          role="listbox"
          style={{
            position: 'absolute',
            zIndex: 20,
            left: 0,
            right: 0,
            top: '100%',
            margin: '2px 0 0',
            padding: 0,
            listStyle: 'none',
            background: 'var(--fondo-card, #1a2332)',
            border: '1px solid var(--borde, #334)',
            borderRadius: 6,
            maxHeight: 220,
            overflowY: 'auto',
            boxShadow: '0 8px 24px rgba(0,0,0,.35)',
          }}
        >
          {sugerencias.map((item, i) => (
            <li key={codigoDeItem(item)}>
              <button
                type="button"
                role="option"
                aria-selected={i === indiceActivo}
                onMouseDown={(ev) => ev.preventDefault()}
                onClick={() => aplicarCodigo(codigoDeItem(item))}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 10px',
                  border: 'none',
                  background: i === indiceActivo ? 'var(--acento-suave, rgba(0,180,120,.15))' : 'transparent',
                  color: 'inherit',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                <strong>{codigoDeItem(item)}</strong>
                {(item.nombre || item.descripcion) && (
                  <span style={{ color: 'var(--texto-suave)', marginLeft: 8 }}>
                    {item.nombre || item.descripcion}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {mostrarLista && sugerencias.length === 0 && items.length > 0 && (
        <p style={{
          position: 'absolute',
          zIndex: 20,
          left: 0,
          right: 0,
          top: '100%',
          margin: '2px 0 0',
          padding: '8px 10px',
          fontSize: 12,
          background: 'var(--fondo-card, #1a2332)',
          border: '1px solid var(--borde, #334)',
          borderRadius: 6,
        }}
        >
          Sin coincidencias para «{incompleto}»
        </p>
      )}
    </div>
  );
}

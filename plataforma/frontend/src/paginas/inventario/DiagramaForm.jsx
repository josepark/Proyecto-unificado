import { useEffect, useId, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, CampoTextarea, Fila } from '../../componentes/CamposFormulario';

const OPC_TIPO = [
  ['TOPO', 'Topología de red'],
  ['RACK', 'Diagrama de rack'],
  ['ARQ', 'Arquitectura'],
  ['FLUJO', 'Diagrama de flujo'],
  ['PLANO', 'Plano físico'],
  ['OTRO', 'Otro'],
];

function esImagen(url) {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(url || '');
}

export default function DiagramaForm() {
  const idArchivo = useId();
  const idFiltroActivos = useId();
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEditar, puedeEliminar } = useOutletContext() ?? {};

  const { datos: existente, cargando: cargandoExistente, error: errorCarga } = useApi(
    () => (editando ? inventarioApi.obtenerDiagrama(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: datacentersResp } = useApi(() => inventarioApi.datacenters(), []);
  const { datos: activosResp } = useApi(() => inventarioApi.listarActivos({ page_size: 1000 }), []);
  const datacenters = datacentersResp?.results ?? datacentersResp ?? [];
  const activos = (activosResp?.results ?? activosResp ?? []).slice().sort((a, b) => (a.id_activo > b.id_activo ? 1 : -1));

  const [titulo, setTitulo] = useState('');
  const [tipo, setTipo] = useState('TOPO');
  const [version, setVersion] = useState('');
  const [datacenter, setDatacenter] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [seleccionados, setSeleccionados] = useState(new Set());
  const [busquedaActivo, setBusquedaActivo] = useState('');
  const [sugerencias, setSugerencias] = useState(null);
  const [analizando, setAnalizando] = useState(false);

  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (editando && existente) {
      setTitulo(existente.titulo || '');
      setTipo(existente.tipo || 'TOPO');
      setVersion(existente.version || '');
      setDatacenter(existente.datacenter ? String(existente.datacenter) : '');
      setDescripcion(existente.descripcion || '');
      setSeleccionados(new Set((existente.activos_codigos || []).map((a) => a.id)));
    }
  }, [editando, existente]);

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'subir'} diagramas con tu rol actual.{' '}
          <Link to="/inventario/centro-datos">Volver</Link>
        </div>
      </div>
    );
  }
  if (editando && cargandoExistente) return <p>Cargando diagrama…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar el diagrama. <Link to="/inventario/centro-datos">Volver</Link>
        </div>
      </div>
    );
  }

  function alternarActivo(activoId) {
    setSeleccionados((s) => {
      const copia = new Set(s);
      if (copia.has(activoId)) copia.delete(activoId);
      else copia.add(activoId);
      return copia;
    });
  }

  async function manejarArchivo(ev) {
    const file = ev.target.files?.[0] || null;
    setArchivo(file);
    setSugerencias(null);
    if (!file) return;
    if (!/\.svg$/i.test(file.name)) {
      setSugerencias({ noAplica: true });
      return;
    }
    setAnalizando(true);
    try {
      const fd = new FormData();
      fd.append('archivo', file);
      const r = await inventarioApi.sugerirActivosDiagrama(fd);
      const sug = r.sugerencias || [];
      if (sug.length) {
        setSeleccionados((s) => {
          const copia = new Set(s);
          sug.forEach((x) => copia.add(x.activo_id));
          return copia;
        });
      }
      setSugerencias({ lista: sug });
    } catch {
      setSugerencias({ error: true });
    } finally {
      setAnalizando(false);
    }
  }

  async function guardar(ev) {
    ev.preventDefault();
    if (!titulo.trim()) {
      setError('El título es obligatorio.');
      return;
    }
    if (!editando && !archivo) {
      setError('El archivo es obligatorio al crear.');
      return;
    }
    setGuardando(true);
    setError(null);
    const fd = new FormData();
    fd.append('titulo', titulo);
    fd.append('tipo', tipo);
    fd.append('version', version || '');
    fd.append('descripcion', descripcion || '');
    if (datacenter) fd.append('datacenter', datacenter);
    else if (editando) fd.append('datacenter', '');
    if (archivo) fd.append('archivo', archivo);
    seleccionados.forEach((activoId) => fd.append('activos_ids', activoId));

    try {
      if (editando) await inventarioApi.editarDiagrama(id, fd);
      else await inventarioApi.subirDiagrama(fd);
      navegar('/inventario/centro-datos');
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar() {
    if (!window.confirm(`¿Eliminar el diagrama "${titulo}"?`)) return;
    setEliminando(true);
    try {
      await inventarioApi.eliminarDiagrama(id);
      navegar('/inventario/centro-datos');
    } catch (e) {
      setError(formatearErrorApi(e));
      setEliminando(false);
    }
  }

  const activosFiltrados = activos.filter((a) => {
    if (!busquedaActivo) return true;
    const t = `${a.id_activo} ${a.nombre}`.toLowerCase();
    return t.includes(busquedaActivo.toLowerCase());
  });

  return (
    <div>
      <Link to="/inventario/centro-datos" className="volver">
        ← Volver a Centro de datos
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? 'Editar diagrama' : 'Subir diagrama / topología'}
      </h2>

      <form onSubmit={guardar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Diagrama / Topología</h2>
          <div className="cuerpo">
            <div style={{ marginBottom: 12 }}>
              <Campo label="Título *" value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
            </div>
            <Fila>
              <CampoSelect label="Tipo" opciones={OPC_TIPO} value={tipo} onChange={(e) => setTipo(e.target.value)} />
              <Campo label="Versión" placeholder="1.0" value={version} onChange={(e) => setVersion(e.target.value)} />
            </Fila>
            <div style={{ marginBottom: 12 }}>
              <CampoSelect
                label="Centro de datos"
                opciones={[['', '— ninguno —'], ...datacenters.map((c) => [String(c.id), `${c.codigo} — ${c.nombre}`])]}
                value={datacenter}
                onChange={(e) => setDatacenter(e.target.value)}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label htmlFor={idArchivo} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
                Archivo (imagen, SVG o PDF) {editando ? '— dejar vacío para conservar el actual' : '*'}
              </label>
              <input id={idArchivo} type="file" accept="image/*,.pdf,.svg" onChange={manejarArchivo} />
              {editando && existente?.archivo_url && (
                <div style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 4 }}>
                  Actual:{' '}
                  <a href={existente.archivo_url} target="_blank" rel="noreferrer">
                    ver archivo
                  </a>
                  {esImagen(existente.archivo_url) && (
                    <div style={{ marginTop: 6 }}>
                      <img src={existente.archivo_url} alt={titulo} style={{ maxWidth: 220, border: '1px solid var(--borde)', borderRadius: 6 }} />
                    </div>
                  )}
                </div>
              )}
              {analizando && (
                <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>Analizando el diagrama…</div>
              )}
              {sugerencias?.noAplica && (
                <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>
                  La detección automática de activos solo está disponible para archivos SVG; para PDF o imagen,
                  seleccioná los activos manualmente abajo.
                </div>
              )}
              {sugerencias?.error && (
                <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>
                  No se pudo analizar el diagrama automáticamente; seleccioná los activos manualmente.
                </div>
              )}
              {sugerencias?.lista && sugerencias.lista.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>
                  No se reconoció en el texto del diagrama ningún activo del inventario. Seleccionalos manualmente si
                  corresponde.
                </div>
              )}
              {sugerencias?.lista && sugerencias.lista.length > 0 && (
                <div style={{ fontSize: 11, color: '#155f45', marginTop: 6 }}>
                  ✓ {sugerencias.lista.length} activo{sugerencias.lista.length > 1 ? 's' : ''} preseleccionado
                  {sugerencias.lista.length > 1 ? 's' : ''} automáticamente — revisá la lista antes de guardar:
                  <br />
                  {sugerencias.lista.map((s, i) => (
                    <span key={i}>
                      &nbsp;&nbsp;• {s.id_activo} ({Math.round(s.confianza * 100)}%) — coincide con &quot;{s.texto_coincidente}&quot;
                      <br />
                    </span>
                  ))}
                </div>
              )}
            </div>
            <CampoTextarea label="Descripción" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Correlación con el inventario</h2>
          <div className="cuerpo">
            <label htmlFor={idFiltroActivos} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
              Activos relacionados ({seleccionados.size} seleccionado{seleccionados.size === 1 ? '' : 's'})
            </label>
            <input
              id={idFiltroActivos}
              placeholder="Filtrar por ID o nombre…"
              value={busquedaActivo}
              onChange={(e) => setBusquedaActivo(e.target.value)}
              style={{ width: '100%', marginBottom: 8 }}
            />
            <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid var(--borde)', borderRadius: 6, padding: 8 }}>
              {activosFiltrados.map((a) => (
                <label key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0', fontSize: 13 }}>
                  <input type="checkbox" checked={seleccionados.has(a.id)} onChange={() => alternarActivo(a.id)} />
                  <b>{a.id_activo}</b> — {a.nombre}
                </label>
              ))}
              {!activosFiltrados.length && (
                <p style={{ fontSize: 13, color: 'var(--texto-suave)', margin: 0 }}>Sin resultados.</p>
              )}
            </div>
            {!editando && (
              <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>
                Si el archivo es SVG, se intentan detectar automáticamente los activos que menciona.
              </div>
            )}
          </div>
        </div>

        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Subir diagrama'}
          </button>
          <Link to="/inventario/centro-datos" className="btn btn-sec" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
            Cancelar
          </Link>
          {editando && puedeEliminar && (
            <button
              type="button"
              className="btn btn-sec"
              onClick={eliminar}
              disabled={eliminando}
              style={{ color: 'var(--crit)', marginLeft: 'auto' }}
            >
              {eliminando ? 'Eliminando…' : 'Eliminar diagrama'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

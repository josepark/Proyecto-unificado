import { useMemo, useRef, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { NIVEL_COLOR, descripcionNivel, mensajeErrorRbac } from './rbacUtil';

export default function Matriz() {
  const { puedeEditar, soloLecturaRbac } = useOutletContext() ?? {};
  const puedeEditarMatriz = puedeEditar && !soloLecturaRbac;

  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: heatmap } = useApi(() => rbacApi.heatmapMatriz(), []);

  const [filtroGrupo, setFiltroGrupo] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [rolDetalle, setRolDetalle] = useState(null);

  const paramsMatriz = useMemo(() => {
    const p = {};
    if (filtroGrupo) p.grupo = filtroGrupo;
    if (filtroCategoria) p.categoria = filtroCategoria;
    return p;
  }, [filtroGrupo, filtroCategoria]);

  const { datos, cargando, error, recargar } = useApi(
    () => rbacApi.matriz(paramsMatriz),
    [filtroGrupo, filtroCategoria],
  );

  const [editando, setEditando] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [resaltado, setResaltado] = useState(null);
  const columnasRef = useRef({});

  function irASistema(ev) {
    if (ev.key !== 'Enter') return;
    ev.preventDefault();
    const q = busqueda.trim().toLowerCase();
    if (!q) return;
    const encontrado = (datos?.sistemas ?? []).find((s) => s.nombre.toLowerCase().includes(q));
    if (!encontrado) return;
    columnasRef.current[encontrado.id]?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    setResaltado(encontrado.id);
    setTimeout(() => setResaltado(null), 2200);
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">{mensajeErrorRbac('la matriz de control de acceso', error)}</div>
      </div>
    );
  }
  if (cargando || !datos) return <p>Cargando matriz…</p>;

  const { roles, sistemas, celdas, niveles } = datos;

  async function cambiarNivel(rolId, sistemaId, nivel) {
    setGuardando(true);
    try {
      await rbacApi.editarCeldaMatriz(rolId, sistemaId, nivel);
      await recargar();
    } catch (e) {
      window.alert(e.message);
    } finally {
      setGuardando(false);
      setEditando(null);
    }
  }

  const rolSeleccionado = rolDetalle ? roles.find((r) => r.id === rolDetalle) : null;

  return (
    <div>
      <h2 style={{ margin: '4px 0 8px', color: 'var(--verde-profundo)' }}>Matriz de Control de Acceso</h2>
      {soloLecturaRbac && (
        <p className="sub" style={{ marginBottom: 12 }}>
          Modo consulta (solo lectura) — rol Consultor.
        </p>
      )}

      {heatmap?.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>Mapa de calor — accesos Admin (A) por categoría</h2>
          <div className="cuerpo">
            <table>
              <thead>
                <tr>
                  <th>Categoría</th>
                  <th className="num">Sistemas</th>
                  <th className="num">Celdas Admin (A)</th>
                  <th className="num">Accesos elevados</th>
                </tr>
              </thead>
              <tbody>
                {heatmap.map((h) => (
                  <tr key={h.categoria}>
                    <td>{h.categoria}</td>
                    <td className="num">{h.sistemas}</td>
                    <td className="num" style={{ color: h.n_admin > 0 ? 'var(--crit)' : undefined, fontWeight: h.n_admin > 0 ? 'bold' : undefined }}>
                      {h.n_admin}
                    </td>
                    <td className="num">{h.n_elevados}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
        <input
          placeholder="Buscar sistema… (Enter para ir)"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          onKeyDown={irASistema}
          style={{ maxWidth: 260 }}
        />
        <select value={filtroGrupo} onChange={(e) => setFiltroGrupo(e.target.value)} style={{ maxWidth: 180 }}>
          <option value="">Todos los grupos</option>
          {(catalogos?.grupos_rol ?? []).map((g) => (
            <option key={g.codigo} value={g.codigo}>{g.nombre}</option>
          ))}
        </select>
        <select value={filtroCategoria} onChange={(e) => setFiltroCategoria(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">Todas las categorías</option>
          {(catalogos?.categorias_sistema ?? []).map((c) => (
            <option key={c.id} value={c.nombre}>{c.nombre}</option>
          ))}
        </select>
        <Link to="/rbac/matriz/comparar" style={{ fontSize: 13 }}>Comparar dos roles →</Link>
        {puedeEditarMatriz && (
          <>
            <a href="/rbac/api/export/matriz.csv" style={{ fontSize: 13 }}>Exportar matriz (CSV)</a>
            <Link to="/rbac/matriz/importar" style={{ fontSize: 13 }}>Importar matriz (CSV)</Link>
          </>
        )}
      </div>

      <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginBottom: 12 }}>
        {roles.length} roles × {sistemas.length} sistemas. Clic en abreviatura del rol para ver su fila completa.{' '}
        {niveles.map((n) => (
          <span key={n.codigo} style={{ marginRight: 10 }} title={n.descripcion}>
            <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: NIVEL_COLOR[n.codigo], marginRight: 4, verticalAlign: 'middle' }} />
            {n.codigo} = {n.nombre}
          </span>
        ))}
      </p>

      {rolSeleccionado && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="cuerpo">
            <strong>{rolSeleccionado.abreviatura}</strong> — {rolSeleccionado.denominacion}
            <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--texto-suave)' }}>({rolSeleccionado.grupo})</span>
            <button type="button" className="btn btn-sec" style={{ marginLeft: 12, padding: '2px 8px', fontSize: 12 }} onClick={() => setRolDetalle(null)}>
              Cerrar
            </button>
            <Link to={`/rbac/roles/${rolSeleccionado.id}/editar`} style={{ marginLeft: 8, fontSize: 12 }}>Ver ficha del rol →</Link>
          </div>
        </div>
      )}

      <div style={{ overflow: 'auto', border: '1px solid var(--borde)', borderRadius: 10, maxHeight: '70vh' }}>
        <table style={{ borderRadius: 0 }}>
          <thead>
            <tr>
              <th style={{ position: 'sticky', left: 0, zIndex: 2, background: 'var(--panel-solid)' }}>Rol</th>
              {sistemas.map((s) => (
                <th
                  key={s.id}
                  ref={(el) => { columnasRef.current[s.id] = el; }}
                  title={`${s.nombre} (${s.categoria})`}
                  style={{
                    writingMode: 'vertical-rl', textAlign: 'left', minWidth: 30,
                    background: resaltado === s.id ? 'var(--resaltado)' : undefined,
                    color: resaltado === s.id ? 'var(--cric-gold-400)' : undefined,
                    display: rolDetalle && !celdas[`${rolDetalle}:${s.id}`] && celdas[`${rolDetalle}:${s.id}`] !== '—' ? undefined : undefined,
                  }}
                >
                  {s.nombre.length > 18 ? `${s.nombre.slice(0, 18)}…` : s.nombre}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {roles
              .filter((r) => !rolDetalle || r.id === rolDetalle)
              .map((r) => (
                <tr key={r.id}>
                  <td style={{ position: 'sticky', left: 0, background: 'var(--panel-solid)', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                    <button
                      type="button"
                      onClick={() => setRolDetalle(rolDetalle === r.id ? null : r.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 'bold', padding: 0 }}
                      title="Ver solo este rol"
                    >
                      {r.abreviatura}
                    </button>
                  </td>
                  {sistemas.map((s) => {
                    const clave = `${r.id}:${s.id}`;
                    const nivel = celdas[clave] || '—';
                    const esEditable = puedeEditarMatriz && editando === clave;
                    const auditQ = encodeURIComponent(`${r.abreviatura} × ${s.nombre}`);
                    return (
                      <td
                        key={s.id}
                        onClick={() => puedeEditarMatriz && !guardando && setEditando(clave)}
                        style={{
                          textAlign: 'center',
                          cursor: puedeEditarMatriz ? 'pointer' : 'default',
                          background: esEditable ? 'var(--panel-solid)' : resaltado === s.id ? 'var(--resaltado)' : undefined,
                        }}
                      >
                        {esEditable ? (
                          <select
                            autoFocus
                            defaultValue={nivel}
                            disabled={guardando}
                            onBlur={() => setEditando(null)}
                            onChange={(e) => cambiarNivel(r.id, s.id, e.target.value)}
                            style={{ padding: '2px 4px', fontSize: 11 }}
                          >
                            {niveles.map((n) => (
                              <option key={n.codigo} value={n.codigo}>{n.codigo}</option>
                            ))}
                          </select>
                        ) : (
                          <>
                            <span
                              title={descripcionNivel(niveles, nivel)}
                              style={{
                                display: 'inline-block', width: 20, height: 20, lineHeight: '20px',
                                borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 'bold',
                                background: NIVEL_COLOR[nivel],
                              }}
                            >
                              {nivel === '—' ? '' : nivel}
                            </span>
                            {nivel !== '—' && (
                              <Link
                                to={`/rbac/auditoria?q=${auditQ}&entidad=matriz_acceso`}
                                title="Historial de cambios en esta celda"
                                style={{ display: 'block', fontSize: 9, marginTop: 2, color: 'var(--texto-suave)' }}
                                onClick={(e) => e.stopPropagation()}
                              >
                                ⏱
                              </Link>
                            )}
                          </>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

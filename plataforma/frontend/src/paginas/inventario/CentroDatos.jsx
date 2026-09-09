import { useEffect, useRef, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { useInventarioMeta } from '../../hooks/useInventarioMeta';

const COLOR_TIPO_FALLBACK = { PRIN: '#3fa87f', MINI: '#c9a94e', DR: '#8b5cf6', CLOUD: '#0ea5e9' };

function esImagen(url) {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(url || '');
}

function Mapa({ datacenters, coloresTipo }) {
  const contenedorRef = useRef(null);
  const mapaRef = useRef(null);
  const marcadoresRef = useRef([]);

  useEffect(() => {
    if (!contenedorRef.current || mapaRef.current) return;
    mapaRef.current = L.map(contenedorRef.current).setView([4.5, -74.1], 5);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '© OpenStreetMap',
    }).addTo(mapaRef.current);
    return () => {
      mapaRef.current?.remove();
      mapaRef.current = null;
    };
  }, []);

  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;
    marcadoresRef.current.forEach((m) => mapa.removeLayer(m));
    marcadoresRef.current = [];
    const puntos = (datacenters || []).filter((c) => c.latitud && c.longitud);
    puntos.forEach((c) => {
      const color = coloresTipo[c.tipo] || COLOR_TIPO_FALLBACK[c.tipo] || '#6b7280';
      const marcador = L.circleMarker([c.latitud, c.longitud], {
        radius: 11,
        color: '#fff',
        weight: 2,
        fillColor: color,
        fillOpacity: 0.9,
      }).addTo(mapa);
      marcador.bindPopup(`<b>${c.nombre}</b><br>${c.codigo} · ${c.tier_display}<br>${c.ciudad} · ${c.num_activos} activos`);
      marcadoresRef.current.push(marcador);
    });
    if (puntos.length) {
      const grupo = L.featureGroup(marcadoresRef.current);
      try {
        mapa.fitBounds(grupo.getBounds().pad(0.5));
      } catch {
        /* rango invalido con un solo punto muy cercano al borde; se ignora */
      }
    }
    setTimeout(() => mapa.invalidateSize(), 200);
  }, [datacenters, coloresTipo]);

  return <div ref={contenedorRef} style={{ height: 360, borderRadius: 10, border: '1px solid var(--borde)', marginBottom: 16 }} />;
}

function TarjetaRacks({ dc, puedeEditar }) {
  const [abierto, setAbierto] = useState(false);
  const [form, setForm] = useState(null);
  const [error, setError] = useState(null);
  const { datos: racks, cargando, recargar } = useApi(
    () => (abierto ? inventarioApi.racksDatacenter(dc.id) : Promise.resolve(null)),
    [abierto, dc.id],
  );
  const lista = racks ?? [];

  async function guardar(ev) {
    ev.preventDefault();
    setError(null);
    try {
      await inventarioApi.crearRack({
        datacenter: dc.id,
        codigo: form.codigo.trim(),
        capacidad_u: Number(form.capacidad_u) || 42,
        ubicacion: form.ubicacion.trim(),
      });
      setForm(null);
      recargar();
    } catch (e) {
      setError(formatearErrorApi(e));
    }
  }

  return (
    <div style={{ marginTop: 10, borderTop: '1px solid var(--borde)', paddingTop: 10 }}>
      <button type="button" className="btn btn-sec" onClick={() => setAbierto((a) => !a)}>
        {abierto ? 'Ocultar racks' : 'Ver racks'}
      </button>
      {abierto && (
        <div style={{ marginTop: 10 }}>
          {cargando ? (
            <p style={{ fontSize: 13 }}>Cargando racks…</p>
          ) : (
            <>
              {!lista.length ? (
                <p style={{ fontSize: 13, color: 'var(--texto-suave)' }}>Sin racks registrados en este centro.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th className="num">Capacidad</th>
                      <th className="num">Ocupación</th>
                      <th>Ubicación</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lista.map((r) => (
                      <tr key={r.id}>
                        <td><b>{r.codigo}</b></td>
                        <td className="num">{r.capacidad_u} U</td>
                        <td className="num">{r.ocupacion_u ?? 0} U</td>
                        <td>{r.ubicacion || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {puedeEditar && (
                <div style={{ marginTop: 10 }}>
                  {!form ? (
                    <button type="button" className="btn btn-sec" onClick={() => setForm({ codigo: '', capacidad_u: '42', ubicacion: '' })}>
                      + Nuevo rack
                    </button>
                  ) : (
                    <form onSubmit={guardar} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                      <input placeholder="Código (A01)" value={form.codigo} required
                        onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))} />
                      <input type="number" placeholder="U" value={form.capacidad_u} min="1"
                        onChange={(e) => setForm((f) => ({ ...f, capacidad_u: e.target.value }))} style={{ width: 70 }} />
                      <input placeholder="Ubicación en sala" value={form.ubicacion}
                        onChange={(e) => setForm((f) => ({ ...f, ubicacion: e.target.value }))} style={{ flex: 1, minWidth: 140 }} />
                      <button type="submit" className="btn btn-primary">Guardar</button>
                      <button type="button" className="btn btn-sec" onClick={() => setForm(null)}>Cancelar</button>
                    </form>
                  )}
                  {error && <p style={{ color: 'var(--crit)', fontSize: 13 }}>{error}</p>}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TarjetaDatacenter({ dc, puedeEditar, coloresClase }) {
  const [abierto, setAbierto] = useState(false);
  const { datos: activos, cargando } = useApi(
    () => (abierto ? inventarioApi.activosDatacenter(dc.id) : Promise.resolve(null)),
    [abierto, dc.id],
  );

  return (
    <div className="card">
      <h2 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{dc.nombre}</span>
        <span style={{ fontSize: 11, fontWeight: 'normal' }}>{dc.tier_display}</span>
      </h2>
      <div className="cuerpo">
        <div style={{ fontSize: 13, color: 'var(--texto-suave)', marginBottom: 10 }}>
          <b>{dc.codigo}</b> · {dc.tipo_display}
          <br />
          {dc.ciudad || '—'}, {dc.departamento || ''} ({dc.pais || ''})
          <br />
          Responsable: {dc.responsable || '—'} · Activos: <b>{dc.num_activos}</b>
          {dc.descripcion && (
            <>
              <br />
              {dc.descripcion}
            </>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-sec" onClick={() => setAbierto((a) => !a)}>
            {abierto ? 'Ocultar activos' : `Ver activos (${dc.num_activos})`}
          </button>
          {puedeEditar && (
            <Link className="btn btn-sec" to={`/inventario/centro-datos/datacenters/${dc.id}/editar`}>
              Editar
            </Link>
          )}
        </div>
        {abierto && (
          <div style={{ marginTop: 10 }}>
            {cargando ? (
              <p style={{ fontSize: 13 }}>Cargando…</p>
            ) : !activos?.length ? (
              <p style={{ fontSize: 13, color: 'var(--texto-suave)' }}>Sin activos asignados a este centro de datos.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Activo</th>
                    <th>Clase</th>
                    <th>Riesgo</th>
                  </tr>
                </thead>
                <tbody>
                  {activos.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <Link to={`/inventario/activos/${a.id}`}>
                          <b>{a.id_activo}</b>
                        </Link>
                      </td>
                      <td>{a.nombre}</td>
                      <td>
                        <span className="clase-badge" style={{ background: coloresClase[a.clase] || '#888' }} title={a.clase_display}>
                          {a.clase_display || a.clase}
                        </span>
                      </td>
                      <td>
                        <span className={`tag t-${a.nivel_riesgo}`}>{a.nivel_riesgo_display}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        <TarjetaRacks dc={dc} puedeEditar={puedeEditar} />
      </div>
    </div>
  );
}

function TarjetaDiagrama({ d, datacenters }) {
  const nombreDC = (id) => datacenters?.find((c) => c.id === id)?.codigo || '';
  const meta = [d.tipo_display, d.version ? `v${d.version}` : '', d.datacenter ? nombreDC(d.datacenter) : '']
    .filter(Boolean)
    .join(' · ');
  const nLinks = (d.activos_codigos || []).length;
  return (
    <Link
      to={`/inventario/centro-datos/diagramas/${d.id}/editar`}
      style={{ textDecoration: 'none', color: 'inherit' }}
    >
      <div className="card" style={{ cursor: 'pointer' }}>
        <div
          style={{
            height: 120,
            background: '#f4f6f5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {esImagen(d.archivo_url) ? (
            <img src={d.archivo_url} alt={d.titulo} style={{ maxWidth: '100%', maxHeight: '100%' }} />
          ) : (
            <span style={{ fontSize: 32 }}>📄</span>
          )}
        </div>
        <div className="cuerpo">
          <div style={{ fontWeight: 'bold', fontSize: 13 }}>{d.titulo}</div>
          <div style={{ fontSize: 12, color: 'var(--texto-suave)' }}>{meta}</div>
          {nLinks > 0 && (
            <div style={{ fontSize: 11, color: 'var(--acento)', marginTop: 4 }}>
              🔗 {nLinks} activo{nLinks > 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function CentroDatos() {
  const { puedeEditar } = useOutletContext() ?? {};
  const { coloresClase, coloresTipoDc } = useInventarioMeta();
  const coloresTipo = { ...COLOR_TIPO_FALLBACK, ...coloresTipoDc };
  const { datos: datacentersResp, cargando: cargandoDC } = useApi(() => inventarioApi.datacenters(), []);
  const { datos: diagramasResp, cargando: cargandoDiag } = useApi(() => inventarioApi.diagramas(), []);
  const [busqueda, setBusqueda] = useState('');
  const [filtroDC, setFiltroDC] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');

  const datacenters = datacentersResp?.results ?? datacentersResp ?? [];
  const diagramas = diagramasResp?.results ?? diagramasResp ?? [];

  const diagramasFiltrados = diagramas.filter((d) => {
    const texto = `${d.titulo} ${d.descripcion || ''}`.toLowerCase();
    return (
      (!busqueda || texto.includes(busqueda.toLowerCase())) &&
      (!filtroDC || String(d.datacenter) === filtroDC) &&
      (!filtroTipo || d.tipo === filtroTipo)
    );
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px', flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Centro de datos</h2>
        {puedeEditar && (
          <div style={{ display: 'flex', gap: 8 }}>
            <Link className="btn btn-primary" to="/inventario/centro-datos/datacenters/nuevo" style={{ textDecoration: 'none' }}>
              + Nuevo centro de datos
            </Link>
            <Link className="btn btn-sec" to="/inventario/centro-datos/diagramas/nuevo" style={{ textDecoration: 'none' }}>
              + Subir diagrama / topología
            </Link>
          </div>
        )}
      </div>

      {cargandoDC ? <p>Cargando mapa…</p> : <Mapa datacenters={datacenters} coloresTipo={coloresTipo} />}

      {cargandoDC ? (
        <p>Cargando centros de datos…</p>
      ) : (
        <div className="detalle-grid" style={{ marginBottom: 20 }}>
          {datacenters.map((dc) => (
            <TarjetaDatacenter key={dc.id} dc={dc} puedeEditar={puedeEditar} coloresClase={coloresClase} />
          ))}
          {!datacenters.length && <p style={{ color: 'var(--texto-suave)' }}>Sin centros de datos registrados.</p>}
        </div>
      )}

      <div className="card">
        <h2>Diagramas y topologías</h2>
        <div className="cuerpo">
          <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
            <input
              placeholder="Buscar diagrama por título o descripción…"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              style={{ flex: 1, minWidth: 220 }}
            />
            <select value={filtroDC} onChange={(e) => setFiltroDC(e.target.value)}>
              <option value="">Todos los centros de datos</option>
              {datacenters.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.codigo}
                </option>
              ))}
            </select>
            <select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)}>
              <option value="">Todos los tipos</option>
              <option value="TOPO">Topología de red</option>
              <option value="RACK">Diagrama de rack</option>
              <option value="ARQ">Arquitectura</option>
              <option value="FLUJO">Diagrama de flujo</option>
              <option value="PLANO">Plano físico</option>
              <option value="OTRO">Otro</option>
            </select>
          </div>

          {cargandoDiag ? (
            <p>Cargando diagramas…</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14 }}>
              {diagramasFiltrados.map((d) => (
                <TarjetaDiagrama key={d.id} d={d} datacenters={datacenters} />
              ))}
              {!diagramasFiltrados.length && (
                <p style={{ color: 'var(--texto-suave)' }}>Sin diagramas para el filtro seleccionado.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

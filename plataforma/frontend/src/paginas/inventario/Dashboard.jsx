import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { useInventarioMeta } from '../../hooks/useInventarioMeta';
import PanelVinculacion from '../../componentes/PanelVinculacion';
import { claseTagNivelInventario, pendientesSync } from '../../lib/integracionUi';

export default function Dashboard() {
  const navegar = useNavigate();
  const [searchParams] = useSearchParams();
  const { puedeEditar, alertasUnificadas } = useOutletContext() ?? {};
  const alertasRes = alertasUnificadas;
  const vinc = alertasRes?.vinculacion;
  const { coloresClase } = useInventarioMeta();
  const { datos: stats, cargando: cargandoStats } = useApi(() => inventarioApi.estadisticas(), []);
  const [busqueda, setBusqueda] = useState('');
  const [filtroClase, setFiltroClase] = useState('');
  const [soloSinEspejo, setSoloSinEspejo] = useState(searchParams.get('solo_sin_espejo') === '1');
  const [seleccionados, setSeleccionados] = useState(() => new Set());
  const { datos: activos, cargando: cargandoLista } = useApi(
    () => inventarioApi.listarActivos({
      search: busqueda,
      page_size: 50,
      ...(filtroClase ? { clase: filtroClase } : {}),
      ...(soloSinEspejo ? { sin_espejo_riesgos: 'true' } : {}),
    }),
    [busqueda, filtroClase, soloSinEspejo],
  );

  useEffect(() => {
    if (searchParams.get('solo_sin_espejo') === '1') setSoloSinEspejo(true);
  }, [searchParams]);

  const clasesCatalogo = stats?.clases ?? [];
  const kpisClase = useMemo(() => {
    const por = stats?.por_clase ?? {};
    if (clasesCatalogo.length) {
      return clasesCatalogo.map((c) => ({
        codigo: c.codigo,
        label: c.nombre,
        n: por[c.codigo] || 0,
        color: c.color || coloresClase[c.codigo],
      }));
    }
    return Object.entries(por).map(([codigo, n]) => ({
      codigo,
      label: codigo,
      n,
      color: coloresClase[codigo],
    }));
  }, [stats, clasesCatalogo, coloresClase]);

  const filas = activos?.results ?? activos ?? [];
  const todosVisibles = filas.length > 0 && filas.every((a) => seleccionados.has(a.id));
  const algunoSeleccionado = seleccionados.size > 0;

  function alternar(id) {
    setSeleccionados((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function alternarTodos() {
    if (todosVisibles) {
      setSeleccionados(new Set());
      return;
    }
    setSeleccionados(new Set(filas.map((a) => a.id)));
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px', flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Dashboard</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link
            className="btn btn-sec"
            to="/inventario/alertas"
            style={{ textDecoration: 'none' }}
          >
            🔔 Centro de alertas
            {(alertasRes?.total_consolidado ?? 0) > 0 ? ` (${alertasRes.total_consolidado})` : ''}
          </Link>
          <a className="btn btn-sec" href={inventarioApi.exportarInventarioXlsx()} style={{ textDecoration: 'none' }}>
            ⬇ Exportar Excel
          </a>
          {algunoSeleccionado ? (
            <a
              className="btn btn-sec"
              href={inventarioApi.etiquetasLotePdf([...seleccionados])}
              target="_blank"
              rel="noreferrer"
              style={{ textDecoration: 'none' }}
            >
              🏷️ Etiquetas ({seleccionados.size})
            </a>
          ) : null}
          {puedeEditar ? (
            <>
              <Link className="btn btn-sec" to="/inventario/activos/importar" style={{ textDecoration: 'none' }}>
                ⬆ Importar Excel
              </Link>
              <Link className="btn btn-sec" to="/inventario/clases" style={{ textDecoration: 'none' }}>
                Clases de activo
              </Link>
              <Link className="btn btn-primary" to="/inventario/activos/nuevo" style={{ textDecoration: 'none' }}>
                + Nuevo activo
              </Link>
            </>
          ) : null}
        </div>
      </div>

      {(pendientesSync(vinc) > 0 || vinc?.disponible === false) && (
        <PanelVinculacion
          vinculacion={vinc}
          compacto
          puedeEditar={puedeEditar}
          ocultarSiOk
        />
      )}

      {cargandoStats ? (
        <p>Cargando indicadores…</p>
      ) : stats ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 13,
            marginBottom: 20,
          }}
        >
          <Kpi n={stats.total_activos} l="Activos totales" />
          <Kpi n={stats.por_nivel_riesgo?.CRIT || 0} l="Riesgo crítico" />
          <Kpi n={stats.por_nivel_riesgo?.ALTO || 0} l="Riesgo alto" />
          {kpisClase.map((k) => (
            <Kpi key={k.codigo} n={k.n} l={k.label} color={k.color} />
          ))}
          <Kpi n={stats.datos_personales || 0} l="Con datos personales" />
        </div>
      ) : (
        <p>No se pudieron cargar los indicadores.</p>
      )}

      {!cargandoStats && stats?.total_activos === 0 ? (
        <div className="aviso" style={{ marginBottom: 16 }}>
          <strong>Inventario vacío.</strong> Este espacio de datos es propio de su cuenta. Use{' '}
          {puedeEditar ? (
            <Link to="/inventario/activos/nuevo">+ Nuevo activo</Link>
          ) : (
            '«Nuevo activo»'
          )}{' '}
          o importación Excel para comenzar. Los usuarios de demostración (<code>admin</code>,{' '}
          <code>consultor</code>) comparten el inventario de ejemplo de la organización.
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder="Buscar por ID, nombre, propietario, notas…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ flex: 1, minWidth: 220, maxWidth: 420 }}
        />
        <select value={filtroClase} onChange={(e) => setFiltroClase(e.target.value)} style={{ minWidth: 180 }}>
          <option value="">Todas las clases</option>
          {clasesCatalogo.map((c) => (
            <option key={c.codigo} value={c.codigo}>{c.nombre}</option>
          ))}
        </select>
        <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            type="checkbox"
            checked={soloSinEspejo}
            onChange={(e) => setSoloSinEspejo(e.target.checked)}
          />
          Solo sin espejo en Riesgos
          <span title="Activos del Inventario sin registro espejo en Gestión de Riesgos (no incluye huérfanos solo en Riesgos)" style={{ marginLeft: 4, cursor: 'help' }}>ⓘ</span>
        </label>
      </div>

      {cargandoLista ? (
        <p>Cargando activos…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th style={{ width: 36 }}>
                <input
                  type="checkbox"
                  aria-label="Seleccionar todos los activos visibles"
                  checked={todosVisibles}
                  onChange={alternarTodos}
                />
              </th>
              <th>ID</th>
              <th>Activo</th>
              <th>Clase</th>
              <th>Nivel</th>
              <th title="Vínculo con Gestión de Riesgos">Sync ↗</th>
              <th>Propietario</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((a) => (
              <tr key={a.id}>
                <td onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar ${a.id_activo}`}
                    checked={seleccionados.has(a.id)}
                    onChange={() => alternar(a.id)}
                  />
                </td>
                <td
                  onClick={() => navegar(`/inventario/activos/${a.id}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <b>{a.id_activo}</b>
                </td>
                <td onClick={() => navegar(`/inventario/activos/${a.id}`)} style={{ cursor: 'pointer' }}>
                  {a.nombre}
                </td>
                <td onClick={() => navegar(`/inventario/activos/${a.id}`)} style={{ cursor: 'pointer' }}>
                  <span className="clase-badge" style={{ background: coloresClase[a.clase] || '#888' }} title={a.clase_display}>
                    {a.clase}
                  </span>
                </td>
                <td onClick={() => navegar(`/inventario/activos/${a.id}`)} style={{ cursor: 'pointer' }}>
                  <span className={claseTagNivelInventario(a.nivel_riesgo)}>{a.nivel_riesgo_display}</span>
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  {a.vinculado_riesgos === null ? (
                    <span style={{ color: 'var(--texto-suave)', fontSize: 11 }} title="Gestión de Riesgos no disponible">—</span>
                  ) : a.vinculado_riesgos ? (
                    <Link
                      to={`/gestion-riesgos/activos/${a.riesgos_id}`}
                      title="Ver en Gestión de Riesgos"
                      style={{ fontSize: 12 }}
                    >
                      ↗
                    </Link>
                  ) : (
                    <Link
                      to={`/inventario/activos/${a.id}`}
                      title="Sin espejo en Gestión de Riesgos — abrir ficha"
                      style={{ color: 'var(--alto)', fontSize: 12, textDecoration: 'none' }}
                    >
                      ⚠
                    </Link>
                  )}
                </td>
                <td onClick={() => navegar(`/inventario/activos/${a.id}`)} style={{ cursor: 'pointer' }}>
                  {a.propietario || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Kpi({ n, l, color }) {
  return (
    <div className="kpi" style={color ? { borderLeftColor: color } : undefined}>
      <div className="n" style={color ? { color } : undefined}>{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}

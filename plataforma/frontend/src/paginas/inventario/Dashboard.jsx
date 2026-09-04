import { useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

const CLASE_COLOR = { INFRA: '#1f6b52', SIST: '#c9a94e', EQUI: '#28407a' };

export default function Dashboard() {
  const navegar = useNavigate();
  const { puedeEditar } = useOutletContext() ?? {};
  const { datos: stats, cargando: cargandoStats } = useApi(() => inventarioApi.estadisticas(), []);
  const [busqueda, setBusqueda] = useState('');
  const { datos: activos, cargando: cargandoLista } = useApi(
    () => inventarioApi.listarActivos({ search: busqueda, page_size: 50 }),
    [busqueda],
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Dashboard</h2>
        {puedeEditar && (
          <div style={{ display: 'flex', gap: 8 }}>
            <Link className="btn btn-sec" to="/inventario/activos/importar" style={{ textDecoration: 'none' }}>
              ⬆ Importar Excel
            </Link>
            <Link className="btn btn-primary" to="/inventario/activos/nuevo" style={{ textDecoration: 'none' }}>
              + Nuevo activo
            </Link>
          </div>
        )}
      </div>

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
          <Kpi n={stats.por_clase?.INFRA || 0} l="Infraestructura" />
          <Kpi n={stats.por_clase?.SIST || 0} l="Sistemas de info." />
          <Kpi n={stats.por_clase?.EQUI || 0} l="Equipos de cómputo" />
          <Kpi n={stats.datos_personales || 0} l="Con datos personales" />
        </div>
      ) : (
        <p>No se pudieron cargar los indicadores.</p>
      )}

      <input
        placeholder="Buscar por ID, nombre, propietario, notas…"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        style={{ width: '100%', maxWidth: 420, marginBottom: 12 }}
      />

      {cargandoLista ? (
        <p>Cargando activos…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Activo</th>
              <th>Clase</th>
              <th>Riesgo</th>
              <th>Propietario</th>
            </tr>
          </thead>
          <tbody>
            {(activos?.results ?? activos ?? []).map((a) => (
              <tr
                key={a.id}
                onClick={() => navegar(`/inventario/activos/${a.id}`)}
                style={{ cursor: 'pointer' }}
              >
                <td>
                  <b>{a.id_activo}</b>
                </td>
                <td>{a.nombre}</td>
                <td>
                  <span
                    className="clase-badge"
                    style={{ background: CLASE_COLOR[a.clase] || '#888' }}
                  >
                    {a.clase}
                  </span>
                </td>
                <td>
                  <span className={`tag t-${a.nivel_riesgo}`}>{a.nivel_riesgo_display}</span>
                </td>
                <td>{a.propietario || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Kpi({ n, l }) {
  return (
    <div className="kpi">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}

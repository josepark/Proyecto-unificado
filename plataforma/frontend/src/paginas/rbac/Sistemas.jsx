import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import BannerErrorMutacion from '../../componentes/BannerErrorMutacion';
import { mensajeErrorRbac } from './rbacUtil';

export default function Sistemas() {
  const { puedeEditar } = useOutletContext();
  const [busqueda, setBusqueda] = useState('');
  const [categoria, setCategoria] = useState('');
  const [clasificacion, setClasificacion] = useState('');
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: sistemas, cargando, error, recargar } = useApi(
    () => rbacApi.listarSistemas({
      ...(busqueda ? { q: busqueda } : {}),
      ...(categoria ? { categoria } : {}),
      ...(clasificacion ? { clasificacion } : {}),
      ...(incluirInactivos ? { incluir_inactivos: 1 } : {}),
    }),
    [busqueda, categoria, clasificacion, incluirInactivos],
  );
  const [cambiandoEstado, setCambiandoEstado] = useState(null);
  const [errorMutacion, setErrorMutacion] = useState(null);

  async function alternarActivo(id) {
    setCambiandoEstado(id);
    setErrorMutacion(null);
    try {
      await rbacApi.toggleActivoSistema(id);
      recargar();
    } catch (e) {
      setErrorMutacion(e.message);
    } finally {
      setCambiandoEstado(null);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('sistemas', error)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Sistemas</h2>
        {puedeEditar && (
          <Link className="btn btn-primary" to="/rbac/sistemas/nuevo" style={{ textDecoration: 'none' }}>
            + Nuevo sistema
          </Link>
        )}
      </div>

      <BannerErrorMutacion error={errorMutacion} onCerrar={() => setErrorMutacion(null)} />

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder="Buscar por nombre…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ flex: 1, minWidth: 200 }}
        />
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="">Todas las categorías</option>
          {(catalogos?.categorias_sistema ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
        <select value={clasificacion} onChange={(e) => setClasificacion(e.target.value)}>
          <option value="">Todas las clasificaciones</option>
          {(catalogos?.clasificaciones ?? []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input
            type="checkbox"
            style={{ width: 'auto' }}
            checked={incluirInactivos}
            onChange={(e) => setIncluirInactivos(e.target.checked)}
          />
          Mostrar desactivados
        </label>
      </div>

      {cargando ? (
        <p>Cargando sistemas…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Sistema / Recurso</th>
              <th>Categoría</th>
              <th>Clasificación</th>
              <th>ATT&amp;CK</th>
              <th className="num">Roles con acceso</th>
              <th>Estado</th>
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {(sistemas ?? []).map((s) => (
              <tr key={s.id} style={!s.activo ? { opacity: 0.55 } : undefined}>
                <td>
                  <Link to={`/rbac/sistemas/${s.id}/editar`}>
                    <b>{s.nombre}</b>
                  </Link>
                </td>
                <td>{s.categoria}</td>
                <td>{s.clasificacion}</td>
                <td>{s.tecnicas_attack || '—'}</td>
                <td className="num">{s.n_roles}</td>
                <td>
                  <span className={`tag ${s.activo ? 't-BAJO' : 't-CRIT'}`}>{s.activo ? 'Activo' : 'Desactivado'}</span>
                </td>
                {puedeEditar && (
                  <td>
                    <button
                      className="btn-sec"
                      disabled={cambiandoEstado === s.id}
                      onClick={() => alternarActivo(s.id)}
                    >
                      {cambiandoEstado === s.id ? 'Guardando…' : s.activo ? 'Desactivar' : 'Reactivar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!(sistemas ?? []).length && (
              <tr>
                <td colSpan={puedeEditar ? 7 : 6} className="sub">
                  Ningún sistema coincide con el filtro aplicado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

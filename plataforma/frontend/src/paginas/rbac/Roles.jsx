import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';

export default function Roles() {
  const { puedeEditar } = useOutletContext();
  const [busqueda, setBusqueda] = useState('');
  const [incluirInactivos, setIncluirInactivos] = useState(false);
  const { datos: roles, cargando, error, recargar } = useApi(
    () => rbacApi.listarRoles({
      ...(busqueda ? { q: busqueda } : {}),
      ...(incluirInactivos ? { incluir_inactivos: 1 } : {}),
    }),
    [busqueda, incluirInactivos],
  );
  const [certificando, setCertificando] = useState(null);
  const [cambiandoEstado, setCambiandoEstado] = useState(null);

  async function certificar(id) {
    setCertificando(id);
    try {
      await rbacApi.certificarRol(id);
      recargar();
    } catch (e) {
      alert(e.message);
    } finally {
      setCertificando(null);
    }
  }

  async function alternarActivo(id) {
    setCambiandoEstado(id);
    try {
      await rbacApi.toggleActivoRol(id);
      recargar();
    } catch (e) {
      alert(e.message);
    } finally {
      setCambiandoEstado(null);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar la Matriz RBAC ({error.status === 401 ? 'inicie sesión con rol Dinamizador o Administrador' : error.message}).
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Roles</h2>
        {puedeEditar && (
          <Link className="btn btn-primary" to="/rbac/roles/nuevo" style={{ textDecoration: 'none' }}>
            + Nuevo rol
          </Link>
        )}
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder="Buscar por abreviatura, denominación o código…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ flex: 1, minWidth: 220 }}
        />
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
        <p>Cargando roles…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Rol</th>
              <th>Denominación</th>
              <th>Grupo</th>
              <th>Riesgo ATT&amp;CK</th>
              <th>Revisión</th>
              <th>Estado</th>
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {(roles ?? []).map((r) => (
              <tr key={r.id} style={!r.activo ? { opacity: 0.55 } : undefined}>
                <td>
                  <Link to={`/rbac/roles/${r.id}/editar`}>
                    <b>{r.abreviatura}</b>
                  </Link>
                </td>
                <td>{r.denominacion}</td>
                <td>{r.grupo}</td>
                <td>{r.riesgo_attack}</td>
                <td>
                  {!r.activo ? (
                    '—'
                  ) : r.revision_vencida ? (
                    <span className="tag t-ALTO">Vencida</span>
                  ) : (
                    <span className="tag t-BAJO">Al día</span>
                  )}
                </td>
                <td>
                  <span className={`tag ${r.activo ? 't-BAJO' : 't-CRIT'}`}>{r.activo ? 'Activo' : 'Desactivado'}</span>
                </td>
                {puedeEditar && (
                  <td style={{ display: 'flex', gap: 6 }}>
                    {r.activo && (
                      <button
                        className="btn-sec"
                        disabled={certificando === r.id}
                        onClick={() => certificar(r.id)}
                      >
                        {certificando === r.id ? 'Certificando…' : 'Certificar'}
                      </button>
                    )}
                    <button
                      className="btn-sec"
                      disabled={cambiandoEstado === r.id}
                      onClick={() => alternarActivo(r.id)}
                    >
                      {cambiandoEstado === r.id ? 'Guardando…' : r.activo ? 'Desactivar' : 'Reactivar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!(roles ?? []).length && (
              <tr>
                <td colSpan={puedeEditar ? 7 : 6} className="sub">
                  Ningún rol coincide con el filtro aplicado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

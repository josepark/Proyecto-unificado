import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import BannerErrorMutacion from '../../componentes/BannerErrorMutacion';
import { mensajeErrorRbac } from './rbacUtil';

const ESTADO_CLASE = { Activo: 't-BAJO', Temporal: 't-MEDIO', Suspendido: 't-ALTO', Revocado: 't-CRIT' };
const ESTADOS = ['Activo', 'Temporal', 'Suspendido', 'Revocado'];

function FilaEstado({ usuario, onAplicar, guardando }) {
  const [estado, setEstado] = useState(usuario.estado);
  const [motivo, setMotivo] = useState('');
  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <select value={estado} onChange={(e) => setEstado(e.target.value)} style={{ width: 110 }}>
        {ESTADOS.map((e) => (
          <option key={e} value={e}>
            {e}
          </option>
        ))}
      </select>
      <input placeholder="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} style={{ width: 110 }} />
      <button
        className="btn-sec"
        disabled={guardando || estado === usuario.estado}
        onClick={() => onAplicar(usuario.id, estado, motivo)}
      >
        {guardando ? '…' : 'Aplicar'}
      </button>
    </div>
  );
}

export default function Usuarios() {
  const { puedeEditar } = useOutletContext();
  const [busqueda, setBusqueda] = useState('');
  const [estado, setEstado] = useState('');
  const { datos: usuarios, cargando, error, recargar } = useApi(
    () => rbacApi.listarUsuarios({ ...(busqueda ? { q: busqueda } : {}), ...(estado ? { estado } : {}) }),
    [busqueda, estado],
  );
  const [cambiando, setCambiando] = useState(null);
  const [eliminando, setEliminando] = useState(null);
  const [errorMutacion, setErrorMutacion] = useState(null);

  async function aplicarEstado(id, nuevoEstado, motivo) {
    setCambiando(id);
    setErrorMutacion(null);
    try {
      await rbacApi.cambiarEstadoUsuario(id, nuevoEstado, motivo);
      recargar();
    } catch (e) {
      setErrorMutacion(e.message);
    } finally {
      setCambiando(null);
    }
  }

  async function eliminar(u) {
    if (!confirm(`¿Eliminar el registro del usuario ${u.nombre}? La bitácora conserva sus movimientos, pero el registro no se puede recuperar.`)) return;
    setEliminando(u.id);
    setErrorMutacion(null);
    try {
      await rbacApi.eliminarUsuario(u.id);
      recargar();
    } catch (e) {
      setErrorMutacion(e.message);
    } finally {
      setEliminando(null);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('usuarios', error)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Usuarios</h2>
        {puedeEditar && (
          <Link className="btn btn-primary" to="/rbac/usuarios/nuevo" style={{ textDecoration: 'none' }}>
            + Nuevo usuario
          </Link>
        )}
      </div>

      <BannerErrorMutacion error={errorMutacion} onCerrar={() => setErrorMutacion(null)} />

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          placeholder="Buscar por nombre o rol…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ flex: 1, minWidth: 220 }}
        />
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
      </div>

      {cargando ? (
        <p>Cargando usuarios…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Rol</th>
              <th>Estado</th>
              <th>MFA</th>
              <th>Sistemas</th>
              <th>Excepciones</th>
              {puedeEditar && <th>Cambiar estado</th>}
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {(usuarios ?? []).map((u) => (
              <tr key={u.id}>
                <td>
                  <Link to={`/rbac/usuarios/${u.id}/editar`}>
                    <b>{u.nombre}</b>
                  </Link>
                </td>
                <td>
                  <b>{u.rol}</b>
                </td>
                <td>
                  <span className={`tag ${ESTADO_CLASE[u.estado] || ''}`}>{u.estado}</span>
                </td>
                <td>{u.mfa_activo}</td>
                <td>{u.n_sistemas}</td>
                <td>{u.n_excepciones > 0 ? <b style={{ color: 'var(--alto)' }}>{u.n_excepciones}</b> : 0}</td>
                {puedeEditar && (
                  <td>
                    <FilaEstado usuario={u} onAplicar={aplicarEstado} guardando={cambiando === u.id} />
                  </td>
                )}
                {puedeEditar && (
                  <td>
                    <button
                      className="btn-sec"
                      disabled={eliminando === u.id}
                      onClick={() => eliminar(u)}
                      style={{ color: 'var(--crit)' }}
                    >
                      {eliminando === u.id ? 'Eliminando…' : 'Eliminar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!(usuarios ?? []).length && (
              <tr>
                <td colSpan={puedeEditar ? 8 : 6} className="sub">
                  Ningún usuario coincide con el filtro aplicado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

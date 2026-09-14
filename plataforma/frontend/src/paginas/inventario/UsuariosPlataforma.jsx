import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import BannerErrorMutacion from '../../componentes/BannerErrorMutacion';
import { formatearErrorApi } from '../../api/client';
import { etiquetasModulos } from '../../lib/modulosPlataforma';

const ROL_CLASE = {
  Consultor: 't-BAJO',
  Dinamizador: 't-MEDIO',
  Administrador: 't-ALTO',
};

export default function UsuariosPlataforma() {
  const { puedeEliminar } = useOutletContext() ?? {};
  const [busqueda, setBusqueda] = useState('');
  const [rol, setRol] = useState('');
  const [area, setArea] = useState('');
  const [soloActivos, setSoloActivos] = useState(true);
  const { datos, cargando, error, recargar } = useApi(
    () =>
      inventarioApi.listarUsuariosPlataforma({
        ...(busqueda ? { search: busqueda } : {}),
        ...(rol ? { rol } : {}),
        ...(area ? { area } : {}),
        ...(soloActivos ? { is_active: true } : {}),
        page_size: 100,
      }),
    [busqueda, rol, area, soloActivos],
  );
  const { datos: meta } = useApi(() => inventarioApi.metaUsuariosPlataforma(), []);
  const [eliminando, setEliminando] = useState(null);
  const [errorMutacion, setErrorMutacion] = useState(null);

  if (puedeEliminar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          La gestión de cuentas de acceso requiere rol <b>Administrador</b>.
        </div>
      </div>
    );
  }

  const lista = datos?.results ?? datos ?? [];

  async function eliminar(u) {
    if (
      !confirm(
        `¿Eliminar la cuenta «${u.username}»? Esta acción no se puede deshacer. Considere desactivarla en su lugar.`,
      )
    ) {
      return;
    }
    setEliminando(u.id);
    setErrorMutacion(null);
    try {
      await inventarioApi.eliminarUsuarioPlataforma(u.id);
      recargar();
    } catch (e) {
      setErrorMutacion(formatearErrorApi(e));
    } finally {
      setEliminando(null);
    }
  }

  async function alternarActivo(u) {
    setErrorMutacion(null);
    try {
      await inventarioApi.editarUsuarioPlataforma(u.id, {
        is_active: !u.is_active,
        rol: u.rol,
        modulos_acceso: u.modulos_acceso,
      });
      recargar();
    } catch (e) {
      setErrorMutacion(formatearErrorApi(e));
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">No se pudo cargar la lista de usuarios: {error.message}</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <div>
          <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Cuentas de acceso</h2>
          <p className="sub" style={{ margin: '6px 0 0' }}>
            Usuarios que inician sesión en la plataforma. Distintos de los usuarios del registro RBAC (MCA-001).
          </p>
        </div>
        <Link className="btn btn-primary" to="/inventario/usuarios/nuevo" style={{ textDecoration: 'none' }}>
          + Nueva cuenta
        </Link>
      </div>

      <BannerErrorMutacion error={errorMutacion} onCerrar={() => setErrorMutacion(null)} />

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          placeholder="Buscar por usuario, nombre o correo…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ flex: 1, minWidth: 220 }}
        />
        <select value={rol} onChange={(e) => setRol(e.target.value)}>
          <option value="">Todos los roles</option>
          {(meta?.roles ?? ['Consultor', 'Dinamizador', 'Administrador']).map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <input
          placeholder="Filtrar área…"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          list="areas-plataforma"
          style={{ minWidth: 140 }}
        />
        <datalist id="areas-plataforma">
          {(meta?.areas ?? []).map((a) => (
            <option key={a} value={a} />
          ))}
        </datalist>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)} />
          Solo activos
        </label>
      </div>

      {cargando ? (
        <p>Cargando cuentas…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Nombre</th>
              <th>Área</th>
              <th>Rol SGSI</th>
              <th>Proyectos</th>
              <th>Correo</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lista.map((u) => (
              <tr key={u.id} style={u.is_active ? undefined : { opacity: 0.65 }}>
                <td>
                  <Link to={`/inventario/usuarios/${u.id}/editar`}>
                    <b>{u.username}</b>
                  </Link>
                  {u.is_superuser ? (
                    <span className="tag t-CRIT" style={{ marginLeft: 6 }}>
                      super
                    </span>
                  ) : null}
                </td>
                <td>{u.nombre_completo}</td>
                <td>{u.area || '—'}</td>
                <td>
                  <span className={`tag ${ROL_CLASE[u.rol] || ''}`}>{u.rol || 'Sin rol'}</span>
                </td>
                <td style={{ fontSize: 12, maxWidth: 220 }}>
                  {etiquetasModulos(u.modulos_acceso).join(' · ')}
                </td>
                <td>{u.email || '—'}</td>
                <td>{u.is_active ? 'Activo' : 'Inactivo'}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button className="btn-sec" onClick={() => alternarActivo(u)} style={{ marginRight: 6 }}>
                    {u.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                  {!u.is_superuser ? (
                    <button
                      className="btn-sec"
                      disabled={eliminando === u.id}
                      onClick={() => eliminar(u)}
                      style={{ color: 'var(--crit)' }}
                    >
                      {eliminando === u.id ? '…' : 'Eliminar'}
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!lista.length && (
              <tr>
                <td colSpan={8} className="sub">
                  No hay cuentas que coincidan con el filtro.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

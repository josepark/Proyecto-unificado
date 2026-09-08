import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { mensajeErrorRbac } from './rbacUtil';

export default function Excepciones() {
  const { puedeEditar } = useOutletContext();
  const [incluirVencidas, setIncluirVencidas] = useState(false);
  const { datos, cargando, error, recargar } = useApi(
    () => rbacApi.listarExcepciones(incluirVencidas ? { vencidas: 1 } : undefined),
    [incluirVencidas],
  );
  const [retirando, setRetirando] = useState(null);

  async function retirar(fila) {
    if (!confirm(`¿Retirar esta excepción? «${fila.usuario}» volverá al nivel ${fila.nivel_rol} de su rol en «${fila.sistema}».`)) return;
    setRetirando(`${fila.usuario_id}:${fila.sistema_id}`);
    try {
      await rbacApi.eliminarExcepcion(fila.usuario_id, fila.sistema_id);
      recargar();
    } catch (e) {
      alert(e.message);
    } finally {
      setRetirando(null);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('excepciones', error)}
        </div>
      </div>
    );
  }

  const filas = datos?.filas ?? [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Excepciones de acceso</h2>
        {puedeEditar && (
          <Link className="btn btn-primary" to="/rbac/excepciones/masiva" style={{ textDecoration: 'none' }}>
            Asignación masiva
          </Link>
        )}
      </div>

      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Diferencias entre el acceso efectivo de una persona y el que otorga su rol, cada una con motivo y responsable
        en la bitácora (control 5.18). {datos?.total_vigentes ?? 0} vigente(s)
        {datos?.total_vencidas ? ` · ${datos.total_vencidas} vencida(s) pendiente(s) de depurar` : ''}.
      </p>

      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, marginBottom: 12 }}>
        <input type="checkbox" style={{ width: 'auto' }} checked={incluirVencidas} onChange={(e) => setIncluirVencidas(e.target.checked)} />
        Incluir vencidas
      </label>

      {cargando ? (
        <p>Cargando excepciones…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Estado</th>
              <th>Sistema</th>
              <th>Rol</th>
              <th>Nivel del rol</th>
              <th>Nivel excepción</th>
              <th>Motivo</th>
              <th>Vigencia</th>
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {filas.map((e) => (
              <tr key={`${e.usuario_id}:${e.sistema_id}`} style={e.vencida ? { opacity: 0.6 } : undefined}>
                <td>
                  <Link to={`/rbac/usuarios/${e.usuario_id}/editar`}>{e.usuario}</Link>
                </td>
                <td>{e.usuario_estado}</td>
                <td>
                  <Link to={`/rbac/sistemas/${e.sistema_id}/editar`}>{e.sistema}</Link>
                </td>
                <td>{e.rol}</td>
                <td>
                  <span className={`chip niv-${e.nivel_rol === '—' ? 'X' : e.nivel_rol}`}>{e.nivel_rol}</span>
                </td>
                <td>
                  <span className={`chip niv-${e.nivel_excepcion === '—' ? 'X' : e.nivel_excepcion}`}>{e.nivel_excepcion}</span>
                </td>
                <td>{e.motivo}</td>
                <td>
                  {e.fecha_fin ? (
                    <>
                      {e.fecha_fin}
                      {e.vencida && (
                        <>
                          <br />
                          <small style={{ color: 'var(--crit)' }}>vencida</small>
                        </>
                      )}
                    </>
                  ) : (
                    'Indefinida'
                  )}
                </td>
                {puedeEditar && (
                  <td>
                    <button
                      className="btn-sec"
                      disabled={retirando === `${e.usuario_id}:${e.sistema_id}`}
                      onClick={() => retirar(e)}
                    >
                      {retirando === `${e.usuario_id}:${e.sistema_id}` ? 'Retirando…' : 'Retirar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!filas.length && (
              <tr>
                <td colSpan={puedeEditar ? 9 : 8} className="sub">
                  No hay excepciones {incluirVencidas ? 'registradas' : 'vigentes'}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

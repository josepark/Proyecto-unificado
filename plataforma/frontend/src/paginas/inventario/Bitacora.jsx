import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

function BitaItem({ r }) {
  const cambios = r.cambios || [];
  return (
    <div style={{ borderBottom: '1px solid var(--borde)', padding: '10px 0' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'baseline' }}>
        <span className="tag t-MEDIO" style={{ textTransform: 'uppercase' }}>
          {r.tipo}
        </span>
        <b>{r.id_activo || ''}</b> — {r.nombre || ''}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--texto-suave)' }}>
          {new Date(r.fecha).toLocaleString('es-CO')} · {r.usuario}
        </span>
      </div>
      {cambios.length > 0 && (
        <div style={{ marginTop: 6, fontSize: 12 }}>
          {cambios.map((c, i) => (
            <div key={i}>
              <b>{c.campo}</b>: <span style={{ color: 'var(--texto-suave)' }}>{c.antes || '∅'}</span> →{' '}
              <span>{c.despues || '∅'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Bitacora() {
  const { roles, puedeEliminar } = useOutletContext() ?? {};
  const esAdmin = puedeEliminar || (roles ?? []).includes('Administrador');

  const { datos: cambios, cargando: cargandoCambios } = useApi(
    () => inventarioApi.bitacora({ limite: 80 }),
    [],
  );
  const { datos: accesos, cargando: cargandoAccesos, error: errorAccesos } = useApi(
    () => (esAdmin ? inventarioApi.accesosUnificado({ limite: 80 }) : inventarioApi.accesos()),
    [esAdmin],
  );
  const [verificando, setVerificando] = useState(false);
  const [resultadoVerif, setResultadoVerif] = useState(null);

  async function verificar() {
    setVerificando(true);
    setResultadoVerif(null);
    try {
      const r = await inventarioApi.verificarIntegridad();
      setResultadoVerif(r);
    } catch (e) {
      setResultadoVerif({ integra: false, error: e.message });
    } finally {
      setVerificando(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '4px 0 4px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Bitácora</h2>
        <button className="btn btn-sec" style={{ marginLeft: 'auto' }} onClick={verificar} disabled={verificando}>
          {verificando ? 'Verificando…' : 'Verificar integridad de la cadena'}
        </button>
      </div>
      {resultadoVerif && (
        <p style={{ fontWeight: 'bold', marginBottom: 12, color: resultadoVerif.integra ? 'var(--bajo)' : 'var(--crit)' }}>
          {resultadoVerif.integra
            ? `Cadena íntegra: ${resultadoVerif.total_verificado} registro(s) verificados sin alteraciones.`
            : `Cadena rota: se detectó una alteración en el registro #${resultadoVerif.registro_alterado ?? '?'}${resultadoVerif.error ? ` (${resultadoVerif.error})` : ''}.`}
        </p>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Registro de cambios del inventario (ISO/IEC 27001 · 8.15)</h2>
        <div className="cuerpo">
          {cargandoCambios ? (
            <p>Cargando…</p>
          ) : !cambios?.length ? (
            <p style={{ color: 'var(--texto-suave)' }}>Sin registros.</p>
          ) : (
            cambios.map((r, i) => <BitaItem key={i} r={r} />)
          )}
        </div>
      </div>

      <div className="card">
        <h2>{esAdmin ? 'Auditoría de accesos (Inventario + RBAC)' : 'Auditoría de accesos'}</h2>
        <div className="cuerpo">
          {cargandoAccesos ? (
            <p>Cargando…</p>
          ) : errorAccesos ? (
            <p style={{ color: 'var(--texto-suave)' }}>No disponible.</p>
          ) : !accesos?.length ? (
            <p style={{ color: 'var(--texto-suave)' }}>Sin registros de acceso.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  {esAdmin ? <th>Módulo</th> : null}
                  <th>Usuario</th>
                  <th>Acción</th>
                  <th>Recurso</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {accesos.map((a, i) => (
                  <tr key={i}>
                    <td>{new Date(a.fecha).toLocaleString('es-CO')}</td>
                    {esAdmin ? <td>{a.modulo || '—'}</td> : null}
                    <td>
                      <b>{a.usuario}</b>
                    </td>
                    <td>{a.tipo}</td>
                    <td>{a.recurso || a.detalle || '—'}</td>
                    <td>{a.ip || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

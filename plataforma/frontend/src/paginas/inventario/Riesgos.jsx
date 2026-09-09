import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

function nivelCelda(p, i) {
  const s = p * i;
  if (s >= 17) return 'CRIT';
  if (s >= 10) return 'ALTO';
  if (s >= 5) return 'MED';
  return 'BAJO';
}

export default function Riesgos() {
  const { puedeEditar } = useOutletContext() ?? {};
  const navegar = useNavigate();
  const { datos, cargando, error, recargar } = useApi(() => inventarioApi.riesgos(), []);
  const { datos: cob, cargando: cargandoCob } = useApi(() => inventarioApi.cobertura(), []);

  async function recalcular() {
    if (!window.confirm('¿Aplicar el nivel de riesgo calculado a todos los activos con valoración C-I-D? Quedará registrado en la bitácora.')) return;
    try {
      const r = await inventarioApi.recalcularRiesgos();
      alert(`Riesgos recalculados: ${r.actualizados || 0} activos actualizados.`);
      recargar();
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  }

  if (cargando) return <p>Cargando riesgos…</p>;
  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">No se pudo cargar el motor de riesgos ({error.message}).</div>
      </div>
    );
  }

  const activos = datos?.activos ?? [];
  const grid = {};
  activos.forEach((a) => {
    const k = `${a.probabilidad}-${a.impacto}`;
    (grid[k] = grid[k] || []).push(a);
  });
  const maxCobertura = Math.max(...(cob?.detalle ?? []).map((x) => x.num_activos), 1);
  const filasOrdenadas = [...activos].sort((a, b) => (b.score ?? -1) - (a.score ?? -1));

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '4px 0 16px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Valoración inherente</h2>
        <span style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
          Motor probabilidad × impacto del Inventario (ISO/IEC 27005). Para vulns, cobertura y PTR use{' '}
          <Link to="/gestion-riesgos">Gestión de Riesgos</Link>.
        </span>
        {puedeEditar && (
          <button className="btn btn-sec" style={{ marginLeft: 'auto' }} onClick={recalcular}>
            ↻ Recalcular y aplicar niveles
          </button>
        )}
      </div>

      <div className="detalle-grid">
        <div className="card">
          <h2>Matriz de riesgo (probabilidad × impacto)</h2>
          <div className="cuerpo">
            <table className="rmatrix" style={{ width: '100%', textAlign: 'center' }}>
              <thead>
                <tr>
                  <th colSpan={2}></th>
                  <th colSpan={5} style={{ fontWeight: 'normal', color: 'var(--texto-suave)' }}>
                    Impacto →
                  </th>
                </tr>
                <tr>
                  <th colSpan={2}></th>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <th key={i}>{i}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[5, 4, 3, 2, 1].map((p) => (
                  <tr key={p}>
                    {p === 5 && (
                      <th
                        rowSpan={5}
                        style={{
                          writingMode: 'vertical-rl',
                          transform: 'rotate(180deg)',
                          fontWeight: 'normal',
                          color: 'var(--texto-suave)',
                        }}
                      >
                        Probabilidad ↑
                      </th>
                    )}
                    <th>{p}</th>
                    {[1, 2, 3, 4, 5].map((i) => {
                      const arr = grid[`${p}-${i}`] || [];
                      const lvl = nivelCelda(p, i);
                      return (
                        <td
                          key={i}
                          className={`tag t-${lvl}`}
                          style={{ padding: 10 }}
                          title={arr.map((a) => a.id_activo).join(', ')}
                        >
                          {arr.length || ''}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--texto-suave)', marginTop: 8 }}>
              Cada celda muestra cuántos activos caen en esa combinación. Pasá el cursor para ver los IDs.
            </div>
          </div>
        </div>

        <div className="card">
          <h2>Cobertura de controles (ISO 27002)</h2>
          <div className="cuerpo">
            {cargandoCob ? (
              <p>Cargando…</p>
            ) : (
              <>
                <div style={{ fontSize: 13, marginBottom: 10 }}>
                  Controles en uso: <b>{cob.controles_usados}/{cob.total_controles}</b> · Activos con al menos un
                  control: <b>{cob.activos_con_control}/{cob.total_activos}</b> ({cob.cobertura_activos_pct}%)
                </div>
                {cob.detalle.slice(0, 12).map((x) => (
                  <div key={x.codigo} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 90, fontSize: 12 }} title={x.descripcion}>
                      {x.codigo}
                    </div>
                    <div style={{ flex: 1, background: 'var(--gris)', borderRadius: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${(x.num_activos / maxCobertura) * 100}%`,
                          background: 'var(--acento)',
                          color: '#fff',
                          fontSize: 11,
                          padding: '2px 6px',
                          minWidth: 18,
                        }}
                      >
                        {x.num_activos}
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Riesgo calculado por activo</h2>
        <div className="cuerpo" style={{ padding: 0 }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Activo</th>
                <th>Prob.</th>
                <th>Impacto</th>
                <th>Score</th>
                <th>Nivel calc.</th>
                <th>vs registrado</th>
              </tr>
            </thead>
            <tbody>
              {filasOrdenadas.map((a) => (
                <tr key={a.id} onClick={() => navegar(`/inventario/activos/${a.id}`)} style={{ cursor: 'pointer' }}>
                  <td>
                    <b>{a.id_activo}</b>
                  </td>
                  <td>{a.nombre}</td>
                  <td>{a.probabilidad}</td>
                  <td>{a.impacto ?? '—'}</td>
                  <td>{a.score ?? '—'}</td>
                  <td>
                    <span className={`tag t-${a.nivel}`}>{a.nivel}</span>
                  </td>
                  <td>
                    {a.nivel !== a.nivel_registrado ? (
                      <span style={{ color: 'var(--alto)', fontSize: 11 }}>≠ registrado ({a.nivel_registrado})</span>
                    ) : (
                      <span style={{ color: 'var(--bajo)', fontSize: 11 }}>✓</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

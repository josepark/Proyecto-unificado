import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { mensajeErrorRbac } from './rbacUtil';

export default function Inicio() {
  const { datos: d, cargando, error } = useApi(() => rbacApi.inicio(), []);

  if (cargando) return <p>Cargando…</p>;
  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('el tablero de control de acceso', error)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 style={{ margin: '4px 0 4px', color: 'var(--verde-profundo)' }}>Tablero de control de acceso</h2>
      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Estado actual del control de acceso basado en roles (RBAC) del SUIIN.{' '}
        <a href="/rbac/api/export/accesos_usuarios.csv" style={{ fontSize: 13 }}>
          Exportar accesos efectivos (CSV)
        </a>
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: 13,
          marginBottom: 20,
        }}
      >
        <Kpi n={d.stats.roles} l="Roles definidos" />
        <Kpi n={d.stats.sistemas} l="Sistemas y recursos" />
        <Kpi n={d.stats.accesos} l="Accesos definidos en la matriz" />
        <Kpi n={d.stats.usuarios} l="Usuarios activos" />
      </div>

      <div className="detalle-grid">
        <div className="card">
          <h2>Roles activos por nivel de riesgo (MITRE ATT&amp;CK)</h2>
          <div className="cuerpo">
            {d.riesgo.map((r) => (
              <div key={r.nombre} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 50, fontSize: 12 }}>{r.nombre}</div>
                <div style={{ flex: 1, background: 'var(--gris)', borderRadius: 4, overflow: 'hidden', height: 18 }}>
                  <div
                    style={{
                      width: `${d.max_riesgo ? (r.n / d.max_riesgo) * 100 : 0}%`,
                      background: r.color,
                      height: '100%',
                    }}
                  />
                </div>
                <div style={{ width: 24, fontSize: 12, textAlign: 'right' }}>{r.n}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Cumplimiento MFA</h2>
          <div className="cuerpo" style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
            <div
              role="img"
              aria-label={`${d.mfa_pct} por ciento de cumplimiento MFA`}
              style={{
                width: 90,
                height: 90,
                borderRadius: '50%',
                flexShrink: 0,
                background: `conic-gradient(var(--acento) 0 ${d.mfa_pct}%, var(--borde) 0 100%)`,
              }}
            />
            <div>
              <div style={{ fontSize: 26, fontWeight: 'bold', color: 'var(--verde-profundo)' }}>{d.mfa_pct}%</div>
              <div style={{ fontSize: 12, color: 'var(--texto-suave)' }}>
                {d.mfa_total ? `${d.mfa_ok} de ${d.mfa_total} usuarios con MFA exigido, activo` : 'Ningún usuario activo exige MFA'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {d.proximos_vencimientos.length > 0 && (
        <>
          <div
            style={{
              background: '#fdefe0',
              color: '#8a5810',
              border: '1px solid #f0d9b5',
              borderRadius: 8,
              padding: '10px 14px',
              fontSize: 13,
              marginBottom: 14,
            }}
          >
            {d.proximos_vencimientos.length} vencimiento(s) en los próximos {d.dias_alerta} días — revíselos antes de
            que el sistema los suspenda/retire automáticamente.
          </div>
          <div className="card" style={{ marginBottom: 20 }}>
            <h2>Vencimientos próximos ({d.dias_alerta} días)</h2>
            <div className="cuerpo">
              <table>
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Persona</th>
                    <th>Contexto</th>
                    <th>Vence</th>
                    <th className="num">Días</th>
                  </tr>
                </thead>
                <tbody>
                  {d.proximos_vencimientos.map((v, i) => (
                    <tr key={i} style={v.dias <= 2 ? { background: '#fdecea' } : undefined}>
                      <td>{v.tipo}</td>
                      <td>{v.nombre}</td>
                      <td>{v.contexto}</td>
                      <td>{v.fecha_fin}</td>
                      <td className="num" style={{ color: v.dias <= 2 ? 'var(--alto)' : 'var(--medio)', fontWeight: v.dias <= 2 ? 'bold' : 'normal' }}>
                        {v.dias}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <div className="detalle-grid">
        <div className="card">
          <h2>Alertas de cumplimiento MFA</h2>
          <div className="cuerpo">
            {d.alertas_mfa.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Rol</th>
                    <th>MFA exigido</th>
                    <th>MFA activo</th>
                  </tr>
                </thead>
                <tbody>
                  {d.alertas_mfa.map((a) => (
                    <tr key={a.id}>
                      <td>{a.nombre}</td>
                      <td>{a.rol}</td>
                      <td>{a.mfa_requerido}</td>
                      <td style={{ color: 'var(--crit)' }}>{a.mfa_activo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ fontSize: 13, margin: 0 }}>
                Sin incumplimientos: todos los usuarios activos cuyo rol exige MFA lo tienen habilitado.
              </p>
            )}
          </div>
        </div>

        <div className="card">
          <h2>Roles críticos (accesos nivel Admin)</h2>
          <div className="cuerpo">
            <table>
              <thead>
                <tr>
                  <th>Rol</th>
                  <th>Denominación</th>
                  <th className="num">Sistemas con nivel A</th>
                </tr>
              </thead>
              <tbody>
                {d.criticos.map((r) => (
                  <tr key={r.abreviatura}>
                    <td>
                      <b>{r.abreviatura}</b>
                    </td>
                    <td>{r.denominacion}</td>
                    <td className="num">{r.n_admin}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 8 }}>
              Revisión trimestral obligatoria (POL-SI-002).
            </p>
          </div>
        </div>
      </div>

      <div className="detalle-grid">
        <div className="card">
          <h2>Accesos temporales vigentes</h2>
          <div className="cuerpo">
            {d.temporales.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Rol</th>
                    <th>Fecha fin</th>
                  </tr>
                </thead>
                <tbody>
                  {d.temporales.map((t, i) => (
                    <tr key={i}>
                      <td>{t.nombre}</td>
                      <td>{t.rol}</td>
                      <td>{t.fecha_fin || 'Sin definir — corregir'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ fontSize: 13, margin: 0 }}>No hay accesos temporales vigentes.</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2>Accesos revocados</h2>
          <div className="cuerpo">
            {d.revocados.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Rol</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {d.revocados.map((t, i) => (
                    <tr key={i}>
                      <td>{t.nombre}</td>
                      <td>{t.rol}</td>
                      <td>{t.notas}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ fontSize: 13, margin: 0 }}>Sin revocaciones registradas.</p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Últimos movimientos (bitácora)</h2>
        <div className="cuerpo">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Entidad</th>
                <th>Acción</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {d.log.map((l) => (
                <tr key={l.id}>
                  <td>{l.fecha}</td>
                  <td>{l.entidad}</td>
                  <td>{l.accion}</td>
                  <td>{l.detalle}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 10 }}>
            <Link to="/rbac/auditoria">Ver bitácora completa →</Link>
          </p>
        </div>
      </div>
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

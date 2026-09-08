import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

export default function PanelEjecutivo() {
  const { datos: d, cargando, error } = useApi(() => inventarioApi.panelEjecutivo(), []);

  if (cargando) return <p>Cargando panel ejecutivo…</p>;
  if (error) return <div className="card"><div className="cuerpo">No se pudo cargar el panel ({error.message}).</div></div>;

  const c = d.completitud;
  const madurez = Math.round((c.valoracion_cid + c.propietario + c.centro_datos + c.con_control) / 4);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Panel ejecutivo</h2>
        <a className="btn btn-sec" href="/api/reporte-consolidado.pdf" target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
          ⬇ Reporte consolidado (PDF)
        </a>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 13, marginBottom: 20 }}>
        <Kpi n={d.total_activos} l="Activos totales" />
        <Kpi n={`${c.valoracion_cid}%`} l="Con valoración C-I-D" />
        <Kpi n={`${c.propietario}%`} l="Con propietario" />
        <Kpi n={`${c.con_control}%`} l="Con control asociado" />
        <Kpi n={d.cambios_30dias} l="Cambios (30 días)" />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Madurez del SGSI</h2>
        <div className="cuerpo">
          <div style={{ fontSize: 32, fontWeight: 'bold', color: 'var(--verde-profundo)' }}>{madurez}%</div>
          <div style={{ background: 'var(--borde)', borderRadius: 8, height: 10, marginTop: 8 }}>
            <div style={{ width: `${madurez}%`, background: 'var(--acento)', height: '100%', borderRadius: 8 }} />
          </div>
          <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 8 }}>
            Índice compuesto de completitud del inventario y cobertura de controles.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>Cumplimiento de Control de Acceso (RBAC · SUIIN-SGSI-MCA-001)</h2>
        <div className="cuerpo">
          {!d.rbac ? (
            <p style={{ color: '#9a1f1f' }}>El módulo RBAC no respondió — estos indicadores no están disponibles en este momento.</p>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 13, marginBottom: 16 }}>
                <Kpi n={`${d.rbac.mfa_pct}%`} l="Cumplimiento MFA" crit={d.rbac.mfa_pct < 100} />
                <Kpi n={d.rbac.roles_total} l="Roles MCA" />
                <Kpi n={d.rbac.sistemas_total} l="Sistemas en la matriz" />
                <Kpi n={d.rbac.excepciones_vigentes} l="Excepciones vigentes" crit={d.rbac.excepciones_vencidas > 0} />
                <Kpi n={d.rbac.roles_certificacion_vencida} l="Roles con certificación vencida" crit={d.rbac.roles_certificacion_vencida > 0} />
                <Kpi n={d.rbac.pendientes_total ?? 0} l="Pendientes RBAC (total)" crit={(d.rbac.pendientes_total ?? 0) > 0} />
              </div>
              {d.rbac.desglose_pendientes && (
                <div style={{ fontSize: 13, marginBottom: 12 }}>
                  <strong>Desglose de pendientes</strong>
                  <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                    <li>Vencimientos próximos (7 d): <b>{d.rbac.desglose_pendientes.proximos_vencimientos}</b></li>
                    <li>MFA incumplido: <b>{d.rbac.desglose_pendientes.alertas_mfa}</b></li>
                    <li>Certificación de rol vencida: <b>{d.rbac.desglose_pendientes.roles_certificacion_vencida}</b></li>
                    <li>Excepciones vencidas: <b>{d.rbac.desglose_pendientes.excepciones_vencidas}</b></li>
                  </ul>
                  <Link to="/rbac/inicio" style={{ fontSize: 12 }}>Ir al tablero RBAC →</Link>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {d.datacenters?.length > 0 && (
        <div className="card">
          <h2>Activos por centro de datos</h2>
          <div className="cuerpo" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Sede</th>
                  <th className="num">Activos</th>
                  <th className="num">Críticos</th>
                  <th className="num">Infra sin rack</th>
                </tr>
              </thead>
              <tbody>
                {d.datacenters.map((dc) => (
                  <tr key={dc.id}>
                    <td><Link to={`/inventario/centro-datos/datacenters/${dc.id}/editar`}>{dc.codigo}</Link></td>
                    <td>{dc.nombre}</td>
                    <td className="num">{dc.total_activos}</td>
                    <td className="num" style={{ color: dc.criticos ? 'var(--crit)' : undefined }}>{dc.criticos}</td>
                    <td className="num">{dc.sin_rack}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: 12, margin: '8px 14px 0' }}>
              <Link to="/inventario/centro-datos">Ver mapa y diagramas →</Link>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ n, l, crit }) {
  return (
    <div className="kpi" style={crit ? { borderLeftColor: 'var(--crit)' } : undefined}>
      <div className="n" style={crit ? { color: 'var(--crit)' } : undefined}>{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}

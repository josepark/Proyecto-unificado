import { Link } from 'react-router-dom';
import { inventarioApi } from '../api/inventario';
import { MSG_SYNC_OPERADOR, pendientesSync } from '../lib/integracionUi';

function KpiSync({ valor, etiqueta, critico }) {
  const esNumero = typeof valor === 'number';
  return (
    <div
      className="card"
      style={{
        margin: 0,
        textAlign: 'center',
        borderColor: critico && esNumero && valor > 0 ? 'var(--alto)' : undefined,
      }}
    >
      <div className="cuerpo" style={{ padding: '10px 8px' }}>
        <div
          style={{
            fontSize: 20,
            fontWeight: 'bold',
            color: critico && esNumero && valor > 0 ? 'var(--alto)' : 'var(--verde-profundo)',
          }}
        >
          {valor}
        </div>
        <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 4 }}>{etiqueta}</div>
      </div>
    </div>
  );
}

/** Panel operativo Inventario ↔ Riesgos (Ola 6). */
export default function PanelVinculacion({
  vinculacion,
  detalle,
  compacto = false,
  puedeEditar = false,
  ocultarSiOk = false,
}) {
  const res = detalle?.resumen ?? vinculacion;
  if (!res?.disponible) {
    return (
      <div className="card" style={{ marginBottom: 14 }}>
        <div className="cuerpo" style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
          No se pudo verificar la sincronización — Gestión de Riesgos no responde.
          {' '}<Link to="/inventario/alertas">Centro de alertas →</Link>
        </div>
      </div>
    );
  }

  const sinEspejo = res.sin_espejo_riesgos ?? 0;
  const huerfanos = res.huerfanos_riesgos ?? 0;
  const ok = detalle?.sincronizacion_ok ?? (sinEspejo === 0 && huerfanos === 0);
  if (ocultarSiOk && ok) return null;

  const pct = detalle?.porcentaje_vinculados
    ?? (res.total_inventario ? Math.round((res.vinculados / res.total_inventario) * 1000) / 10 : 100);

  const listaSinEspejo = detalle?.sin_espejo ?? [];
  const listaHuerfanos = detalle?.huerfanos_riesgos ?? [];
  const pend = pendientesSync(res);

  return (
    <div className="card" style={{ marginBottom: 14, borderColor: ok ? undefined : 'var(--alto)' }}>
      <h2>
        Sincronización Inventario ↔ Riesgos
        {ok ? (
          <span style={{ float: 'right', fontSize: 12, color: 'var(--bajo)', fontWeight: 'normal' }}>
            ✓ al día
          </span>
        ) : null}
      </h2>
      <div className="cuerpo">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
            gap: 8,
            marginBottom: compacto && ok ? 0 : 12,
          }}
        >
          <KpiSync valor={`${res.vinculados}/${res.total_inventario}`} etiqueta={`Vinculados (${pct}%)`} />
          <KpiSync valor={sinEspejo} etiqueta="Sin espejo" critico />
          <KpiSync valor={huerfanos} etiqueta="Huérfanos en Riesgos" critico />
        </div>

        {!ok && (
          <p style={{ fontSize: 13, margin: '0 0 10px' }}>
            {puedeEditar ? MSG_SYNC_OPERADOR : (
              <>Hay activos desalineados entre Inventario y Gestión de Riesgos. Contacte al administrador del SGSI.</>
            )}
          </p>
        )}

        {(!compacto || pend > 0) && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: compacto ? 0 : 12 }}>
            <a className="btn btn-sec" style={{ fontSize: 12 }} href={inventarioApi.exportarVinculacionCsv('todos')}>
              ↓ CSV completo
            </a>
            {sinEspejo > 0 ? (
              <a className="btn btn-sec" style={{ fontSize: 12 }} href={inventarioApi.exportarVinculacionCsv('sin_espejo')}>
                ↓ Sin espejo ({sinEspejo})
              </a>
            ) : null}
            {huerfanos > 0 ? (
              <a className="btn btn-sec" style={{ fontSize: 12 }} href={inventarioApi.exportarVinculacionCsv('huerfanos')}>
                ↓ Huérfanos ({huerfanos})
              </a>
            ) : null}
            {sinEspejo > 0 ? (
              <Link to="/inventario/dashboard?solo_sin_espejo=1" style={{ fontSize: 12, alignSelf: 'center' }}>
                Ver en Dashboard →
              </Link>
            ) : null}
            {huerfanos > 0 ? (
              <Link to="/gestion-riesgos/activos?huerfanos=1" style={{ fontSize: 12, alignSelf: 'center' }}>
                Huérfanos en Riesgos →
              </Link>
            ) : null}
          </div>
        )}

        {!compacto && listaSinEspejo.length > 0 && (
          <>
            <h3 style={{ fontSize: 13, margin: '12px 0 6px' }}>Activos sin espejo en Riesgos</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Activo</th>
                  <th>Clase</th>
                </tr>
              </thead>
              <tbody>
                {listaSinEspejo.slice(0, 8).map((a) => (
                  <tr key={a.inventario_id}>
                    <td>
                      <Link to={`/inventario/activos/${a.inventario_id}`}>{a.id_activo}</Link>
                    </td>
                    <td>{a.nombre}</td>
                    <td>{a.clase}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {listaSinEspejo.length > 8 ? (
              <p style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 6 }}>
                +{listaSinEspejo.length - 8} más en el CSV
              </p>
            ) : null}
          </>
        )}

        {!compacto && listaHuerfanos.length > 0 && (
          <>
            <h3 style={{ fontSize: 13, margin: '12px 0 6px' }}>Huérfanos solo en Riesgos</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Activo</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {listaHuerfanos.slice(0, 8).map((a) => (
                  <tr key={a.riesgos_id}>
                    <td>
                      <Link to={`/gestion-riesgos/activos/${a.riesgos_id}`}>{a.id_activo}</Link>
                    </td>
                    <td>{a.nombre}</td>
                    <td>{a.ip_principal || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}

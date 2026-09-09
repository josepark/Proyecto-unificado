import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

const SEV_CLASE = { crit: 't-CRIT', alto: 't-ALTO', medio: 't-MEDIO', bajo: 't-BAJO' };
const SEV_TEXTO = { crit: 'Crítico', alto: 'Alto', medio: 'Medio', bajo: 'Bajo' };

function GrupoInventario({ grupo }) {
  if (!grupo.items.length) return null;
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <h2>
        {grupo.titulo} <span style={{ float: 'right' }}>{grupo.items.length}</span>
      </h2>
      <div className="cuerpo">
        {grupo.items.map((it, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'center',
              padding: '8px 0',
              borderTop: i > 0 ? '1px solid var(--borde)' : 'none',
            }}
          >
            <b style={{ minWidth: 78 }}>{it.id_activo}</b>
            <span style={{ flex: 1, color: '#444' }}>{it.nombre} — {it.detalle}</span>
            <span
              className={`tag ${SEV_CLASE[it.severidad] || ''}`}
              style={{ textTransform: 'uppercase' }}
            >
              {SEV_TEXTO[it.severidad] || it.severidad}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SeccionRbac({ rbac }) {
  if (!rbac?.disponible) {
    return (
      <div className="card" style={{ marginBottom: 14 }}>
        <h2>Matriz RBAC</h2>
        <div className="cuerpo" style={{ color: 'var(--texto-suave)' }}>
          Módulo RBAC no disponible en este momento.
        </div>
      </div>
    );
  }
  const d = rbac.desglose_pendientes || {};
  const filas = [
    ['Vencimientos próximos (7 d)', d.proximos_vencimientos],
    ['MFA incumplido', d.alertas_mfa],
    ['Certificación de rol vencida', d.roles_certificacion_vencida],
    ['Excepciones vencidas', d.excepciones_vencidas],
  ].filter(([, n]) => n > 0);
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <h2>
        Matriz RBAC <span style={{ float: 'right' }}>{rbac.pendientes_total}</span>
      </h2>
      <div className="cuerpo">
        {filas.length === 0 ? (
          <p style={{ margin: 0 }}>Sin pendientes operativos en RBAC.</p>
        ) : (
          filas.map(([titulo, n]) => (
            <div key={titulo} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>{titulo}</span>
              <b>{n}</b>
            </div>
          ))
        )}
        <Link to="/rbac/inicio" style={{ fontSize: 12 }}>Ir al tablero RBAC →</Link>
      </div>
    </div>
  );
}

function SeccionRiesgos({ riesgos }) {
  if (!riesgos?.disponible) {
    return (
      <div className="card" style={{ marginBottom: 14 }}>
        <h2>Gestión de Riesgos</h2>
        <div className="cuerpo" style={{ color: 'var(--texto-suave)' }}>
          Módulo de Riesgos no disponible en este momento.
        </div>
      </div>
    );
  }
  const filas = [
    ['Acciones PTR vencidas', riesgos.total_vencidas],
    ['Acciones PTR por vencer', riesgos.total_por_vencer],
    ['Activos sin cobertura', riesgos.activos_sin_cobertura],
    ['Vulnerabilidades críticas', riesgos.vulnerabilidades_criticas],
    ['Activos comprometidos (Red Team)', riesgos.activos_comprometidos],
  ].filter(([, n]) => n > 0);
  const total = filas.reduce((s, [, n]) => s + n, 0);
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <h2>
        Gestión de Riesgos <span style={{ float: 'right' }}>{total}</span>
      </h2>
      <div className="cuerpo">
        {filas.length === 0 ? (
          <p style={{ margin: 0 }}>Sin alertas operativas en Riesgos.</p>
        ) : (
          filas.map(([titulo, n]) => (
            <div key={titulo} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>{titulo}</span>
              <b>{n}</b>
            </div>
          ))
        )}
        <Link to="/gestion-riesgos" style={{ fontSize: 12 }}>Ir a Gestión de Riesgos →</Link>
      </div>
    </div>
  );
}

export default function Alertas() {
  const { datos, cargando, error } = useApi(() => inventarioApi.alertasUnificadas(), []);

  if (cargando) return <p>Cargando alertas…</p>;
  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">No se pudieron cargar las alertas ({error.message}).</div>
      </div>
    );
  }

  const inv = datos?.inventario ?? {};
  const gruposInv = (inv.grupos ?? []).filter((g) => g.items.length > 0);
  const vacio = gruposInv.length === 0
    && !(datos?.rbac?.pendientes_total > 0)
    && !(datos?.riesgos?.disponible && (
      (datos.riesgos.total_vencidas || 0)
      + (datos.riesgos.total_por_vencer || 0)
      + (datos.riesgos.activos_sin_cobertura || 0)
      + (datos.riesgos.vulnerabilidades_criticas || 0)
      + (datos.riesgos.activos_comprometidos || 0)
    ) > 0);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, margin: '4px 0 16px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Centro de alertas</h2>
        <span style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
          Inventario · RBAC · Riesgos — {datos?.total_consolidado ?? 0} señales
        </span>
      </div>

      {vacio && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cuerpo">Sin alertas activas en ningún módulo.</div>
        </div>
      )}

      {gruposInv.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, color: 'var(--verde-profundo)', margin: '0 0 8px' }}>Inventario</h3>
          {gruposInv.map((g) => (
            <GrupoInventario key={g.clave} grupo={g} />
          ))}
        </>
      )}

      <h3 style={{ fontSize: 14, color: 'var(--verde-profundo)', margin: '16px 0 8px' }}>Integración</h3>
      <SeccionRbac rbac={datos?.rbac} />
      <SeccionRiesgos riesgos={datos?.riesgos} />
    </div>
  );
}

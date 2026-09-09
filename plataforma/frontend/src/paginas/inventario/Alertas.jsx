import { Link } from 'react-router-dom';
import { useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { eventosApi } from '../../api/client';
import PanelVinculacion from '../../componentes/PanelVinculacion';
import { pendientesSync } from '../../lib/integracionUi';

const SEV_CLASE = { crit: 't-CRIT', alto: 't-ALTO', medio: 't-MEDIO', bajo: 't-BAJO' };
const SEV_TEXTO = { crit: 'Crítico', alto: 'Alto', medio: 'Medio', bajo: 'Bajo' };

function KpiResumen({ valor, etiqueta, critico, href }) {
  const contenido = (
    <>
      <div style={{ fontSize: 22, fontWeight: 'bold', color: critico && valor > 0 ? 'var(--crit)' : 'var(--verde-profundo)' }}>
        {valor}
      </div>
      <div style={{ fontSize: 11, color: 'var(--texto-suave)', marginTop: 4 }}>{etiqueta}</div>
    </>
  );
  return (
    <div
      className="card"
      style={{
        margin: 0,
        textAlign: 'center',
        borderColor: critico && valor > 0 ? 'var(--crit)' : undefined,
      }}
    >
      <div className="cuerpo" style={{ padding: '12px 10px' }}>
        {href ? (
          <Link to={href} style={{ textDecoration: 'none', color: 'inherit' }}>
            {contenido}
          </Link>
        ) : contenido}
      </div>
    </div>
  );
}

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
            key={`${it.id}-${it.detalle}`}
            style={{
              display: 'flex',
              gap: 10,
              alignItems: 'center',
              padding: '8px 0',
              borderTop: i > 0 ? '1px solid var(--borde)' : 'none',
            }}
          >
            {it.id ? (
              <Link to={`/inventario/activos/${it.id}`} style={{ minWidth: 78, fontWeight: 'bold' }}>
                {it.id_activo}
              </Link>
            ) : (
              <b style={{ minWidth: 78 }}>{it.id_activo}</b>
            )}
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
        <div className="cuerpo" style={{ color: 'var(--texto-suave)', fontSize: 13 }}>
          Módulo RBAC no disponible en este momento.
        </div>
      </div>
    );
  }
  if (!(rbac.pendientes_total > 0)) return null;

  const d = rbac.desglose_pendientes || {};
  const filas = [
    ['Vencimientos próximos (7 d)', d.proximos_vencimientos, '/rbac/inicio'],
    ['MFA incumplido', d.alertas_mfa, '/rbac/inicio'],
    ['Certificación de rol vencida', d.roles_certificacion_vencida, '/rbac/inicio'],
    ['Excepciones vencidas', d.excepciones_vencidas, '/rbac/inicio'],
  ].filter(([, n]) => n > 0);

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <h2>
        Matriz RBAC <span style={{ float: 'right' }}>{rbac.pendientes_total}</span>
      </h2>
      <div className="cuerpo">
        {filas.map(([titulo, n, ruta]) => (
          <div key={titulo} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
            <Link to={ruta} style={{ color: 'inherit' }}>{titulo}</Link>
            <b>{n}</b>
          </div>
        ))}
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
        <div className="cuerpo" style={{ color: 'var(--texto-suave)', fontSize: 13 }}>
          Módulo de Riesgos no disponible en este momento.
        </div>
      </div>
    );
  }

  const filas = [
    ['Acciones PTR vencidas', riesgos.total_vencidas, '/gestion-riesgos/plan-tratamiento'],
    ['Acciones PTR por vencer', riesgos.total_por_vencer, '/gestion-riesgos/plan-tratamiento'],
    ['Activos sin cobertura', riesgos.activos_sin_cobertura, '/gestion-riesgos/activos'],
    ['Vulnerabilidades críticas', riesgos.vulnerabilidades_criticas, '/gestion-riesgos/vulnerabilidades'],
    ['Activos comprometidos (Red Team)', riesgos.activos_comprometidos, '/gestion-riesgos/activos'],
  ].filter(([, n]) => n > 0);

  if (!filas.length) return null;

  const total = filas.reduce((s, [, n]) => s + n, 0);
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <h2>
        Gestión de Riesgos (operativo) <span style={{ float: 'right' }}>{total}</span>
      </h2>
      <div className="cuerpo">
        {filas.map(([titulo, n, ruta]) => (
          <div key={titulo} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
            <Link to={ruta} style={{ color: 'inherit' }}>{titulo}</Link>
            <b>{n}</b>
          </div>
        ))}
        <Link to="/gestion-riesgos" style={{ fontSize: 12 }}>Ir a Gestión de Riesgos →</Link>
      </div>
    </div>
  );
}

export default function Alertas() {
  const { recargarAlertasUnificadas, puedeEditar } = useOutletContext() ?? {};
  const { datos, cargando, error, recargar } = useApi(() => inventarioApi.alertasUnificadas(), []);

  function actualizarTodo() {
    recargar();
    recargarAlertasUnificadas?.();
    eventosApi.dispatchEvent(new CustomEvent('alertas-actualizadas'));
  }

  if (cargando && !datos) return <p>Cargando alertas…</p>;
  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">No se pudieron cargar las alertas ({error.message}).</div>
      </div>
    );
  }

  const inv = datos?.inventario ?? {};
  const res = datos?.resumen ?? {};
  const gruposInv = (inv.grupos ?? []).filter((g) => g.items.length > 0);
  const rbac = datos?.rbac;
  const riesgos = datos?.riesgos;
  const vinculacion = datos?.vinculacion;
  const syncPend = res.sync ?? pendientesSync(vinculacion);
  const hayIntegracion = (
    !rbac?.disponible
    || rbac.pendientes_total > 0
    || !riesgos?.disponible
    || (riesgos?.total_vencidas || 0)
      + (riesgos?.total_por_vencer || 0)
      + (riesgos?.activos_sin_cobertura || 0)
      + (riesgos?.vulnerabilidades_criticas || 0)
      + (riesgos?.activos_comprometidos || 0) > 0
  );
  const vacio = (datos?.total_consolidado ?? 0) === 0
    && rbac?.disponible
    && riesgos?.disponible
    && vinculacion?.disponible;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0 16px', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Centro de alertas</h2>
        <span style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
          Inventario · RBAC · Riesgos · Sync
        </span>
        <button
          type="button"
          className="btn btn-sec"
          style={{ marginLeft: 'auto', fontSize: 12 }}
          onClick={actualizarTodo}
          disabled={cargando}
        >
          {cargando ? 'Actualizando…' : '↻ Actualizar'}
        </button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
          gap: 10,
          marginBottom: 18,
        }}
      >
        <KpiResumen
          valor={datos?.total_consolidado ?? 0}
          etiqueta="Total señales"
          critico={(res.inventario_criticas ?? 0) > 0 || syncPend > 0}
        />
        <KpiResumen valor={res.inventario ?? 0} etiqueta="Inventario" critico={res.inventario_criticas > 0} href="#inv" />
        <KpiResumen valor={res.rbac ?? 0} etiqueta="RBAC" critico={res.rbac > 0} href="/rbac/inicio" />
        <KpiResumen valor={res.riesgos ?? 0} etiqueta="Riesgos (ops.)" critico={res.riesgos > 0} href="/gestion-riesgos" />
        <KpiResumen valor={syncPend} etiqueta="Sync" critico={syncPend > 0} href="/inventario/riesgos" />
      </div>

      <PanelVinculacion vinculacion={vinculacion} compacto puedeEditar={puedeEditar} />

      {vacio && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="cuerpo">Sin alertas activas en ningún módulo. Todos los indicadores operativos están en verde.</div>
        </div>
      )}

      {gruposInv.length > 0 && (
        <>
          <h3 id="inv" style={{ fontSize: 14, color: 'var(--verde-profundo)', margin: '0 0 8px' }}>
            Inventario
            {res.inventario_criticas > 0 && (
              <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--crit)' }}>
                ({res.inventario_criticas} críticas)
              </span>
            )}
          </h3>
          {gruposInv.map((g) => (
            <GrupoInventario key={g.clave} grupo={g} />
          ))}
        </>
      )}

      {hayIntegracion && (
        <>
          <h3 style={{ fontSize: 14, color: 'var(--verde-profundo)', margin: '16px 0 8px' }}>Integración</h3>
          <SeccionRbac rbac={rbac} />
          <SeccionRiesgos riesgos={riesgos} />
        </>
      )}
    </div>
  );
}

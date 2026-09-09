import { NavLink, Outlet, useOutletContext } from 'react-router-dom';

import { pendientesSync } from '../lib/integracionUi';

const PESTANAS = [
  { to: 'dashboard', etiqueta: 'Dashboard' },
  { to: 'panel-ejecutivo', etiqueta: 'Panel ejecutivo' },
  { to: 'riesgos', etiqueta: 'Valoración inherente' },
  { to: 'alertas', etiqueta: 'Centro de alertas' },
  { to: 'centro-datos', etiqueta: 'Centro de datos' },
  { to: 'clases', etiqueta: 'Clases de activo' },
  { to: 'bitacora', etiqueta: 'Bitácora' },
];

export default function ModuloInventario() {
  const { alertasUnificadas, ...contexto } = useOutletContext() ?? {};
  const vinc = alertasUnificadas?.vinculacion;
  const pendientesSyncCount = pendientesSync(vinc);
  const totalAlertas = alertasUnificadas?.total_consolidado ?? 0;

  return (
    <div>
      <div className="tabs">
        {PESTANAS.map((p) => (
          <NavLink key={p.to} to={p.to} className={({ isActive }) => `tab${isActive ? ' activa' : ''}`}>
            {p.etiqueta}
            {p.to === 'alertas' && totalAlertas > 0 ? (
              <span className="badge-modulo" style={{ marginLeft: 6, verticalAlign: 'middle' }}>
                {totalAlertas}
              </span>
            ) : null}
            {p.to === 'riesgos' && pendientesSyncCount > 0 ? (
              <span
                className="badge-modulo"
                style={{ marginLeft: 6, verticalAlign: 'middle', background: 'var(--alto)' }}
                title="Pendientes de sincronización Inventario ↔ Riesgos"
              >
                ↻{pendientesSyncCount}
              </span>
            ) : null}
          </NavLink>
        ))}
      </div>
      <Outlet context={contexto} />
    </div>
  );
}

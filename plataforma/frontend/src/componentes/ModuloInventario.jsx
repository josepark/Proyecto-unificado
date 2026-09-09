import { NavLink, Outlet, useOutletContext } from 'react-router-dom';

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
  const totalAlertas = alertasUnificadas?.total_consolidado ?? 0;
  const vinc = alertasUnificadas?.vinculacion;
  const pendientesSync = (vinc?.sin_espejo_riesgos ?? 0) + (vinc?.huerfanos_riesgos ?? 0);

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
            {p.to === 'riesgos' && pendientesSync > 0 ? (
              <span
                className="badge-modulo"
                style={{ marginLeft: 6, verticalAlign: 'middle', background: 'var(--alto)' }}
                title="Activos pendientes de sincronizar con Gestión de Riesgos"
              >
                {pendientesSync}
              </span>
            ) : null}
          </NavLink>
        ))}
      </div>
      <Outlet context={contexto} />
    </div>
  );
}

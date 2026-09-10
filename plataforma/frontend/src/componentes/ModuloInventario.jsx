import { Link, NavLink, Outlet, useOutletContext, useLocation } from 'react-router-dom';

import { pendientesSync } from '../lib/integracionUi';
import { tieneModulo } from '../lib/modulosPlataforma';

/** Rutas consultables sin sesión (API AllowAny). El resto exige login. */
const RUTAS_PUBLICAS = new Set(['panel-ejecutivo']);

function rutaInventarioPublica(pathname) {
  const match = pathname.match(/\/inventario\/([^/]+)/);
  return Boolean(match && RUTAS_PUBLICAS.has(match[1]));
}

const PESTANAS_BASE = [
  { to: 'dashboard', etiqueta: 'Dashboard' },
  { to: 'panel-ejecutivo', etiqueta: 'Panel ejecutivo' },
  { to: 'riesgos', etiqueta: 'Valoración inherente' },
  { to: 'alertas', etiqueta: 'Centro de alertas' },
  { to: 'centro-datos', etiqueta: 'Centro de datos' },
  { to: 'clases', etiqueta: 'Clases de activo' },
  { to: 'bitacora', etiqueta: 'Bitácora' },
];

const PESTANA_USUARIOS = { to: 'usuarios', etiqueta: 'Cuentas de acceso' };

export default function ModuloInventario() {
  const { alertasUnificadas, puedeEliminar, modulos, autenticado, ...resto } = useOutletContext() ?? {};
  const ubicacion = useLocation();
  const pestanas = puedeEliminar ? [...PESTANAS_BASE, PESTANA_USUARIOS] : PESTANAS_BASE;
  const gestionUsuarios = ubicacion.pathname.includes('/inventario/usuarios');
  const esPublica = rutaInventarioPublica(ubicacion.pathname);
  const sinInventario = autenticado && !tieneModulo(modulos, 'inventario', { autenticado });
  const rutaTrasLogin = `${ubicacion.pathname}${ubicacion.search}`;

  if (!autenticado && !esPublica) {
    return (
      <div className="modulo-restringido">
        <p>
          El <b>Inventario de activos</b> requiere iniciar sesión para consultar activos, alertas y catálogos.
          El <Link to="/inventario/panel-ejecutivo">panel ejecutivo</Link> permanece disponible sin sesión.
        </p>
        <Link className="btn btn-primary" to={`/login?next=${encodeURIComponent(rutaTrasLogin)}`}>
          Iniciar sesión
        </Link>
      </div>
    );
  }

  if (sinInventario && !gestionUsuarios) {
    return (
      <div className="card">
        <div className="cuerpo">
          Su cuenta no tiene acceso al proyecto <b>Inventario de activos</b>.
        </div>
      </div>
    );
  }
  const vinc = alertasUnificadas?.vinculacion;
  const pendientesSyncCount = pendientesSync(vinc);
  const totalAlertas = alertasUnificadas?.total_consolidado ?? 0;

  return (
    <div>
      <div className="tabs">
        {pestanas.map((p) => (
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
      <Outlet key={resto.usuario ?? 'anon'} context={{ ...resto, alertasUnificadas, puedeEliminar, modulos, autenticado }} />
    </div>
  );
}

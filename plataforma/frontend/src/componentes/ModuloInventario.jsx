import { NavLink, Outlet, useOutletContext } from 'react-router-dom';

const PESTANAS = [
  { to: 'dashboard', etiqueta: 'Dashboard' },
  { to: 'panel-ejecutivo', etiqueta: 'Panel ejecutivo' },
  { to: 'riesgos', etiqueta: 'Riesgos' },
  { to: 'alertas', etiqueta: 'Alertas' },
  { to: 'centro-datos', etiqueta: 'Centro de datos' },
  { to: 'clases', etiqueta: 'Clases de activo' },
  { to: 'bitacora', etiqueta: 'Bitácora' },
];

export default function ModuloInventario() {
  // Mismo motivo que ModuloRBAC.jsx: el contexto de Shell (puedeEditar,
  // puedeEliminar) no pasa automáticamente a las rutas anidadas — hay que
  // leerlo aquí y reenviarlo al propio <Outlet>.
  const contexto = useOutletContext();
  return (
    <div>
      <div className="tabs">
        {PESTANAS.map((p) => (
          <NavLink key={p.to} to={p.to} className={({ isActive }) => `tab${isActive ? ' activa' : ''}`}>
            {p.etiqueta}
          </NavLink>
        ))}
      </div>
      <Outlet context={contexto} />
    </div>
  );
}

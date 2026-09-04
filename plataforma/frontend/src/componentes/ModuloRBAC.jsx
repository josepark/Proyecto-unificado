import { NavLink, Outlet, useOutletContext } from 'react-router-dom';

const PESTANAS = [
  { to: 'inicio', etiqueta: 'Inicio' },
  { to: 'roles', etiqueta: 'Roles' },
  { to: 'usuarios', etiqueta: 'Usuarios' },
  { to: 'matriz', etiqueta: 'Matriz' },
  { to: 'sistemas', etiqueta: 'Sistemas' },
  { to: 'excepciones', etiqueta: 'Excepciones' },
  { to: 'auditoria', etiqueta: 'Auditoría' },
];

export default function ModuloRBAC() {
  // El contexto de Shell (puedeEditar, autenticado) no pasa automáticamente
  // a las rutas anidadas de este módulo — hay que leerlo y reenviarlo al
  // propio <Outlet>, o useOutletContext() en Roles/Usuarios/Matriz vería
  // undefined en vez del valor real.
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

import { NavLink, Outlet, useOutletContext } from 'react-router-dom';

const PESTANAS = [
  { to: 'inicio', etiqueta: 'Inicio', badge: 'pendientes' },
  { to: 'roles', etiqueta: 'Roles', badge: 'cert_vencida' },
  { to: 'usuarios', etiqueta: 'Usuarios', badge: 'mfa' },
  { to: 'matriz', etiqueta: 'Matriz' },
  { to: 'sistemas', etiqueta: 'Sistemas' },
  { to: 'excepciones', etiqueta: 'Excepciones', badge: 'excepciones_vencidas' },
  { to: 'auditoria', etiqueta: 'Auditoría' },
];

export default function ModuloRBAC() {
  const contexto = useOutletContext() ?? {};
  const desglose = contexto.rbacResumen?.desglose;
  const rbacOk = contexto.rbacResumen?.disponible !== false;

  function valorBadge(tipo) {
    if (!desglose || !tipo) return 0;
    if (tipo === 'pendientes') return contexto.rbacResumen?.pendientes ?? 0;
    return desglose[tipo] ?? 0;
  }

  return (
    <div>
      {!rbacOk && (
        <div
          className="card"
          style={{ marginBottom: 12, borderColor: 'var(--alto)' }}
        >
          <div className="cuerpo" style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
            Matriz RBAC no responde en este momento. Los datos mostrados pueden estar desactualizados.
          </div>
        </div>
      )}
      <div className="tabs">
        {PESTANAS.map((p) => {
          const n = valorBadge(p.badge);
          return (
            <NavLink key={p.to} to={p.to} className={({ isActive }) => `tab${isActive ? ' activa' : ''}`}>
              {p.etiqueta}
              {n > 0 ? (
                <span
                  className="badge-modulo"
                  style={{ marginLeft: 6, verticalAlign: 'middle', background: p.badge === 'mfa' ? 'var(--crit)' : 'var(--alto)' }}
                >
                  {n}
                </span>
              ) : null}
            </NavLink>
          );
        })}
      </div>
      <Outlet context={contexto} />
    </div>
  );
}

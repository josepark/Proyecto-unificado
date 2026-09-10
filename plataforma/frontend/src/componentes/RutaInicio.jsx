import { Navigate } from 'react-router-dom';
import { useSesion } from '../hooks/useSesion';
import { rutaInicioModulos } from '../lib/modulosPlataforma';
import { prepararCierreSesion } from '../lib/sesionLocal';

/** Redirección inicial según proyectos permitidos del usuario. */
export default function RutaInicio() {
  const { modulos, cargando, autenticado } = useSesion();
  if (cargando) return null;

  if (!autenticado) {
    return <Navigate to="/login" replace />;
  }

  if (autenticado && !modulos?.length) {
    return (
      <div className="card">
        <div className="cuerpo">
          <h2 style={{ marginTop: 0, color: 'var(--verde-profundo)' }}>Sin proyectos asignados</h2>
          <p>
            Su cuenta está activa pero aún no tiene proyectos de la plataforma. Solicite al{' '}
            <b>Administrador</b> que le asigne Inventario, Matriz RBAC o Gestión de Riesgos en{' '}
            <b>Cuentas de acceso</b>.
          </p>
          <a
            href="/logout/"
            className="btn btn-sec"
            style={{ textDecoration: 'none' }}
            onClick={() => prepararCierreSesion()}
          >
            Cerrar sesión
          </a>
        </div>
      </div>
    );
  }

  return <Navigate to={rutaInicioModulos(modulos, { autenticado })} replace />;
}

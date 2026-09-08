import { Link, useOutletContext } from 'react-router-dom';
import ModuloRBAC from './ModuloRBAC';

/** Puerta RBAC: solo Dinamizador/Administrador (mismo criterio que nginx). */
export default function PuertaRBAC() {
  const { puedeEditar, autenticado } = useOutletContext();

  if (!puedeEditar) {
    return (
      <div className="modulo-restringido">
        <p>
          La <b>Matriz de Control de Acceso (SUIIN-SGSI-MCA-001)</b> requiere una sesión con rol{' '}
          <b>Dinamizador</b> o <b>Administrador</b>.
        </p>
        {!autenticado ? (
          <Link
            className="btn btn-primary"
            to={`/login?next=${encodeURIComponent('/rbac/inicio')}`}
          >
            Iniciar sesión
          </Link>
        ) : (
          <p className="sub">
            Su sesión no tiene permisos para RBAC.{' '}
            <a href="/logout/">Cierre sesión</a> e ingrese con una cuenta Dinamizador o Administrador.
          </p>
        )}
      </div>
    );
  }

  return <ModuloRBAC />;
}

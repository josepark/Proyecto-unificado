import { useOutletContext } from 'react-router-dom';
import ModuloRBAC from './ModuloRBAC';

/** Misma puerta que nginx y dashboard.html: Matriz RBAC solo para
 * Dinamizador/Administrador. Consultor puede ver Inventario y PTR. */
export default function PuertaRBAC() {
  const { puedeEditar, autenticado } = useOutletContext();

  if (!puedeEditar) {
    return (
      <div className="modulo-restringido">
        <p>
          La <b>Matriz de Control de Acceso (SUIIN-SGSI-MCA-001)</b> requiere una sesión con rol{' '}
          <b>Dinamizador</b> o <b>Administrador</b>.
        </p>
        {!autenticado && (
          <a className="btn btn-primary" href="/login/?next=/rbac/inicio">
            Iniciar sesión
          </a>
        )}
      </div>
    );
  }

  return <ModuloRBAC />;
}

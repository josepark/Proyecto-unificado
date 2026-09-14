import { Link, useOutletContext } from 'react-router-dom';
import ModuloRBAC from './ModuloRBAC';
import { puedeVerRbac } from '../paginas/rbac/rbacUtil';
import { tieneModulo } from '../lib/modulosPlataforma';
import { prepararCierreSesion } from '../lib/sesionLocal';

/** Puerta RBAC: edición Dinamizador/Administrador; consulta Consultor. */
export default function PuertaRBAC() {
  const ctx = useOutletContext() ?? {};
  const { puedeEditar, autenticado, roles, soloLecturaRbac, modulos } = ctx;
  const verRbac = puedeVerRbac(ctx) && tieneModulo(modulos, 'rbac', { autenticado });

  if (!verRbac) {
    return (
      <div className="modulo-restringido">
        <p>
          {!tieneModulo(modulos, 'rbac', { autenticado }) && autenticado ? (
            <>
              Su cuenta no tiene acceso al proyecto <b>Matriz RBAC</b>. Contacte al administrador del SGSI
              si necesita permiso.
            </>
          ) : (
            <>
              La <b>Matriz de Control de Acceso (SUIIN-SGSI-MCA-001)</b> requiere una sesión con rol{' '}
              <b>Dinamizador</b>, <b>Administrador</b> o <b>Consultor</b> (solo lectura).
            </>
          )}
        </p>
        {!autenticado ? (
          <Link className="btn btn-primary" to={`/login?next=${encodeURIComponent('/rbac/inicio')}`}>
            Iniciar sesión
          </Link>
        ) : (
          <p className="sub">
            Su sesión no tiene permisos para RBAC.{' '}
            <a href="/logout/" onClick={() => prepararCierreSesion()}>Cerrar sesión</a> e ingrese con una cuenta autorizada.
          </p>
        )}
      </div>
    );
  }

  if (soloLecturaRbac && !puedeEditar) {
    return (
      <>
        <div className="aviso-sesion" style={{ marginBottom: 12 }}>
          Modo consulta RBAC — puede navegar y exportar, pero no modificar roles, usuarios ni la matriz.
        </div>
        <ModuloRBAC />
      </>
    );
  }

  return <ModuloRBAC />;
}

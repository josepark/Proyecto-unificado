import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import ModuloRBAC from './ModuloRBAC';

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** GET /api/auth-rbac/ con reintento — evita falsos 401 por carreras SQLite/nginx. */
async function verificarAuthRbac() {
  for (let i = 0; i < 2; i += 1) {
    try {
      const r = await fetch('/api/auth-rbac/', { credentials: 'same-origin' });
      if (r.status === 204) return true;
    } catch {
      // sigue al reintento
    }
    if (i < 1) await esperar(250);
  }
  return false;
}

/** Puerta RBAC: solo Dinamizador/Administrador (mismo criterio que nginx). */
export default function PuertaRBAC() {
  const { puedeEditar, autenticado } = useOutletContext();
  const [autorizadoRbac, setAutorizadoRbac] = useState(null);

  useEffect(() => {
    if (!puedeEditar) {
      setAutorizadoRbac(false);
      return;
    }
    let vivo = true;
    setAutorizadoRbac(null);
    verificarAuthRbac()
      .then((ok) => vivo && setAutorizadoRbac(ok))
      .catch(() => vivo && setAutorizadoRbac(false));
    return () => {
      vivo = false;
    };
  }, [puedeEditar, autenticado]);

  if (!puedeEditar) {
    return (
      <div className="modulo-restringido">
        <p>
          La <b>Matriz de Control de Acceso (SUIIN-SGSI-MCA-001)</b> requiere una sesión con rol{' '}
          <b>Dinamizador</b> o <b>Administrador</b>.
        </p>
        {!autenticado && (
          <Link className="btn btn-primary" to="/login?next=/rbac/inicio">
            Iniciar sesión
          </Link>
        )}
      </div>
    );
  }

  if (autorizadoRbac === null) {
    return (
      <div className="modulo-restringido">
        <p>Verificando acceso a la Matriz RBAC…</p>
      </div>
    );
  }

  if (!autorizadoRbac) {
    return (
      <div className="modulo-restringido">
        <p>
          No se pudo autorizar el acceso a RBAC con su sesión actual. Esto suele resolverse
          cerrando sesión e ingresando de nuevo (use siempre la misma URL: <b>localhost</b> o{' '}
          <b>127.0.0.1</b>, no ambas).
        </p>
        <p>
          Si acaba de actualizar la plataforma, reconstruya también el contenedor{' '}
          <code>inventario</code>:{' '}
          <code>docker compose build inventario nginx --no-cache &amp;&amp; docker compose up -d</code>
        </p>
        <Link className="btn btn-primary" to="/login?next=/rbac/inicio">
          Iniciar sesión de nuevo
        </Link>
        {' · '}
        <a href="/logout/">Cerrar sesión</a>
      </div>
    );
  }

  return <ModuloRBAC />;
}

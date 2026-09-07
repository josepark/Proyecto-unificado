import { useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom';
import { useSesion } from '../hooks/useSesion';
import { eventosApi } from '../api/client';
import { rbacApi } from '../api/rbac';

function moduloDeRuta(pathname) {
  if (pathname.startsWith('/rbac')) return 'rbac';
  if (pathname.startsWith('/gestion-riesgos')) return 'riesgos';
  if (pathname.startsWith('/inventario')) return 'inventario';
  return 'otro';
}

/** Encabezado + pestañas de módulo — interfaz unificada en React Router. */
export default function Shell() {
  const { autenticado, usuario, puedeEditar, puedeEliminar, cargando, recargar } = useSesion();
  const [sesionVencida, setSesionVencida] = useState(false);
  const [pendientesRbac, setPendientesRbac] = useState(0);
  const ubicacion = useLocation();
  const rutaTrasLogin = `${ubicacion.pathname}${ubicacion.search}`;
  const moduloActivo = useMemo(() => moduloDeRuta(ubicacion.pathname), [ubicacion.pathname]);

  useEffect(() => {
    function alVencer() {
      setSesionVencida(true);
    }
    eventosApi.addEventListener('sesion-vencida', alVencer);
    return () => eventosApi.removeEventListener('sesion-vencida', alVencer);
  }, []);

  // Re-sincroniza roles al cambiar de pestaña de módulo (Inventario / RBAC /
  // Riesgos) — evita encabezado obsoleto mientras las APIs ya devuelven 401.
  useEffect(() => {
    recargar();
    setSesionVencida(false);
  }, [moduloActivo, recargar]);

  useEffect(() => {
    if (!puedeEditar) {
      setPendientesRbac(0);
      return;
    }
    let vivo = true;
    rbacApi
      .resumen()
      .then((r) => vivo && setPendientesRbac(r.pendientes_total || 0))
      .catch(() => vivo && setPendientesRbac(0));
    return () => {
      vivo = false;
    };
  }, [puedeEditar, ubicacion.pathname]);

  return (
    <>
      <header className="cabecera">
        <div className="anillo">
          <span>SU</span>
        </div>
        <div>
          <h1>Soluciones SUIIN</h1>
          <div className="sub">Camino del SUIIN · ISO/IEC 27001:2022 — CRIC</div>
        </div>
        <div className="auth">
          {cargando ? null : autenticado ? (
            <>
              Sesión: <b>{usuario}</b> · <a href="/logout/">Salir</a>
            </>
          ) : (
            <Link to={`/login?next=${encodeURIComponent(rutaTrasLogin)}`}>Iniciar sesión</Link>
          )}
        </div>
      </header>

      {sesionVencida && (
        <div className="aviso-sesion">
          Tu sesión venció.{' '}
          <Link to={`/login?next=${encodeURIComponent(rutaTrasLogin)}`}>Iniciar sesión de nuevo</Link>
          <button className="cerrar" onClick={() => setSesionVencida(false)} aria-label="Cerrar aviso">
            ×
          </button>
        </div>
      )}

      <div className="contenedor">
        <nav className="pestanas-modulo">
          <NavLink to="/inventario" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
            Inventario
          </NavLink>
          <NavLink to="/rbac" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
            Matriz RBAC
            {pendientesRbac > 0 ? <span className="badge-modulo">{pendientesRbac}</span> : null}
          </NavLink>
          <NavLink to="/gestion-riesgos" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
            Gestión de Riesgos y PTR
          </NavLink>
        </nav>

        {/* Matriz RBAC exige rol Dinamizador/Administrador — mismo
           criterio que ya usa la puerta de autorización de nginx (README
           sección 6.3). El servidor sigue siendo quien realmente lo
           impide; esto solo evita que alguien sin el rol vea un módulo
           que de todas formas le va a rechazar cada llamada. */}
        <Outlet context={{ autenticado, puedeEditar, puedeEliminar, cargando }} />
      </div>
    </>
  );
}

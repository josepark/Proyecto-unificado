import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useSesion } from '../hooks/useSesion';
import { eventosApi } from '../api/client';
import { rbacApi } from '../api/rbac';

/** Encabezado + pestañas de módulo, persistentes en toda la app — la
 * misma "una sola interfaz" que ya lograba dashboard.html embebiendo
 * RBAC en un iframe (README sección 6.1), ahora como enrutamiento de
 * React de verdad: Inventario y Matriz RBAC son rutas hermanas del
 * mismo árbol de componentes, no dos aplicaciones cosidas. */
export default function Shell() {
  const { autenticado, usuario, puedeEditar, puedeEliminar, cargando } = useSesion();
  const [sesionVencida, setSesionVencida] = useState(false);
  const [pendientesRbac, setPendientesRbac] = useState(0);
  const ubicacion = useLocation();
  const rutaTrasLogin = `/app${ubicacion.pathname}${ubicacion.search}`;

  useEffect(() => {
    function alVencer() {
      setSesionVencida(true);
    }
    eventosApi.addEventListener('sesion-vencida', alVencer);
    return () => eventosApi.removeEventListener('sesion-vencida', alVencer);
  }, []);

  // Si la persona ya volvió a iniciar sesión y navega a otra pantalla,
  // el aviso no debe seguir pegado — se limpia solo al cambiar de ruta.
  useEffect(() => {
    setSesionVencida(false);
  }, [ubicacion.pathname]);

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
            <a href="/login/">Iniciar sesión</a>
          )}
        </div>
      </header>

      {sesionVencida && (
        <div className="aviso-sesion">
          Tu sesión venció o no tenés permisos para esta sección.{' '}
          <a href={`/login/?next=${encodeURIComponent(rutaTrasLogin)}`}>Iniciar sesión de nuevo</a>
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
        <Outlet context={{ autenticado, puedeEditar, puedeEliminar }} />
      </div>
    </>
  );
}

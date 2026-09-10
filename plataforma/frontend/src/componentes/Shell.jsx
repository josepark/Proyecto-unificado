import { useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom';
import { useSesion } from '../hooks/useSesion';
import { useApi } from '../hooks/useApi';
import { consultarSesionInventario, eventosApi } from '../api/client';
import { inventarioApi } from '../api/inventario';
import { rbacApi } from '../api/rbac';
import { pendientesSync } from '../lib/integracionUi';
import { tieneModulo } from '../lib/modulosPlataforma';
import { puedeVerRbac, ENLACES_ALERTAS_RBAC } from '../paginas/rbac/rbacUtil';
import { prepararCierreSesion } from '../lib/sesionLocal';

function moduloDeRuta(pathname) {
  if (pathname.startsWith('/rbac')) return 'rbac';
  if (pathname.startsWith('/gestion-riesgos')) return 'riesgos';
  if (pathname.startsWith('/inventario')) return 'inventario';
  return 'otro';
}

/** Encabezado + pestañas de módulo — interfaz unificada en React Router. */
export default function Shell() {
  const sesion = useSesion();
  const { autenticado, usuario, puedeEditar, puedeEliminar, cargando, roles, modulos } = sesion;
  const [sesionVencida, setSesionVencida] = useState(false);
  const [pendientesRbac, setPendientesRbac] = useState(0);
  const [desgloseRbac, setDesgloseRbac] = useState(null);
  const [rbacDisponible, setRbacDisponible] = useState(true);
  const [mostrarDesglose, setMostrarDesglose] = useState(false);
  const ubicacion = useLocation();
  const rutaTrasLogin = `${ubicacion.pathname}${ubicacion.search}`;
  const moduloActivo = useMemo(() => moduloDeRuta(ubicacion.pathname), [ubicacion.pathname]);
  const soloLecturaRbac = autenticado && !puedeEditar && (roles ?? []).includes('Consultor');
  const verRbac = puedeVerRbac({ autenticado, puedeEditar, roles })
    && tieneModulo(modulos, 'rbac', { autenticado });
  const verInventario = !autenticado || tieneModulo(modulos, 'inventario', { autenticado });
  const verRiesgos = !autenticado || tieneModulo(modulos, 'riesgos', { autenticado });
  const verAlertasInventario = autenticado && tieneModulo(modulos, 'inventario', { autenticado });

  useEffect(() => {
    function alVencer() {
      setSesionVencida(true);
    }
    eventosApi.addEventListener('sesion-vencida', alVencer);
    return () => eventosApi.removeEventListener('sesion-vencida', alVencer);
  }, []);

  useEffect(() => {
    setSesionVencida(false);
  }, [moduloActivo]);

  useEffect(() => {
    if (!verRbac || cargando) {
      setPendientesRbac(0);
      setDesgloseRbac(null);
      setRbacDisponible(true);
      return;
    }
    let vivo = true;
    consultarSesionInventario()
      .then((s) => {
        if (!vivo || !s.autenticado) {
          setPendientesRbac(0);
          setRbacDisponible(true);
          return null;
        }
        return rbacApi.resumen();
      })
      .then((r) => {
        if (!vivo) return;
        if (!r) {
          setPendientesRbac(0);
          setDesgloseRbac(null);
          setRbacDisponible(false);
          return;
        }
        setRbacDisponible(true);
        setPendientesRbac(r.pendientes_total || 0);
        setDesgloseRbac(r.desglose_pendientes || null);
      })
      .catch(() => {
        if (vivo) {
          setPendientesRbac(0);
          setDesgloseRbac(null);
          setRbacDisponible(false);
        }
      });
    return () => {
      vivo = false;
    };
  }, [verRbac, cargando, autenticado]);

  const { datos: alertasUni, recargar: recargarAlertas } = useApi(
    () => (verAlertasInventario && !cargando ? inventarioApi.alertasUnificadas() : Promise.resolve(null)),
    [verAlertasInventario, cargando, usuario],
  );
  const totalAlertas = alertasUni?.total_consolidado ?? 0;
  const pendientesRiesgos = alertasUni?.resumen?.riesgos ?? 0;
  const vinc = alertasUni?.vinculacion;
  const pendientesSyncCount = pendientesSync(vinc);

  useEffect(() => {
    function actualizarAlertas() {
      if (verAlertasInventario && !cargando) recargarAlertas();
    }
    eventosApi.addEventListener('alertas-actualizadas', actualizarAlertas);
    return () => eventosApi.removeEventListener('alertas-actualizadas', actualizarAlertas);
  }, [verAlertasInventario, cargando, recargarAlertas]);

  const outletContext = {
    autenticado,
    usuario,
    puedeEditar,
    puedeEliminar,
    cargando,
    roles,
    modulos,
    soloLecturaRbac,
    alertasUnificadas: alertasUni,
    recargarAlertasUnificadas: recargarAlertas,
    rbacResumen: rbacDisponible ? { pendientes: pendientesRbac, desglose: desgloseRbac, disponible: true } : { disponible: false },
  };

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
          {cargando && !autenticado ? null : autenticado ? (
            <>
              {verAlertasInventario && totalAlertas > 0 ? (
                <Link
                  to="/inventario/alertas"
                  style={{ fontSize: 12, marginRight: 8, textDecoration: 'none' }}
                  title="Centro de alertas unificado"
                >
                  🔔 {totalAlertas}
                </Link>
              ) : null}
              Sesión: <b>{usuario}</b>
              {soloLecturaRbac ? ' · consulta RBAC' : null}
              {cargando ? ' · …' : null}
              {' · '}
              <a
                href="/logout/"
                className="btn btn-sec"
                style={{ padding: '2px 10px', fontSize: 12, marginLeft: 4 }}
                onClick={() => prepararCierreSesion()}
              >
                Cerrar sesión
              </a>
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
          {verInventario ? (
          <NavLink to="/inventario" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
            Inventario
              {totalAlertas > 0 ? (
                <span className="badge-modulo" style={{ marginLeft: 6 }} title="Señales operativas (Inventario + RBAC + Riesgos + sync)">
                  {totalAlertas}
                </span>
              ) : null}
              {pendientesSyncCount > 0 ? (
                <span
                  className="badge-modulo"
                  style={{ marginLeft: 4, background: 'var(--alto)' }}
                  title="Activos pendientes de sincronizar Inventario ↔ Riesgos (también incluidos en el total)"
                >
                  ↻{pendientesSyncCount}
                </span>
              ) : null}
          </NavLink>
          ) : null}
          {verRbac ? (
          <span style={{ position: 'relative', display: 'inline-block' }}>
            <NavLink to="/rbac" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
              Matriz RBAC
              {!rbacDisponible ? (
                <span
                  className="badge-modulo"
                  style={{ marginLeft: 6, background: 'var(--texto-suave)' }}
                  title="Matriz RBAC no responde en este momento"
                >
                  !
                </span>
              ) : pendientesRbac > 0 ? (
                <button
                  type="button"
                  className="badge-modulo"
                  style={{ cursor: 'pointer', border: 'none', padding: '0 6px' }}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setMostrarDesglose((v) => !v);
                  }}
                  title="Ver desglose de pendientes"
                >
                  {pendientesRbac}
                </button>
              ) : null}
            </NavLink>
            {mostrarDesglose && desgloseRbac && (
              <div
                className="card"
                style={{
                  position: 'absolute', top: '100%', left: 0, zIndex: 30, minWidth: 280,
                  marginTop: 4, boxShadow: '0 4px 16px rgba(0,0,0,.15)',
                }}
              >
                <div className="cuerpo" style={{ fontSize: 13 }}>
                  <strong>Pendientes RBAC</strong>
                  <ul style={{ margin: '8px 0 0', paddingLeft: 18, listStyle: 'none' }}>
                    <li>
                      <Link to={ENLACES_ALERTAS_RBAC.proximos_vencimientos} onClick={() => setMostrarDesglose(false)}>
                        Vencimientos próximos (7 d): <b>{desgloseRbac.proximos_vencimientos}</b>
                      </Link>
                    </li>
                    <li>
                      <Link to={ENLACES_ALERTAS_RBAC.alertas_mfa} onClick={() => setMostrarDesglose(false)}>
                        MFA incumplido: <b>{desgloseRbac.alertas_mfa}</b>
                      </Link>
                    </li>
                    <li>
                      <Link to={ENLACES_ALERTAS_RBAC.roles_certificacion_vencida} onClick={() => setMostrarDesglose(false)}>
                        Certificación de rol vencida: <b>{desgloseRbac.roles_certificacion_vencida}</b>
                      </Link>
                    </li>
                    <li>
                      <Link to={ENLACES_ALERTAS_RBAC.excepciones_vencidas} onClick={() => setMostrarDesglose(false)}>
                        Excepciones vencidas: <b>{desgloseRbac.excepciones_vencidas}</b>
                      </Link>
                    </li>
                  </ul>
                  <Link to="/rbac/inicio" onClick={() => setMostrarDesglose(false)} style={{ fontSize: 12 }}>
                    Ir al tablero RBAC →
                  </Link>
                  {' · '}
                  <Link to="/inventario/alertas" onClick={() => setMostrarDesglose(false)} style={{ fontSize: 12 }}>
                    Centro de alertas unificado →
                  </Link>
                </div>
              </div>
            )}
          </span>
          ) : null}
          {verRiesgos ? (
          <NavLink to="/gestion-riesgos" className={({ isActive }) => `modulo${isActive ? ' activo' : ''}`}>
            Gestión de Riesgos y PTR
            {pendientesRiesgos > 0 ? (
              <span className="badge-modulo" style={{ marginLeft: 6 }} title="Pendientes operativos en Riesgos (PTR, vulns, cobertura)">
                {pendientesRiesgos}
              </span>
            ) : null}
          </NavLink>
          ) : null}
        </nav>

        <Outlet context={outletContext} />
      </div>
    </>
  );
}

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { eventosApi, consultarSesionInventario, leerSesionConfirmada } from '../api/client';
import { sincronizarUsuarioActivo } from '../lib/sesionLocal';

const VACIA = {
  autenticado: false,
  usuario: null,
  roles: [],
  puedeEditar: false,
  puedeEliminar: false,
  modulos: [],
};

const SesionContext = createContext(null);

function mapearSesion(s) {
  return {
    autenticado: s.autenticado,
    usuario: s.usuario,
    roles: s.roles || [],
    puedeEditar: s.puede_editar,
    puedeEliminar: s.puede_eliminar,
    modulos: s.modulos || [],
  };
}

/** Sesión actual (rol, permisos) — misma fuente que el tablero anterior
 * (GET /api/sesion/). Expone recargar() para refrescar tras el login React. */
export function SesionProvider({ children }) {
  const [sesion, setSesion] = useState(VACIA);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(({ silencioso = false } = {}) => {
    if (!silencioso) setCargando(true);
    return leerSesionConfirmada()
      .then((s) => {
        if (s.autenticado) {
          sincronizarUsuarioActivo(s.usuario);
        }
        setSesion(mapearSesion(s));
      })
      .catch(() => {})
      .finally(() => {
        if (!silencioso) setCargando(false);
      });
  }, []);

  useEffect(() => {
    recargar();
  }, [recargar]);

  useEffect(() => {
    async function sincronizar(evento) {
      const s = evento.detail;
      if (!s || typeof s.autenticado !== 'boolean') return;
      if (!s.autenticado) {
        const confirm = await consultarSesionInventario();
        if (!confirm.autenticado) {
          const reconfirm = await leerSesionConfirmada();
          sincronizarUsuarioActivo(reconfirm.autenticado ? reconfirm.usuario : null);
          setSesion(mapearSesion(reconfirm));
        } else {
          sincronizarUsuarioActivo(confirm.usuario);
          setSesion(mapearSesion(confirm));
        }
      } else {
        sincronizarUsuarioActivo(s.usuario);
        setSesion(mapearSesion(s));
      }
      setCargando(false);
    }
    eventosApi.addEventListener('sesion-actualizada', sincronizar);
    return () => eventosApi.removeEventListener('sesion-actualizada', sincronizar);
  }, []);

  useEffect(() => {
    function alRecuperarFoco() {
      if (document.visibilityState === 'visible') recargar({ silencioso: true });
    }
    document.addEventListener('visibilitychange', alRecuperarFoco);
    return () => document.removeEventListener('visibilitychange', alRecuperarFoco);
  }, [recargar]);

  return (
    <SesionContext.Provider value={{ ...sesion, cargando, recargar }}>{children}</SesionContext.Provider>
  );
}

export function useSesion() {
  const ctx = useContext(SesionContext);
  if (!ctx) throw new Error('useSesion debe usarse dentro de SesionProvider');
  return ctx;
}

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { inventarioApi } from '../api/inventario';
import { eventosApi } from '../api/client';

const VACIA = {
  autenticado: false,
  usuario: null,
  roles: [],
  puedeEditar: false,
  puedeEliminar: false,
};

const SesionContext = createContext(null);

function mapearSesion(s) {
  return {
    autenticado: s.autenticado,
    usuario: s.usuario,
    roles: s.roles || [],
    puedeEditar: s.puede_editar,
    puedeEliminar: s.puede_eliminar,
  };
}

/** Sesión actual (rol, permisos) — misma fuente que el tablero anterior
 * (GET /api/sesion/). Expone recargar() para refrescar tras el login React. */
export function SesionProvider({ children }) {
  const [sesion, setSesion] = useState(VACIA);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(() => {
    setCargando(true);
    return inventarioApi
      .sesion()
      .then((s) => setSesion(mapearSesion(s)))
      .catch(() => setSesion(VACIA))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    recargar();
  }, [recargar]);

  useEffect(() => {
    function sincronizar(evento) {
      const s = evento.detail;
      if (!s || typeof s.autenticado !== 'boolean') return;
      setSesion(mapearSesion(s));
      setCargando(false);
    }
    eventosApi.addEventListener('sesion-actualizada', sincronizar);
    return () => eventosApi.removeEventListener('sesion-actualizada', sincronizar);
  }, []);

  useEffect(() => {
    function alRecuperarFoco() {
      if (document.visibilityState === 'visible') recargar();
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

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { inventarioApi } from '../api/inventario';

const VACIA = {
  autenticado: false,
  usuario: null,
  roles: [],
  puedeEditar: false,
  puedeEliminar: false,
};

const SesionContext = createContext(null);

/** Sesión actual (rol, permisos) — misma fuente que el tablero anterior
 * (GET /api/sesion/). Expone recargar() para refrescar tras el login React. */
export function SesionProvider({ children }) {
  const [sesion, setSesion] = useState(VACIA);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(() => {
    setCargando(true);
    return inventarioApi
      .sesion()
      .then((s) =>
        setSesion({
          autenticado: s.autenticado,
          usuario: s.usuario,
          roles: s.roles,
          puedeEditar: s.puede_editar,
          puedeEliminar: s.puede_eliminar,
        }),
      )
      .catch(() => setSesion(VACIA))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    recargar();
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

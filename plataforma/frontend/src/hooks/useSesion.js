import { useEffect, useState } from 'react';
import { inventarioApi } from '../api/inventario';

const VACIA = { autenticado: false, usuario: null, roles: [], puedeEditar: false, puedeEliminar: false };

/** Sesión actual (rol, permisos) — misma fuente que ya usaba el tablero
 * anterior (GET /api/sesion/). `puedeEditar` es también el criterio que
 * decide si el módulo Matriz RBAC se muestra o no (mismo rol que exige
 * la puerta de autorización de nginx — ver README sección 6.3). */
export function useSesion() {
  const [sesion, setSesion] = useState(VACIA);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    inventarioApi
      .sesion()
      .then((s) => {
        if (!vivo) return;
        setSesion({
          autenticado: s.autenticado,
          usuario: s.usuario,
          roles: s.roles,
          puedeEditar: s.puede_editar,
          puedeEliminar: s.puede_eliminar,
        });
      })
      .catch(() => vivo && setSesion(VACIA))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, []);

  return { ...sesion, cargando };
}

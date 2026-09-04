import { useEffect, useState, useCallback } from 'react';

/** Carga `fn()` al montar (y cada vez que cambien `deps`), con estados de
 * carga/error consistentes en toda la app. `recargar()` permite refrescar
 * después de una escritura sin duplicar la lógica de fetch en cada página. */
export function useApi(fn, deps = []) {
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const recargar = useCallback(() => {
    let vivo = true;
    setCargando(true);
    setError(null);
    fn()
      .then((d) => vivo && setDatos(d))
      .catch((e) => vivo && setError(e))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => recargar(), [recargar]);

  return { datos, cargando, error, recargar };
}

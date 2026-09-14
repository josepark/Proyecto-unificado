import { createContext, useContext } from 'react';

const PlataformaContext = createContext({
  anidado: false,
  prefijo: '/gestion-riesgos',
});

export function PlataformaProvider({ anidado = false, prefijo = '/gestion-riesgos', children }) {
  return (
    <PlataformaContext.Provider value={{ anidado, prefijo }}>
      {children}
    </PlataformaContext.Provider>
  );
}

export function usePlataforma() {
  return useContext(PlataformaContext);
}

/** Construye rutas absolutas dentro del módulo (standalone o SPA unificada). */
export function rutaRiesgos(anidado, prefijo, subpath = "") {
  const limpio = String(subpath).replace(/^\//, "");
  if (!anidado) return limpio ? `/${limpio}` : "/";
  return limpio ? `${prefijo}/${limpio}` : prefijo;
}

export function useRiesgosTo(subpath = '') {
  const { anidado, prefijo } = usePlataforma();
  return rutaRiesgos(anidado, prefijo, subpath);
}

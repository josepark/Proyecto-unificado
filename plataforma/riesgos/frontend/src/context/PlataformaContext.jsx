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

/** Enlace interno del módulo: relativo cuando está anidado en la SPA unificada. */
export function useRiesgosTo(subpath = '') {
  const { anidado, prefijo } = usePlataforma();
  const limpio = String(subpath).replace(/^\//, '');
  if (!anidado) return limpio ? `/${limpio}` : '/';
  return limpio ? `${prefijo}/${limpio}` : prefijo;
}

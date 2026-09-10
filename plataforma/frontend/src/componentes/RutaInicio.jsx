import { Navigate } from 'react-router-dom';
import { useSesion } from '../hooks/useSesion';
import { rutaInicioModulos } from '../lib/modulosPlataforma';

/** Redirección inicial según proyectos permitidos del usuario. */
export default function RutaInicio() {
  const { modulos, cargando } = useSesion();
  if (cargando) return null;
  return <Navigate to={rutaInicioModulos(modulos)} replace />;
}

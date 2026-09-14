import { Link } from 'react-router-dom';

/** Banner cuando un Consultor abre una ficha en solo lectura. */
export function AvisoConsultaRbac({ visible }) {
  if (!visible) return null;
  return (
    <div className="aviso-sesion" style={{ marginBottom: 12 }}>
      Modo consulta — ficha de solo lectura. Puede revisar datos y exportar, pero no modificar registros.
    </div>
  );
}

/** Bloquea rutas /nuevo para Consultor (solo lectura). */
export function BloqueoCreacionRbac({ entidad, rutaListado }) {
  return (
    <div className="card">
      <div className="cuerpo">
        Modo consulta: no puede crear {entidad} nuevos.{' '}
        <Link to={rutaListado}>Volver al listado</Link>
      </div>
    </div>
  );
}

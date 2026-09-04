import { useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';

const ESTADO_COLOR = { ok: 't-BAJO', error: 't-CRIT' };

export default function ImportarActivos() {
  const { puedeEditar } = useOutletContext() ?? {};
  const navegar = useNavigate();
  const [archivo, setArchivo] = useState(null);
  const [analizando, setAnalizando] = useState(false);
  const [analisis, setAnalisis] = useState(null);
  const [confirmando, setConfirmando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para importar activos con tu rol actual. <Link to="/inventario/dashboard">Volver</Link>
        </div>
      </div>
    );
  }

  async function analizar(ev) {
    ev.preventDefault();
    if (!archivo) return;
    setAnalizando(true);
    setError(null);
    setAnalisis(null);
    setResultado(null);
    try {
      const fd = new FormData();
      fd.append('archivo', archivo);
      const r = await inventarioApi.importarAnalizar(fd);
      setAnalisis(r);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setAnalizando(false);
    }
  }

  async function confirmar() {
    const filasOk = analisis.filas.filter((f) => f.estado === 'ok');
    if (!filasOk.length) return;
    if (!window.confirm(`¿Crear ${filasOk.length} activo(s) nuevo(s)? Quedará registrado en la bitácora.`)) return;
    setConfirmando(true);
    setError(null);
    try {
      const r = await inventarioApi.importarConfirmar(filasOk);
      setResultado(r);
      setAnalisis(null);
      setArchivo(null);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setConfirmando(false);
    }
  }

  return (
    <div>
      <Link to="/inventario/dashboard" className="volver">
        ← Volver al Dashboard
      </Link>
      <h2 style={{ margin: '4px 0 8px', color: 'var(--verde-profundo)' }}>Importar activos desde Excel</h2>
      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Útil para registrar un lote de equipos nuevos de una sola vez — por ejemplo, tras una compra. Primero se
        analiza el archivo sin guardar nada; solo se crean los activos cuando confirma.
      </p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="cuerpo">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            <a href="/api/activos/importar/plantilla.xlsx">⬇ Descargar plantilla (.xlsx)</a> — incluye los
            encabezados correctos, una fila de ejemplo, y una hoja con los valores válidos de cada campo.
          </p>
          <form onSubmit={analizar} style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input type="file" accept=".xlsx" onChange={(e) => setArchivo(e.target.files?.[0] || null)} />
            <button className="btn btn-primary" type="submit" disabled={!archivo || analizando}>
              {analizando ? 'Analizando…' : 'Analizar archivo'}
            </button>
          </form>
        </div>
      </div>

      {error && (
        <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 16 }}>Error: {error}</p>
      )}

      {analisis && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>
            Resultado del análisis — {analisis.listas} lista{analisis.listas === 1 ? '' : 's'} para crear
            {analisis.con_error > 0 && `, ${analisis.con_error} con error`}
          </h2>
          <div className="cuerpo" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Fila</th>
                  <th>Estado</th>
                  <th>Nombre</th>
                  <th>Clase</th>
                  <th>Mensaje</th>
                </tr>
              </thead>
              <tbody>
                {analisis.filas.map((f) => (
                  <tr key={f.fila}>
                    <td>{f.fila}</td>
                    <td>
                      <span className={`tag ${ESTADO_COLOR[f.estado]}`}>{f.estado === 'ok' ? 'Lista' : 'Error'}</span>
                    </td>
                    <td>{f.datos?.nombre || '—'}</td>
                    <td>{f.datos?.clase || '—'}</td>
                    <td style={{ color: f.estado === 'error' ? 'var(--crit)' : 'inherit', fontSize: 12 }}>
                      {f.mensaje}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="cuerpo" style={{ paddingTop: 0 }}>
            <button className="btn btn-primary" onClick={confirmar} disabled={confirmando || analisis.listas === 0}>
              {confirmando ? 'Creando…' : `Confirmar y crear ${analisis.listas} activo(s)`}
            </button>
          </div>
        </div>
      )}

      {resultado && (
        <div className="card">
          <h2>Importación completada</h2>
          <div className="cuerpo">
            <p>
              <b style={{ color: 'var(--bajo)' }}>{resultado.total_creados} activo(s) creado(s)</b>
              {resultado.total_fallidos > 0 && (
                <>
                  {' '}
                  · <b style={{ color: 'var(--crit)' }}>{resultado.total_fallidos} fallaron</b>
                </>
              )}
            </p>
            {resultado.creados.length > 0 && (
              <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                {resultado.creados.map((c) => (
                  <li key={c.id}>
                    <Link to={`/inventario/activos/${c.id}`}>{c.id_activo}</Link>
                  </li>
                ))}
              </ul>
            )}
            {resultado.fallidos.length > 0 && (
              <>
                <p style={{ fontSize: 13, fontWeight: 'bold', color: 'var(--crit)' }}>Fallaron:</p>
                <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                  {resultado.fallidos.map((f, i) => (
                    <li key={i}>
                      Fila {f.fila}: {f.mensaje}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <button className="btn btn-sec" onClick={() => navegar('/inventario/dashboard')}>
              Ir al Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

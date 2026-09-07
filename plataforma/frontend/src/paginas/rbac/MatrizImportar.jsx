import { useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { rbacApi } from '../../api/rbac';
import { formatearErrorApi } from '../../api/client';

export default function MatrizImportar() {
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
          No tenés permiso para importar la matriz con tu rol actual.{' '}
          <Link to="/rbac/matriz">Volver</Link>
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
      const r = await rbacApi.importarMatrizAnalizar(fd);
      setAnalisis(r);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setAnalizando(false);
    }
  }

  async function confirmar() {
    const cambios = analisis?.cambios ?? [];
    if (!cambios.length) return;
    if (!window.confirm(`¿Aplicar ${cambios.length} cambio(s) en la matriz? Quedará registrado en la bitácora.`)) return;
    setConfirmando(true);
    setError(null);
    try {
      const r = await rbacApi.importarMatrizConfirmar(cambios);
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
      <Link to="/rbac/matriz" className="volver">
        ← Volver a la Matriz
      </Link>
      <h2 style={{ margin: '4px 0 8px', color: 'var(--verde-profundo)' }}>Importar matriz desde CSV</h2>
      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Use el mismo formato que genera «Exportar matriz (CSV)»: delimitador punto y coma, codificación UTF-8.
        Primero se analiza el archivo sin guardar nada; solo se aplican los cambios cuando confirma.
      </p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="cuerpo">
          <p style={{ fontSize: 13, marginTop: 0 }}>
            <a href="/rbac/api/export/matriz.csv">⬇ Descargar matriz actual (.csv)</a> — plantilla con los
            encabezados y valores actuales.
          </p>
          <form onSubmit={analizar} style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
            />
            <button type="submit" className="btn btn-primary" disabled={!archivo || analizando}>
              {analizando ? 'Analizando…' : 'Analizar archivo'}
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--rojo)' }}>
          <div className="cuerpo">{error}</div>
        </div>
      )}

      {resultado && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="cuerpo">
            Importación aplicada: {resultado.aplicados} cambio(s) en la matriz.{' '}
            <button type="button" className="btn btn-primary" onClick={() => navegar('/rbac/matriz')}>
              Ir a la matriz
            </button>
          </div>
        </div>
      )}

      {analisis && (
        <>
          {analisis.errores?.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h2>Advertencias ({analisis.errores.length})</h2>
              <div className="cuerpo">
                <ul style={{ fontSize: 13, margin: 0, paddingLeft: 20 }}>
                  {analisis.errores.map((msg, i) => (
                    <li key={i}>{msg}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <div className="card">
            <h2>Cambios detectados ({analisis.cambios?.length ?? 0})</h2>
            <div className="cuerpo">
              {!analisis.cambios?.length ? (
                <p style={{ fontSize: 13, margin: 0 }}>No hay diferencias respecto a la matriz actual.</p>
              ) : (
                <>
                  <table>
                    <thead>
                      <tr>
                        <th>Sistema</th>
                        <th>Rol</th>
                        <th>Actual</th>
                        <th>Nuevo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analisis.cambios.map((c, i) => (
                        <tr key={i}>
                          <td>{c.sistema}</td>
                          <td>{c.rol}</td>
                          <td>{c.actual}</td>
                          <td><strong>{c.nuevo}</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p style={{ marginTop: 14 }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={confirmando}
                      onClick={confirmar}
                    >
                      {confirmando ? 'Aplicando…' : `Confirmar ${analisis.cambios.length} cambio(s)`}
                    </button>
                  </p>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

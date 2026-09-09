import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { CampoSelect, Fila } from '../../componentes/CamposFormulario';
import BannerErrorMutacion from '../../componentes/BannerErrorMutacion';
import { mensajeErrorRbac } from './rbacUtil';

export default function MatrizComparar() {
  const { datos: roles } = useApi(() => rbacApi.listarRoles(), []);
  const [rolA, setRolA] = useState('');
  const [rolB, setRolB] = useState('');
  const [comparando, setComparando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [soloDiferencias, setSoloDiferencias] = useState(false);
  const [error, setError] = useState(null);

  async function comparar(ev) {
    ev.preventDefault();
    setComparando(true);
    setError(null);
    try {
      const r = await rbacApi.compararRoles(rolA, rolB);
      setResultado(r);
    } catch (e) {
      setError(mensajeErrorRbac('la comparación de roles', e));
      setResultado(null);
    } finally {
      setComparando(false);
    }
  }

  return (
    <div>
      <Link to="/rbac/matriz" className="volver">
        ← Volver a la Matriz
      </Link>
      <h2 style={{ margin: '4px 0 8px', color: 'var(--verde-profundo)' }}>Comparar accesos entre dos roles</h2>
      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Útil para revisiones de mínimo privilegio: vea de un vistazo en qué sistemas difiere el acceso entre dos
        roles parecidos.
      </p>

      <form onSubmit={comparar} style={{ marginBottom: 20 }}>
        <Fila columnas={3}>
          <CampoSelect
            label="Rol A"
            opciones={[['', 'Seleccione…'], ...(roles ?? []).map((r) => [String(r.id), `${r.abreviatura} — ${r.denominacion}`])]}
            value={rolA}
            required
            onChange={(e) => setRolA(e.target.value)}
          />
          <CampoSelect
            label="Rol B"
            opciones={[['', 'Seleccione…'], ...(roles ?? []).map((r) => [String(r.id), `${r.abreviatura} — ${r.denominacion}`])]}
            value={rolB}
            required
            onChange={(e) => setRolB(e.target.value)}
          />
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button className="btn btn-primary" type="submit" disabled={comparando || !rolA || !rolB}>
              {comparando ? 'Comparando…' : 'Comparar'}
            </button>
          </div>
        </Fila>
      </form>

      {error && <BannerErrorMutacion error={error} onCerrar={() => setError(null)} />}

      {resultado && (
        <div className="card">
          <h2>
            {resultado.rol_a.abreviatura} vs {resultado.rol_b.abreviatura}{' '}
            <span style={{ fontWeight: 'normal', fontSize: 13, color: 'var(--texto-suave)' }}>
              ({resultado.num_diferencias} diferencia{resultado.num_diferencias === 1 ? '' : 's'} de{' '}
              {resultado.filas.length} sistemas)
            </span>
          </h2>
          <div className="cuerpo" style={{ paddingBottom: 12 }}>
            <label style={{ fontSize: 13 }}>
              <input
                type="checkbox"
                checked={soloDiferencias}
                onChange={(e) => setSoloDiferencias(e.target.checked)}
                style={{ marginRight: 6 }}
              />
              Mostrar solo diferencias
            </label>
          </div>
          <div className="cuerpo" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Sistema</th>
                  <th>Categoría</th>
                  <th>{resultado.rol_a.abreviatura}</th>
                  <th>{resultado.rol_b.abreviatura}</th>
                </tr>
              </thead>
              <tbody>
                {resultado.filas
                  .filter((f) => !soloDiferencias || f.difiere)
                  .map((f, i) => (
                  <tr key={i} style={f.difiere ? { background: '#fdf1e4' } : undefined}>
                    <td>{f.sistema}</td>
                    <td>{f.categoria}</td>
                    <td>
                      <span className={`chip niv-${f.nivel_a === '—' ? 'X' : f.nivel_a}`}>{f.nivel_a}</span>
                    </td>
                    <td>
                      <span className={`chip niv-${f.nivel_b === '—' ? 'X' : f.nivel_b}`}>{f.nivel_b}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

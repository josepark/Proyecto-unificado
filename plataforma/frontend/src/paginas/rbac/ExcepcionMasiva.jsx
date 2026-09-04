import { useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, Fila } from '../../componentes/CamposFormulario';

export default function ExcepcionMasiva() {
  const { puedeEditar } = useOutletContext() ?? {};
  const navegar = useNavigate();

  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: sistemas } = useApi(() => rbacApi.listarSistemas(), []);
  const { datos: usuarios } = useApi(() => rbacApi.listarUsuarios(), []);

  const [sistemaId, setSistemaId] = useState('');
  const [nivel, setNivel] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [motivo, setMotivo] = useState('');
  const [seleccionados, setSeleccionados] = useState(new Set());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [resultado, setResultado] = useState(null);

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para asignar excepciones con tu rol actual. <Link to="/rbac/excepciones">Volver</Link>
        </div>
      </div>
    );
  }

  const elegibles = (usuarios ?? []).filter((u) => u.estado === 'Activo' || u.estado === 'Temporal');

  function alternar(id) {
    setSeleccionados((s) => {
      const copia = new Set(s);
      if (copia.has(id)) copia.delete(id);
      else copia.add(id);
      return copia;
    });
  }

  function alternarTodos(marcar) {
    setSeleccionados(marcar ? new Set(elegibles.map((u) => u.id)) : new Set());
  }

  async function aplicar(ev) {
    ev.preventDefault();
    if (!window.confirm('¿Aplicar esta excepción a todos los usuarios marcados?')) return;
    setGuardando(true);
    setError(null);
    setResultado(null);
    try {
      const r = await rbacApi.excepcionesMasiva({
        sistema_id: Number(sistemaId), nivel, fecha_fin: fechaFin || null, motivo,
        usuario_ids: [...seleccionados],
      });
      setResultado(r);
      setSeleccionados(new Set());
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <Link to="/rbac/excepciones" className="volver">
        ← Ver excepciones vigentes
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>Asignación masiva de excepciones</h2>
      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Aplique la misma excepción de acceso (control 5.18) a varios usuarios a la vez — por ejemplo, un grupo de
        contratistas que necesita el mismo acceso temporal a un sistema. Cada aplicación queda registrada
        individualmente en la bitácora.
      </p>

      <form onSubmit={aplicar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Sistema, nivel y motivo</h2>
          <div className="cuerpo">
            <Fila columnas={3}>
              <CampoSelect
                label="Sistema *"
                opciones={[['', 'Seleccione…'], ...(sistemas ?? []).map((s) => [String(s.id), s.nombre])]}
                value={sistemaId}
                required
                onChange={(e) => setSistemaId(e.target.value)}
              />
              <CampoSelect
                label="Nivel a asignar *"
                opciones={[
                  ['', 'Seleccione…'],
                  ...(catalogos?.niveles_acceso ?? []).map((n) => [n.codigo, `${n.codigo} — ${n.nombre}`]),
                ]}
                value={nivel}
                required
                onChange={(e) => setNivel(e.target.value)}
              />
              <Campo label="Vigencia hasta" type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
            </Fila>
            <Campo
              label="Motivo (obligatorio) *"
              placeholder="Justificación documentada — control 5.18"
              value={motivo}
              required
              onChange={(e) => setMotivo(e.target.value)}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Usuarios ({elegibles.length} activos/temporales)</h2>
          <div className="cuerpo">
            <div style={{ marginBottom: 8, display: 'flex', gap: 12, fontSize: 13 }}>
              <button type="button" className="btn-sec" onClick={() => alternarTodos(true)}>
                Marcar todos
              </button>
              <button type="button" className="btn-sec" onClick={() => alternarTodos(false)}>
                Desmarcar todos
              </button>
              <span style={{ alignSelf: 'center', color: 'var(--texto-suave)' }}>{seleccionados.size} marcado(s)</span>
            </div>
            <div style={{ maxHeight: 380, overflow: 'auto', border: '1px solid var(--borde)', borderRadius: 6 }}>
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 34 }}></th>
                    <th>Nombre</th>
                    <th>Rol</th>
                  </tr>
                </thead>
                <tbody>
                  {elegibles.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={seleccionados.has(u.id)}
                          onChange={() => alternar(u.id)}
                          id={`u${u.id}`}
                        />
                      </td>
                      <td>
                        <label htmlFor={`u${u.id}`}>{u.nombre}</label>
                      </td>
                      <td>{u.rol}</td>
                    </tr>
                  ))}
                  {!elegibles.length && (
                    <tr>
                      <td colSpan={3} className="sub">
                        No hay usuarios activos o temporales.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {resultado && (
          <p style={{ color: 'var(--acento)', fontWeight: 'bold', marginBottom: 12 }}>
            Excepción aplicada a {resultado.aplicados} usuario(s) sobre «{resultado.sistema}».{' '}
            <button
              type="button"
              onClick={() => navegar('/rbac/excepciones')}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--verde-profundo)', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Ver excepciones
            </button>
          </p>
        )}
        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        <button className="btn btn-primary" type="submit" disabled={guardando || !seleccionados.size}>
          {guardando ? 'Aplicando…' : 'Aplicar excepción a los usuarios marcados'}
        </button>
      </form>
    </div>
  );
}

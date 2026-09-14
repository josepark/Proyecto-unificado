import { useState } from 'react';
import { Link, useOutletContext, useSearchParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import BannerErrorMutacion from '../../componentes/BannerErrorMutacion';
import { Campo, CampoSelect, CampoTextarea, Fila } from '../../componentes/CamposFormulario';
import { formatearErrorApi } from '../../api/client';
import { mensajeErrorRbac } from './rbacUtil';

export default function Excepciones() {
  const { puedeEditar } = useOutletContext();
  const [searchParams] = useSearchParams();
  const [incluirVencidas, setIncluirVencidas] = useState(searchParams.get('vencidas') === '1');
  const { datos, cargando, error, recargar } = useApi(
    () => rbacApi.listarExcepciones(incluirVencidas ? { vencidas: 1 } : undefined),
    [incluirVencidas],
  );
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: usuarios } = useApi(() => rbacApi.listarUsuarios(), []);
  const { datos: sistemas } = useApi(() => rbacApi.listarSistemas(), []);

  const [retirando, setRetirando] = useState(null);
  const [errorMutacion, setErrorMutacion] = useState(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [form, setForm] = useState({ usuario_id: '', sistema_id: '', nivel: 'L', motivo: '', fecha_fin: '' });

  async function retirar(fila) {
    if (!confirm(`¿Retirar esta excepción? «${fila.usuario}» volverá al nivel ${fila.nivel_rol} de su rol en «${fila.sistema}».`)) return;
    setRetirando(`${fila.usuario_id}:${fila.sistema_id}`);
    setErrorMutacion(null);
    try {
      await rbacApi.eliminarExcepcion(fila.usuario_id, fila.sistema_id);
      recargar();
    } catch (e) {
      setErrorMutacion(e.message || 'No se pudo retirar la excepción.');
    } finally {
      setRetirando(null);
    }
  }

  async function crear(ev) {
    ev.preventDefault();
    setGuardando(true);
    setErrorMutacion(null);
    try {
      await rbacApi.crearExcepcion(form.usuario_id, {
        sistema_id: Number(form.sistema_id),
        nivel: form.nivel,
        motivo: form.motivo.trim(),
        fecha_fin: form.fecha_fin || null,
      });
      setForm({ usuario_id: '', sistema_id: '', nivel: 'L', motivo: '', fecha_fin: '' });
      setMostrarForm(false);
      recargar();
    } catch (e) {
      setErrorMutacion(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('excepciones', error)}
        </div>
      </div>
    );
  }

  const filas = datos?.filas ?? [];
  const niveles = catalogos?.niveles_acceso ?? [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px', flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Excepciones de acceso</h2>
        {puedeEditar && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn btn-sec" onClick={() => setMostrarForm((v) => !v)}>
              {mostrarForm ? 'Ocultar formulario' : '+ Nueva excepción'}
            </button>
            <Link className="btn btn-primary" to="/rbac/excepciones/masiva" style={{ textDecoration: 'none' }}>
              Asignación masiva
            </Link>
          </div>
        )}
      </div>

      <BannerErrorMutacion error={errorMutacion} onCerrar={() => setErrorMutacion(null)} />

      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Diferencias entre el acceso efectivo de una persona y el que otorga su rol, cada una con motivo y responsable
        en la bitácora (control 5.18). {datos?.total_vigentes ?? 0} vigente(s)
        {datos?.total_vencidas ? ` · ${datos.total_vencidas} vencida(s) pendiente(s) de depurar` : ''}.
      </p>

      {puedeEditar && mostrarForm && (
        <form onSubmit={crear} className="card" style={{ marginBottom: 14 }}>
          <h2>Registrar excepción individual</h2>
          <div className="cuerpo">
            <Fila>
              <CampoSelect
                label="Usuario *"
                opciones={[
                  ['', 'Seleccione…'],
                  ...(usuarios ?? []).map((u) => [String(u.id), `${u.nombre} (${u.rol})`]),
                ]}
                value={form.usuario_id}
                required
                onChange={(e) => setForm((f) => ({ ...f, usuario_id: e.target.value }))}
              />
              <CampoSelect
                label="Sistema *"
                opciones={[
                  ['', 'Seleccione…'],
                  ...(sistemas ?? []).map((s) => [String(s.id), s.nombre]),
                ]}
                value={form.sistema_id}
                required
                onChange={(e) => setForm((f) => ({ ...f, sistema_id: e.target.value }))}
              />
              <CampoSelect
                label="Nivel de excepción *"
                opciones={niveles.map((n) => [n.codigo, `${n.codigo} — ${n.nombre}`])}
                value={form.nivel}
                required
                onChange={(e) => setForm((f) => ({ ...f, nivel: e.target.value }))}
              />
            </Fila>
            <Fila>
              <Campo
                label="Vigencia hasta (opcional)"
                type="date"
                value={form.fecha_fin}
                onChange={(e) => setForm((f) => ({ ...f, fecha_fin: e.target.value }))}
              />
            </Fila>
            <CampoTextarea
              label="Motivo *"
              required
              maxLength={400}
              placeholder="Justificación del acceso distinto al rol (control 5.18)"
              value={form.motivo}
              onChange={(e) => setForm((f) => ({ ...f, motivo: e.target.value }))}
            />
            <button type="submit" className="btn btn-primary" disabled={guardando}>
              {guardando ? 'Guardando…' : 'Registrar excepción'}
            </button>
          </div>
        </form>
      )}

      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, marginBottom: 12 }}>
        <input type="checkbox" style={{ width: 'auto' }} checked={incluirVencidas} onChange={(e) => setIncluirVencidas(e.target.checked)} />
        Incluir vencidas
      </label>

      {cargando ? (
        <p>Cargando excepciones…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Estado</th>
              <th>Sistema</th>
              <th>Rol</th>
              <th>Nivel del rol</th>
              <th>Nivel excepción</th>
              <th>Motivo</th>
              <th>Vigencia</th>
              {puedeEditar && <th></th>}
            </tr>
          </thead>
          <tbody>
            {filas.map((e) => (
              <tr key={`${e.usuario_id}:${e.sistema_id}`} style={e.vencida ? { opacity: 0.6 } : undefined}>
                <td>
                  <Link to={`/rbac/usuarios/${e.usuario_id}/editar`}>{e.usuario}</Link>
                </td>
                <td>{e.usuario_estado}</td>
                <td>
                  <Link to={`/rbac/sistemas/${e.sistema_id}/editar`}>{e.sistema}</Link>
                </td>
                <td>{e.rol}</td>
                <td>
                  <span className={`chip niv-${e.nivel_rol === '—' ? 'X' : e.nivel_rol}`}>{e.nivel_rol}</span>
                </td>
                <td>
                  <span className={`chip niv-${e.nivel_excepcion === '—' ? 'X' : e.nivel_excepcion}`}>{e.nivel_excepcion}</span>
                </td>
                <td>{e.motivo}</td>
                <td>
                  {e.fecha_fin ? (
                    <>
                      {e.fecha_fin}
                      {e.vencida && (
                        <>
                          <br />
                          <small style={{ color: 'var(--crit)' }}>vencida</small>
                        </>
                      )}
                    </>
                  ) : (
                    'Indefinida'
                  )}
                </td>
                {puedeEditar && (
                  <td>
                    <button
                      className="btn-sec"
                      disabled={retirando === `${e.usuario_id}:${e.sistema_id}`}
                      onClick={() => retirar(e)}
                    >
                      {retirando === `${e.usuario_id}:${e.sistema_id}` ? 'Retirando…' : 'Retirar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!filas.length && (
              <tr>
                <td colSpan={puedeEditar ? 9 : 8} className="sub">
                  No hay excepciones {incluirVencidas ? 'registradas' : 'vigentes'}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

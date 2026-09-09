import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, CampoTextarea, Fila } from '../../componentes/CamposFormulario';
import { AvisoConsultaRbac, BloqueoCreacionRbac } from '../../componentes/AvisoConsultaRbac';
import { modoFormularioRbac } from './rbacUtil';

const OPC_MFA_ACTIVO = [
  ['No', 'No'],
  ['Sí', 'Sí'],
  ['Sí — sistemas críticos', 'Sí — sistemas críticos'],
];
const OPC_NDA = [
  ['NDA-001', 'NDA-001'],
  ['NDA-002', 'NDA-002'],
  ['NDA-004', 'NDA-004'],
  ['', 'Ninguno'],
];
const OPC_ESTADO_INICIAL = [
  ['Activo', 'Activo'],
  ['Temporal', 'Temporal'],
];

function vacio() {
  return {
    nombre: '', rol_id: '', mfa_activo: 'No', nda: '', estado: 'Activo',
    fecha_inicio: '', fecha_fin: '', notas: '',
  };
}

function desdeUsuario(u) {
  return {
    nombre: u.nombre || '', rol_id: String(u.rol_id ?? ''), mfa_activo: u.mfa_activo || 'No',
    nda: u.nda || '', estado: u.estado || 'Activo',
    fecha_inicio: u.fecha_inicio || '', fecha_fin: u.fecha_fin || '', notas: u.notas || '',
  };
}

export default function UsuarioForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const ctx = useOutletContext() ?? {};
  const { puedeEditar } = ctx;
  const { soloLectura, bloqueado, bloquearCreacion } = modoFormularioRbac(ctx, editando);

  const { datos: usuarioExistente, cargando: cargandoUsuario, error: errorCarga, recargar: recargarUsuario } = useApi(
    () => (editando ? rbacApi.obtenerUsuario(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: roles } = useApi(() => rbacApi.listarRoles(), []);
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: sistemas } = useApi(() => rbacApi.listarSistemas(), []);

  const [form, setForm] = useState(editando ? null : vacio());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [avisoMfa, setAvisoMfa] = useState(false);
  const [excForm, setExcForm] = useState({ sistema_id: '', nivel: 'L', motivo: '', fecha_fin: '' });
  const [guardandoExc, setGuardandoExc] = useState(null);

  useEffect(() => {
    if (editando && usuarioExistente) setForm(desdeUsuario(usuarioExistente));
  }, [editando, usuarioExistente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  if (bloqueado) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'registrar'} usuarios con tu rol actual.{' '}
          <Link to="/rbac/usuarios">Volver</Link>
        </div>
      </div>
    );
  }
  if (bloquearCreacion) {
    return <BloqueoCreacionRbac entidad="usuarios" rutaListado="/rbac/usuarios" />;
  }
  if (editando && (cargandoUsuario || !form)) return <p>Cargando usuario…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar el usuario a editar. <Link to="/rbac/usuarios">Volver</Link>
        </div>
      </div>
    );
  }

  const rolElegido = (roles ?? []).find((r) => String(r.id) === form.rol_id);
  const niveles = catalogos?.niveles_acceso ?? [];

  async function agregarExcepcion(ev) {
    ev.preventDefault();
    setGuardandoExc('nueva');
    setError(null);
    try {
      await rbacApi.crearExcepcion(id, {
        sistema_id: Number(excForm.sistema_id),
        nivel: excForm.nivel,
        motivo: excForm.motivo.trim(),
        fecha_fin: excForm.fecha_fin || null,
      });
      setExcForm({ sistema_id: '', nivel: 'L', motivo: '', fecha_fin: '' });
      recargarUsuario();
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardandoExc(null);
    }
  }

  async function retirarExcepcion(sistemaId) {
    if (!confirm('¿Retirar esta excepción? El usuario volverá al nivel de su rol en ese sistema.')) return;
    setGuardandoExc(String(sistemaId));
    setError(null);
    try {
      await rbacApi.eliminarExcepcion(id, sistemaId);
      recargarUsuario();
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardandoExc(null);
    }
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    setAvisoMfa(false);
    const body = {
      nombre: form.nombre, rol_id: Number(form.rol_id), mfa_activo: form.mfa_activo,
      nda: form.nda, notas: form.notas,
      fecha_inicio: form.fecha_inicio || null, fecha_fin: form.fecha_fin || null,
      ...(editando ? {} : { estado: form.estado }),
    };
    try {
      const resultado = editando
        ? await rbacApi.editarUsuario(id, body)
        : await rbacApi.crearUsuario(body);
      if (resultado.aviso_mfa) {
        // Mismo aviso que ya daba el formulario HTML: el rol exige MFA y el
        // usuario no lo tiene activo — no bloquea el guardado, solo avisa.
        setAvisoMfa(true);
        setGuardando(false);
        return;
      }
      navegar('/rbac/usuarios');
    } catch (e) {
      setError(formatearErrorApi(e));
      setGuardando(false);
    }
  }

  return (
    <div>
      <Link to="/rbac/usuarios" className="volver">
        ← Volver a Usuarios
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? (soloLectura ? form.nombre : `Editar ${form.nombre}`) : 'Registrar usuario'}
      </h2>

      <AvisoConsultaRbac visible={soloLectura} />

      <form onSubmit={guardar}>
        <fieldset disabled={soloLectura} style={{ border: 'none', margin: 0, padding: 0 }}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Identidad y rol</h2>
          <div className="cuerpo">
            <Fila>
              <Campo
                label="Nombre completo *"
                placeholder="Nombre y apellidos, tal como figuran en el documento de identidad"
                value={form.nombre}
                required
                maxLength={120}
                onChange={(e) => set('nombre', e.target.value)}
              />
              <CampoSelect
                label="Rol (Determinación 7 / SGSI) *"
                opciones={[
                  ['', 'Seleccione un rol…'],
                  ...(roles ?? []).map((r) => [String(r.id), `${r.abreviatura} — ${r.denominacion}`]),
                ]}
                value={form.rol_id}
                required
                onChange={(e) => set('rol_id', e.target.value)}
              />
            </Fila>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Cumplimiento</h2>
          <div className="cuerpo">
            <Fila columnas={3}>
              <CampoSelect
                label="MFA activo"
                opciones={OPC_MFA_ACTIVO}
                value={form.mfa_activo}
                onChange={(e) => set('mfa_activo', e.target.value)}
              />
              <CampoSelect
                label="NDA firmado"
                opciones={OPC_NDA}
                value={form.nda}
                onChange={(e) => set('nda', e.target.value)}
              />
              <div>
                {rolElegido && (
                  <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 22 }}>
                    Este rol exige MFA: <b>{rolElegido.mfa_requerido}</b>
                  </p>
                )}
              </div>
            </Fila>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Vigencia del acceso</h2>
          <div className="cuerpo">
            {!editando && (
              <div style={{ marginBottom: 12 }}>
                <CampoSelect
                  label="Estado inicial"
                  opciones={OPC_ESTADO_INICIAL}
                  value={form.estado}
                  onChange={(e) => set('estado', e.target.value)}
                />
              </div>
            )}
            <Fila>
              <Campo
                label="Fecha de inicio"
                type="date"
                value={form.fecha_inicio}
                onChange={(e) => set('fecha_inicio', e.target.value)}
              />
              <Campo
                label="Fecha de fin"
                type="date"
                value={form.fecha_fin}
                onChange={(e) => set('fecha_fin', e.target.value)}
              />
            </Fila>
            <p style={{ fontSize: 12, color: 'var(--texto-suave)', margin: 0 }}>
              {editando
                ? 'Solo aplican si el estado es Temporal (control 5.18). El estado en sí se cambia desde el listado de Usuarios, no desde aquí, para dejar el motivo documentado.'
                : 'El acceso Temporal exige fecha de inicio y de fin (control 5.18); al vencer, el sistema suspende al usuario automáticamente.'}
            </p>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Observaciones</h2>
          <div className="cuerpo">
            <CampoTextarea
              label="Notas"
              maxLength={400}
              placeholder="Contexto opcional: proveedor, área, motivo del acceso…"
              value={form.notas}
              onChange={(e) => set('notas', e.target.value)}
            />
          </div>
        </div>

        {avisoMfa && (
          <p style={{ color: 'var(--alto)', fontWeight: 'bold', marginBottom: 12 }}>
            Advertencia: el rol seleccionado exige MFA y el usuario no lo tiene activo. Los cambios se guardaron —
            corrija el MFA cuando corresponda, o{' '}
            <button
              type="button"
              onClick={() => navegar('/rbac/usuarios')}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--verde-profundo)', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold' }}
            >
              continuar a la lista
            </button>
            .
          </p>
        )}
        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        {!soloLectura && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" type="submit" disabled={guardando}>
              {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Registrar usuario'}
            </button>
            <Link to="/rbac/usuarios" className="btn btn-sec" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
              Cancelar
            </Link>
          </div>
        )}
        </fieldset>
      </form>

      {editando && (usuarioExistente?.accesos?.length ?? 0) > 0 && (
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Accesos efectivos (matriz + excepciones)</h2>
            <div className="cuerpo" style={{ padding: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>Sistema</th>
                    <th>Categoría</th>
                    <th>Nivel rol</th>
                    <th>Excepción</th>
                    <th>Efectivo</th>
                    {!soloLectura && <th></th>}
                  </tr>
                </thead>
                <tbody>
                  {usuarioExistente.accesos
                    .filter((a) => a.nivel_efectivo && a.nivel_efectivo !== '—')
                    .map((a) => (
                      <tr key={a.sistema_id} style={a.nivel_exc ? { background: '#fdf1e4' } : undefined}>
                        <td>{a.nombre}</td>
                        <td>{a.categoria}</td>
                        <td>{a.nivel_rol}</td>
                        <td>{a.nivel_exc ? `${a.nivel_exc}${a.motivo ? ` — ${a.motivo}` : ''}` : '—'}</td>
                        <td><strong>{a.nivel_efectivo}</strong></td>
                        {!soloLectura && (
                          <td>
                            {a.nivel_exc ? (
                              <button
                                type="button"
                                className="btn-sec"
                                disabled={guardandoExc === String(a.sistema_id)}
                                onClick={() => retirarExcepcion(a.sistema_id)}
                              >
                                {guardandoExc === String(a.sistema_id) ? '…' : 'Retirar'}
                              </button>
                            ) : null}
                          </td>
                        )}
                      </tr>
                    ))}
                </tbody>
              </table>
              <p style={{ fontSize: 12, color: 'var(--texto-suave)', margin: '8px 14px 0' }}>
                Las filas resaltadas tienen excepción vigente. Para cambiar la matriz base, use la{' '}
                <Link to="/rbac/matriz">Matriz</Link>.
              </p>
            </div>
          </div>
        )}

      {editando && !soloLectura && (
          <form onSubmit={agregarExcepcion} className="card" style={{ marginBottom: 14 }}>
            <h2>Nueva excepción de acceso</h2>
            <div className="cuerpo">
              <Fila>
                <CampoSelect
                  label="Sistema *"
                  opciones={[
                    ['', 'Seleccione…'],
                    ...(sistemas ?? []).map((s) => [String(s.id), s.nombre]),
                  ]}
                  value={excForm.sistema_id}
                  required
                  onChange={(e) => setExcForm((f) => ({ ...f, sistema_id: e.target.value }))}
                />
                <CampoSelect
                  label="Nivel *"
                  opciones={niveles.map((n) => [n.codigo, `${n.codigo} — ${n.nombre}`])}
                  value={excForm.nivel}
                  required
                  onChange={(e) => setExcForm((f) => ({ ...f, nivel: e.target.value }))}
                />
                <Campo
                  label="Vigencia hasta"
                  type="date"
                  value={excForm.fecha_fin}
                  onChange={(e) => setExcForm((f) => ({ ...f, fecha_fin: e.target.value }))}
                />
              </Fila>
              <CampoTextarea
                label="Motivo *"
                required
                maxLength={400}
                placeholder="Justificación del acceso distinto al rol (control 5.18)"
                value={excForm.motivo}
                onChange={(e) => setExcForm((f) => ({ ...f, motivo: e.target.value }))}
              />
              <button type="submit" className="btn btn-sec" disabled={guardandoExc === 'nueva'}>
                {guardandoExc === 'nueva' ? 'Guardando…' : 'Agregar excepción'}
              </button>
            </div>
          </form>
        )}
    </div>
  );
}

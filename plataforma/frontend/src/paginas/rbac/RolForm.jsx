import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, CampoTextarea, Fila } from '../../componentes/CamposFormulario';

const OPC_SI_NO_DET7 = [
  ['1', 'Sí'],
  ['0', 'No — rol SGSI'],
];
const OPC_MFA = [
  ['No', 'No'],
  ['Sí — sistemas críticos', 'Sí — sistemas críticos'],
  ['Sí — obligatorio', 'Sí — obligatorio'],
  ['N/A', 'N/A'],
];
const OPC_REVISION = [
  ['Semestral', 'Semestral'],
  ['Trimestral', 'Trimestral'],
  ['Mensual', 'Mensual'],
  ['Anual', 'Anual'],
];

function vacio() {
  return {
    codigo: '', abreviatura: '', denominacion: '', grupo_id: '', cosecha: '',
    en_det7: '1', mfa_requerido: 'No', riesgo_attack: 'Bajo', revision_periodica: 'Semestral',
    funcion: '', observaciones: '', clonar_de: '',
  };
}

function desdeRol(r) {
  return {
    codigo: r.codigo || '', abreviatura: r.abreviatura || '', denominacion: r.denominacion || '',
    grupo_id: String(r.grupo_id ?? ''), cosecha: r.cosecha || '',
    en_det7: r.en_det7 ? '1' : '0', mfa_requerido: r.mfa_requerido || 'No',
    riesgo_attack: r.riesgo_attack || 'Bajo', revision_periodica: r.revision_periodica || 'Semestral',
    funcion: r.funcion || '', observaciones: r.observaciones || '', clonar_de: '',
  };
}

export default function RolForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEditar } = useOutletContext() ?? {};

  const { datos: rolExistente, cargando: cargandoRol, error: errorCarga, recargar } = useApi(
    () => (editando ? rbacApi.obtenerRol(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: rolesParaClonar } = useApi(
    () => (editando ? Promise.resolve(null) : rbacApi.listarRoles()),
    [editando],
  );

  const [form, setForm] = useState(editando ? null : vacio());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [nota, setNota] = useState('');
  const [certificando, setCertificando] = useState(false);
  const [cambiandoEstado, setCambiandoEstado] = useState(false);
  const [eliminando, setEliminando] = useState(false);

  useEffect(() => {
    if (editando && rolExistente) setForm(desdeRol(rolExistente));
  }, [editando, rolExistente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'crear'} roles con tu rol actual.{' '}
          <Link to="/rbac/roles">Volver</Link>
        </div>
      </div>
    );
  }
  if (editando && (cargandoRol || !form)) return <p>Cargando rol…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar el rol a editar. <Link to="/rbac/roles">Volver</Link>
        </div>
      </div>
    );
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    const body = {
      codigo: form.codigo, abreviatura: form.abreviatura, denominacion: form.denominacion,
      grupo_id: Number(form.grupo_id), cosecha: form.cosecha, en_det7: form.en_det7,
      mfa_requerido: form.mfa_requerido, riesgo_attack: form.riesgo_attack,
      revision_periodica: form.revision_periodica, funcion: form.funcion,
      observaciones: form.observaciones,
    };
    if (!editando && form.clonar_de) body.clonar_de = form.clonar_de;

    try {
      const resultado = editando
        ? await rbacApi.editarRol(id, body)
        : await rbacApi.crearRol(body);
      navegar(`/rbac/roles/${resultado.id}/editar`);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  async function marcarRevisado() {
    setCertificando(true);
    try {
      await rbacApi.certificarRol(id, nota);
      setNota('');
      recargar();
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setCertificando(false);
    }
  }

  async function alternarActivo() {
    setCambiandoEstado(true);
    setError(null);
    try {
      await rbacApi.toggleActivoRol(id);
      recargar();
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setCambiandoEstado(false);
    }
  }

  async function eliminar() {
    if (!window.confirm(`¿Eliminar definitivamente el rol ${form.abreviatura}? Esta acción borra su fila de la matriz y no se puede deshacer. Si desea conservar el historial, use Desactivar.`)) return;
    setEliminando(true);
    setError(null);
    try {
      await rbacApi.eliminarRol(id);
      navegar('/rbac/roles');
    } catch (e) {
      setError(formatearErrorApi(e));
      setEliminando(false);
    }
  }

  const grupos = catalogos?.grupos_rol ?? [];
  const riesgos = catalogos?.riesgos_attack ?? ['Bajo', 'Medio', 'Alto'];

  return (
    <div>
      <Link to="/rbac/roles" className="volver">
        ← Volver a Roles
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? `Editar rol ${form.abreviatura}` : 'Nuevo rol'}
        {editando && rolExistente && !rolExistente.activo && (
          <span className="tag t-CRIT" style={{ marginLeft: 10, verticalAlign: 'middle' }}>
            DESACTIVADO
          </span>
        )}
      </h2>

      <form onSubmit={guardar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Identificación</h2>
          <div className="cuerpo">
            <Fila columnas={3}>
              <Campo label="Código *" value={form.codigo} required onChange={(e) => set('codigo', e.target.value)} />
              <Campo label="Abreviatura *" value={form.abreviatura} required onChange={(e) => set('abreviatura', e.target.value)} />
              <Campo label="Cosecha" placeholder="01 al 05 / N/A" value={form.cosecha} onChange={(e) => set('cosecha', e.target.value)} />
            </Fila>
            <div style={{ marginBottom: 12 }}>
              <Campo
                label="Denominación oficial *"
                value={form.denominacion}
                required
                onChange={(e) => set('denominacion', e.target.value)}
              />
            </div>
            <Fila>
              <CampoSelect
                label="Grupo *"
                opciones={grupos.map((g) => [String(g.id), g.nombre])}
                value={form.grupo_id}
                onChange={(e) => set('grupo_id', e.target.value)}
              />
              <CampoSelect
                label="¿En Determinación 7?"
                opciones={OPC_SI_NO_DET7}
                value={form.en_det7}
                onChange={(e) => set('en_det7', e.target.value)}
              />
            </Fila>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Seguridad y cumplimiento</h2>
          <div className="cuerpo">
            <Fila columnas={3}>
              <CampoSelect
                label="MFA requerido"
                opciones={OPC_MFA}
                value={form.mfa_requerido}
                onChange={(e) => set('mfa_requerido', e.target.value)}
              />
              <CampoSelect
                label="Riesgo ATT&CK"
                opciones={riesgos.map((r) => [r, r])}
                value={form.riesgo_attack}
                onChange={(e) => set('riesgo_attack', e.target.value)}
              />
              <CampoSelect
                label="Periodicidad de revisión (POL-SI-002)"
                opciones={OPC_REVISION}
                value={form.revision_periodica}
                onChange={(e) => set('revision_periodica', e.target.value)}
              />
            </Fila>
          </div>
        </div>

        {!editando && (
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Accesos iniciales</h2>
            <div className="cuerpo">
              <CampoSelect
                label="Clonar accesos desde"
                opciones={[
                  ['', 'Ninguno — iniciar sin accesos'],
                  ...(rolesParaClonar ?? []).map((r) => [String(r.id), `${r.abreviatura} — ${r.denominacion}`]),
                ]}
                value={form.clonar_de}
                onChange={(e) => set('clonar_de', e.target.value)}
              />
              <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 8, marginBottom: 0 }}>
                Si no clona un rol existente, la fila del nuevo rol en la matriz se inicializa sin accesos
                (mínimo privilegio); defínalos luego en la Matriz.
              </p>
            </div>
          </div>
        )}

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Función y observaciones</h2>
          <div className="cuerpo">
            <CampoTextarea
              label="Función (Decisión No. 02)"
              style={{ marginBottom: 12 }}
              value={form.funcion}
              onChange={(e) => set('funcion', e.target.value)}
            />
            <CampoTextarea
              label="Observaciones SI"
              value={form.observaciones}
              onChange={(e) => set('observaciones', e.target.value)}
            />
          </div>
        </div>

        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear rol'}
          </button>
          <Link to="/rbac/roles" className="btn btn-sec" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
            Cancelar
          </Link>
        </div>
      </form>

      {editando && rolExistente?.activo && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Certificación periódica de accesos</h2>
          <div className="cuerpo">
            <p style={{ fontSize: 13, marginTop: 0 }}>
              Periodicidad declarada: <b>{rolExistente.revision_periodica}</b> · Última revisión:{' '}
              <span style={{ color: rolExistente.revision_vencida ? 'var(--alto)' : 'inherit' }}>
                {rolExistente.ultima_revision || 'nunca revisada'}
                {rolExistente.revision_vencida ? ' — vencida' : ''}
              </span>
            </p>
            <Fila columnas={1}>
              <Campo
                label="Nota de la revisión (opcional)"
                placeholder="Ej.: se confirmaron los accesos con el responsable del área"
                value={nota}
                onChange={(e) => setNota(e.target.value)}
              />
            </Fila>
            <button className="btn btn-sec" onClick={marcarRevisado} disabled={certificando}>
              {certificando ? 'Guardando…' : 'Marcar como revisado hoy'}
            </button>
          </div>
        </div>
      )}

      {editando && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Accesos y usuarios</h2>
          <div className="cuerpo">
            <p style={{ fontSize: 13, margin: 0 }}>
              {rolExistente?.accesos?.length ?? 0} acceso(s) definidos · {rolExistente?.usuarios?.length ?? 0} usuario(s) con este rol.{' '}
              Para cambiar los niveles de acceso, use la <Link to="/rbac/matriz">Matriz</Link>.
            </p>
          </div>
        </div>
      )}

      {editando && (
        <div className="card">
          <h2>Zona de baja</h2>
          <div className="cuerpo" style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-sec" onClick={alternarActivo} disabled={cambiandoEstado}>
              {cambiandoEstado ? 'Guardando…' : rolExistente?.activo ? 'Desactivar rol' : 'Reactivar rol'}
            </button>
            {puedeEditar && (
              <button className="btn btn-sec" onClick={eliminar} disabled={eliminando} style={{ color: 'var(--crit)' }}>
                {eliminando ? 'Eliminando…' : 'Eliminar rol'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

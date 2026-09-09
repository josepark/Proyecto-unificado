import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, Fila } from '../../componentes/CamposFormulario';
import { CampoCodigosCatalogo } from '../../componentes/CampoCodigosCatalogo';

const OPC_CLASIFICACION = [
  ['Altamente Confidencial', 'Altamente Confidencial'],
  ['Confidencial', 'Confidencial'],
  ['Interna', 'Interna'],
  ['Pública', 'Pública'],
];

function vacio() {
  return { nombre: '', categoria_id: '', categoria_nueva: '', clasificacion: 'Interna', tecnicas_attack: '' };
}

function desdeSistema(s) {
  return {
    nombre: s.nombre || '', categoria_id: String(s.categoria_id ?? ''), categoria_nueva: '',
    clasificacion: s.clasificacion || 'Interna', tecnicas_attack: s.tecnicas_attack || '',
  };
}

export default function SistemaForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEditar } = useOutletContext() ?? {};

  const { datos: sistemaExistente, cargando: cargandoSistema, error: errorCarga, recargar } = useApi(
    () => (editando ? rbacApi.obtenerSistema(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos: catalogoMitre, cargando: cargandoMitre, error: errorMitre } = useApi(
    () => inventarioApi.amenazas().then((r) => r.results || r),
    [],
  );

  const [form, setForm] = useState(editando ? null : vacio());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [cambiandoEstado, setCambiandoEstado] = useState(false);
  const [eliminando, setEliminando] = useState(false);

  useEffect(() => {
    if (editando && sistemaExistente) setForm(desdeSistema(sistemaExistente));
  }, [editando, sistemaExistente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'crear'} sistemas con tu rol actual.{' '}
          <Link to="/rbac/sistemas">Volver</Link>
        </div>
      </div>
    );
  }
  if (editando && (cargandoSistema || !form)) return <p>Cargando sistema…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar el sistema a editar. <Link to="/rbac/sistemas">Volver</Link>
        </div>
      </div>
    );
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    const body = {
      nombre: form.nombre, clasificacion: form.clasificacion,
      // Codigos separados por "/" (no coma) — asi los valida el backend
      // (rutas._validar_datos_sistema), igual que ya hacia el formulario HTML.
      tecnicas_attack: form.tecnicas_attack,
      ...(form.categoria_nueva.trim()
        ? { categoria_nueva: form.categoria_nueva.trim() }
        : { categoria_id: Number(form.categoria_id) }),
    };
    try {
      const resultado = editando
        ? await rbacApi.editarSistema(id, body)
        : await rbacApi.crearSistema(body);
      navegar(`/rbac/sistemas/${resultado.id}/editar`);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  async function alternarActivo() {
    setCambiandoEstado(true);
    setError(null);
    try {
      await rbacApi.toggleActivoSistema(id);
      recargar();
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setCambiandoEstado(false);
    }
  }

  async function eliminar() {
    if (!window.confirm(`¿Eliminar definitivamente «${form.nombre}»? Esta acción borra su columna de la matriz y no se puede deshacer. Si desea conservar el historial, use Desactivar.`)) return;
    setEliminando(true);
    setError(null);
    try {
      await rbacApi.eliminarSistema(id);
      navegar('/rbac/sistemas');
    } catch (e) {
      setError(formatearErrorApi(e));
      setEliminando(false);
    }
  }

  const categorias = catalogos?.categorias_sistema ?? [];

  return (
    <div>
      <Link to="/rbac/sistemas" className="volver">
        ← Volver a Sistemas
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? `Editar ${form.nombre}` : 'Crear sistema / recurso'}
        {editando && sistemaExistente && !sistemaExistente.activo && (
          <span className="tag t-CRIT" style={{ marginLeft: 10, verticalAlign: 'middle' }}>
            DESACTIVADO
          </span>
        )}
      </h2>

      <form onSubmit={guardar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Identificación</h2>
          <div className="cuerpo">
            <div style={{ marginBottom: 12 }}>
              <Campo label="Nombre *" value={form.nombre} required onChange={(e) => set('nombre', e.target.value)} />
            </div>
            <Fila>
              <CampoSelect
                label={form.categoria_nueva ? 'Categoría existente (ignorada, hay una nueva abajo)' : 'Categoría existente'}
                opciones={categorias.map((c) => [String(c.id), c.nombre])}
                value={form.categoria_id}
                disabled={Boolean(form.categoria_nueva.trim())}
                onChange={(e) => set('categoria_id', e.target.value)}
              />
              <Campo
                label="…o nueva categoría"
                placeholder="Dejar vacío si no aplica"
                value={form.categoria_nueva}
                onChange={(e) => set('categoria_nueva', e.target.value)}
              />
            </Fila>
            <div style={{ maxWidth: 'calc(50% - 6px)' }}>
              <CampoSelect
                label="Clasificación"
                opciones={OPC_CLASIFICACION}
                value={form.clasificacion}
                onChange={(e) => set('clasificacion', e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Técnicas ATT&amp;CK</h2>
          <div className="cuerpo">
            <CampoCodigosCatalogo
              label="Códigos separados por «/» (p. ej. T1566/T1190)"
              placeholder="T1566/T1190 — escriba T para ver sugerencias"
              separador="/"
              value={form.tecnicas_attack}
              onChange={(v) => set('tecnicas_attack', v)}
              items={catalogoMitre || []}
              cargando={cargandoMitre}
              errorCatalogo={errorMitre}
              filtrarItem={(a) => a.tipo === 'TE' || a.tipo === 'ST'}
            />
            <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 8, marginBottom: 0 }}>
              Cada código debe existir en el catálogo MITRE ATT&CK ya sincronizado; el backend rechaza técnicas no reconocidas.
            </p>
          </div>
        </div>

        {!editando && (
          <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginBottom: 14 }}>
            Al crear un sistema, su columna en la matriz se inicializa sin accesos; defínalos luego en la Matriz.
          </p>
        )}

        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear sistema'}
          </button>
          <Link to="/rbac/sistemas" className="btn btn-sec" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
            Cancelar
          </Link>
        </div>
      </form>

      {editando && (
        <>
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Roles con acceso ({sistemaExistente?.roles?.length ?? 0})</h2>
            <div className="cuerpo">
              {sistemaExistente?.roles?.length ? (
                <table>
                  <thead>
                    <tr>
                      <th>Rol</th>
                      <th>Denominación</th>
                      <th>Nivel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sistemaExistente.roles.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <Link to={`/rbac/roles/${r.id}/editar`}>
                            <b>{r.abreviatura}</b>
                          </Link>
                        </td>
                        <td>{r.denominacion}</td>
                        <td>
                          <span className={`chip niv-${r.nivel}`}>{r.nivel}</span> {r.nivel_nombre}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ fontSize: 13, margin: 0 }}>Ningún rol tiene acceso a este sistema todavía.</p>
              )}
              <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 10, marginBottom: 0 }}>
                Para cambiar los niveles de acceso, use la <Link to="/rbac/matriz">Matriz</Link>.
              </p>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Usuarios con acceso efectivo ({sistemaExistente?.usuarios?.length ?? 0})</h2>
            <div className="cuerpo">
              {sistemaExistente?.usuarios?.length ? (
                <table>
                  <thead>
                    <tr>
                      <th>Usuario</th>
                      <th>Rol</th>
                      <th>Nivel</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sistemaExistente.usuarios.map((u, i) => (
                      <tr key={i}>
                        <td>{u.nombre}</td>
                        <td>{u.rol}</td>
                        <td>
                          <span className={`tag ${u.nivel === '—' ? '' : ''}`}>{u.nivel}</span>
                          {u.es_excepcion ? ' (excepción)' : ''}
                        </td>
                        <td>{u.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ fontSize: 13, margin: 0 }}>Ningún usuario registrado tiene acceso efectivo a este recurso.</p>
              )}
            </div>
          </div>

          <div className="card">
            <h2>Zona de baja</h2>
            <div className="cuerpo" style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-sec" onClick={alternarActivo} disabled={cambiandoEstado}>
                {cambiandoEstado ? 'Guardando…' : sistemaExistente?.activo ? 'Desactivar sistema' : 'Reactivar sistema'}
              </button>
              <button className="btn btn-sec" onClick={eliminar} disabled={eliminando} style={{ color: 'var(--crit)' }}>
                {eliminando ? 'Eliminando…' : 'Eliminar sistema'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

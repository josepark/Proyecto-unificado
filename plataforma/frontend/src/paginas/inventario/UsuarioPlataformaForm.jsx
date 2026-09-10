import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, Fila } from '../../componentes/CamposFormulario';
import { MODULOS_PLATAFORMA } from '../../lib/modulosPlataforma';

const ROLES = [
  ['Consultor', 'Consultor — solo lectura'],
  ['Dinamizador', 'Dinamizador — lectura y escritura'],
  ['Administrador', 'Administrador — control total'],
];

function vacio() {
  return {
    username: '',
    password: '',
    password2: '',
    email: '',
    first_name: '',
    last_name: '',
    rol: 'Consultor',
    area: '',
    modulos_acceso: [],
    is_active: true,
  };
}

function desdeUsuario(u) {
  return {
    username: u.username || '',
    password: '',
    password2: '',
    email: u.email || '',
    first_name: u.first_name || '',
    last_name: u.last_name || '',
    rol: u.rol || 'Consultor',
    area: u.area || '',
    modulos_acceso: u.modulos_acceso?.length
      ? u.modulos_acceso
      : MODULOS_PLATAFORMA.map((m) => m.id),
    is_active: u.is_active !== false,
  };
}

export default function UsuarioPlataformaForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEliminar } = useOutletContext() ?? {};

  const { datos: existente, cargando, error: errorCarga } = useApi(
    () => (editando ? inventarioApi.obtenerUsuarioPlataforma(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: meta } = useApi(() => inventarioApi.metaUsuariosPlataforma(), []);

  const [form, setForm] = useState(editando ? null : vacio());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (editando && existente) setForm(desdeUsuario(existente));
  }, [editando, existente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  function alternarModulo(id) {
    setForm((f) => {
      const actuales = new Set(f.modulos_acceso || []);
      if (actuales.has(id)) actuales.delete(id);
      else actuales.add(id);
      return { ...f, modulos_acceso: MODULOS_PLATAFORMA.map((m) => m.id).filter((x) => actuales.has(x)) };
    });
  }

  const esAdmin = form?.rol === 'Administrador' || existente?.is_superuser;

  if (puedeEliminar === false) {
    return <Navigate to="/inventario/usuarios" replace />;
  }

  if (editando && (cargando || !form)) return <p>Cargando cuenta…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar la cuenta. <Link to="/inventario/usuarios">Volver</Link>
        </div>
      </div>
    );
  }

  async function guardar(ev) {
    ev.preventDefault();
    setError(null);

    if (!editando && form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (form.password && form.password !== form.password2) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    if (!esAdmin && !(form.modulos_acceso || []).length) {
      setError('Seleccione al menos un proyecto.');
      return;
    }

    const payload = {
      username: form.username.trim(),
      email: form.email.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      rol: form.rol,
      area: form.area.trim(),
      modulos_acceso: esAdmin ? MODULOS_PLATAFORMA.map((m) => m.id) : form.modulos_acceso,
      is_active: form.is_active,
    };
    if (form.password) payload.password = form.password;

    setGuardando(true);
    try {
      if (editando) {
        await inventarioApi.editarUsuarioPlataforma(id, payload);
      } else {
        await inventarioApi.crearUsuarioPlataforma(payload);
      }
      navegar('/inventario/usuarios');
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/inventario/usuarios" className="sub">
          ← Cuentas de acceso
        </Link>
        <h2 style={{ margin: '8px 0 0', color: 'var(--verde-profundo)' }}>
          {editando ? `Editar «${form.username}»` : 'Nueva cuenta de acceso'}
        </h2>
      </div>

      {error ? (
        <div className="aviso aviso-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      ) : null}

      <form onSubmit={guardar} className="card">
        <div className="cuerpo">
          <h3 style={{ marginTop: 0 }}>Identidad</h3>
          <Fila columnas={2}>
            <Campo
              label="Usuario (login) *"
              value={form.username}
              onChange={(e) => set('username', e.target.value)}
              required
              autoComplete="off"
              disabled={editando && existente?.is_superuser}
            />
            <Campo
              label="Correo electrónico"
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              autoComplete="off"
            />
          </Fila>
          <Fila columnas={2}>
            <Campo
              label="Nombre"
              value={form.first_name}
              onChange={(e) => set('first_name', e.target.value)}
            />
            <Campo
              label="Apellido"
              value={form.last_name}
              onChange={(e) => set('last_name', e.target.value)}
            />
          </Fila>
          <Campo
            label="Área organizacional"
            value={form.area}
            onChange={(e) => set('area', e.target.value)}
            list="areas-form-plataforma"
            placeholder="Ej: UAIIN, TIC, Jurídica, Planeación…"
          />
          <datalist id="areas-form-plataforma">
            {(meta?.areas ?? []).map((a) => (
              <option key={a} value={a} />
            ))}
          </datalist>

          <h3>Acceso</h3>
          <Fila columnas={2}>
            <CampoSelect
              label="Rol en la plataforma *"
              opciones={ROLES}
              value={form.rol}
              onChange={(e) => set('rol', e.target.value)}
              disabled={editando && existente?.is_superuser}
            />
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => set('is_active', e.target.checked)}
                />
                Cuenta activa
              </label>
            </div>
          </Fila>

          <h3>Proyectos con acceso</h3>
          <p className="sub" style={{ marginTop: 0 }}>
            {esAdmin
              ? 'Los Administradores tienen acceso a todos los proyectos de la plataforma.'
              : editando
                ? 'Módulos que puede ver este usuario. Debe haber al menos uno marcado.'
                : 'Marque los proyectos a los que tendrá acceso. Debe seleccionar al menos uno antes de guardar.'}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {MODULOS_PLATAFORMA.map((m) => (
              <label
                key={m.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 14,
                  opacity: esAdmin ? 0.7 : 1,
                }}
              >
                <input
                  type="checkbox"
                  checked={
                    esAdmin
                      ? true
                      : (form.modulos_acceso || []).includes(m.id)
                  }
                  onChange={() => alternarModulo(m.id)}
                  disabled={esAdmin}
                />
                {m.etiqueta}
              </label>
            ))}
          </div>

          <h3>{editando ? 'Nueva contraseña (opcional)' : 'Contraseña *'}</h3>
          <Fila columnas={2}>
            <Campo
              label={editando ? 'Contraseña' : 'Contraseña *'}
              type="password"
              value={form.password}
              onChange={(e) => set('password', e.target.value)}
              required={!editando}
              autoComplete="new-password"
            />
            <Campo
              label="Confirmar contraseña"
              type="password"
              value={form.password2}
              onChange={(e) => set('password2', e.target.value)}
              required={!editando && Boolean(form.password)}
              autoComplete="new-password"
            />
          </Fila>

          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            <button type="submit" className="btn btn-primary" disabled={guardando}>
              {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear cuenta'}
            </button>
            <Link to="/inventario/usuarios" className="btn-sec" style={{ lineHeight: '32px', textDecoration: 'none' }}>
              Cancelar
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}

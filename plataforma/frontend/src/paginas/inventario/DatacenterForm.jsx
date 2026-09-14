import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, Fila } from '../../componentes/CamposFormulario';
import { useInventarioMeta } from '../../hooks/useInventarioMeta';

const OPC_TIPO_FALLBACK = [
  ['PRIN', 'Datacenter principal'],
  ['MINI', 'Mini-datacenter'],
  ['DR', 'Sitio de respaldo (DR)'],
  ['CLOUD', 'Nube / Colocation'],
];
const OPC_TIER_FALLBACK = [
  ['NA', 'No clasificado'],
  ['T1', 'Tier I'],
  ['T2', 'Tier II'],
  ['T3', 'Tier III'],
  ['T4', 'Tier IV'],
];

function vacio() {
  return {
    codigo: '', nombre: '', tipo: 'PRIN', nivel_tier: 'NA', responsable: '',
    direccion: '', ciudad: '', departamento: '', latitud: '', longitud: '', descripcion: '',
  };
}

function desdeDatacenter(c) {
  return {
    codigo: c.codigo || '', nombre: c.nombre || '', tipo: c.tipo || 'PRIN',
    nivel_tier: c.nivel_tier || 'NA', responsable: c.responsable || '',
    direccion: c.direccion || '', ciudad: c.ciudad || '', departamento: c.departamento || '',
    latitud: c.latitud ?? '', longitud: c.longitud ?? '', descripcion: c.descripcion || '',
  };
}

function numOrNull(v) {
  return v === '' || v === null || v === undefined ? null : Number(v);
}

export default function DatacenterForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEditar, puedeEliminar } = useOutletContext() ?? {};
  const { meta } = useInventarioMeta();

  const opcTipo = (meta?.datacenter?.tipos ?? []).map((t) => [t.codigo, t.nombre]);
  const opcTier = (meta?.datacenter?.tiers ?? []).map((t) => [t.codigo, t.nombre]);

  const { datos: existente, cargando: cargandoDc, error: errorCarga } = useApi(
    () => (editando ? inventarioApi.obtenerDatacenter(id) : Promise.resolve(null)),
    [id],
  );

  const [form, setForm] = useState(vacio());
  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (editando && existente) setForm(desdeDatacenter(existente));
  }, [editando, existente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'crear'} centros de datos con tu rol actual.{' '}
          <Link to="/inventario/centro-datos">Volver</Link>
        </div>
      </div>
    );
  }
  if (editando && cargandoDc) return <p>Cargando centro de datos…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se encontró ese centro de datos. <Link to="/inventario/centro-datos">Volver</Link>
        </div>
      </div>
    );
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    const body = {
      codigo: form.codigo, nombre: form.nombre, tipo: form.tipo, nivel_tier: form.nivel_tier,
      responsable: form.responsable, direccion: form.direccion, ciudad: form.ciudad,
      departamento: form.departamento, latitud: numOrNull(form.latitud), longitud: numOrNull(form.longitud),
      descripcion: form.descripcion, pais: 'Colombia',
    };
    try {
      if (editando) await inventarioApi.editarDatacenter(id, body);
      else await inventarioApi.crearDatacenter(body);
      navegar('/inventario/centro-datos');
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar() {
    const n = existente?.num_activos ?? 0;
    const msg = n
      ? `Este centro tiene ${n} activo(s) asignado(s). Si elimina, quedarán sin sede. ¿Continuar?`
      : `¿Eliminar el centro de datos ${form.codigo}?`;
    if (!window.confirm(msg)) return;
    setEliminando(true);
    setError(null);
    try {
      await inventarioApi.eliminarDatacenter(id, n > 0);
      navegar('/inventario/centro-datos');
    } catch (e) {
      const det = e.data?.detail;
      if (e.status === 409 && det && n > 0 && window.confirm(`${det}\n\n¿Confirmar eliminación?`)) {
        try {
          await inventarioApi.eliminarDatacenter(id, true);
          navegar('/inventario/centro-datos');
          return;
        } catch (e2) {
          setError(formatearErrorApi(e2));
        }
      } else {
        setError(formatearErrorApi(e));
      }
    } finally {
      setEliminando(false);
    }
  }

  return (
    <div>
      <Link to="/inventario/centro-datos" className="volver">
        ← Volver a Centro de datos
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? `Editar ${form.codigo}` : 'Nuevo centro de datos'}
      </h2>
      {editando && existente?.num_activos > 0 && (
        <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
          {existente.num_activos} activo(s) asignados a este centro.
        </p>
      )}

      <form onSubmit={guardar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Identificación</h2>
          <div className="cuerpo">
            <Fila>
              <Campo
                label="Código *"
                value={form.codigo}
                required
                readOnly={editando}
                onChange={(e) => set('codigo', e.target.value)}
              />
              <CampoSelect
                label="Tipo"
                opciones={opcTipo.length ? opcTipo : OPC_TIPO_FALLBACK}
                value={form.tipo}
                onChange={(e) => set('tipo', e.target.value)}
              />
            </Fila>
            <div style={{ marginBottom: 12 }}>
              <Campo label="Nombre *" value={form.nombre} required onChange={(e) => set('nombre', e.target.value)} />
            </div>
            <Fila>
              <CampoSelect
                label="Nivel Tier"
                opciones={opcTier.length ? opcTier : OPC_TIER_FALLBACK}
                value={form.nivel_tier}
                onChange={(e) => set('nivel_tier', e.target.value)}
              />
              <Campo label="Responsable" value={form.responsable} onChange={(e) => set('responsable', e.target.value)} />
            </Fila>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Ubicación</h2>
          <div className="cuerpo">
            <div style={{ marginBottom: 12 }}>
              <Campo label="Dirección" value={form.direccion} onChange={(e) => set('direccion', e.target.value)} />
            </div>
            <Fila>
              <Campo label="Ciudad" value={form.ciudad} onChange={(e) => set('ciudad', e.target.value)} />
              <Campo label="Departamento" value={form.departamento} onChange={(e) => set('departamento', e.target.value)} />
            </Fila>
            <Fila>
              <Campo label="Latitud" placeholder="Ej: 2.4448" value={form.latitud} onChange={(e) => set('latitud', e.target.value)} />
              <Campo label="Longitud" placeholder="Ej: -76.6147" value={form.longitud} onChange={(e) => set('longitud', e.target.value)} />
            </Fila>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Descripción</h2>
          <div className="cuerpo">
            <textarea style={{ width: '100%' }} value={form.descripcion} onChange={(e) => set('descripcion', e.target.value)} />
          </div>
        </div>

        {error && <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>}

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear centro de datos'}
          </button>
          <Link to="/inventario/centro-datos" className="btn btn-sec" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
            Cancelar
          </Link>
          {editando && puedeEliminar && (
            <button type="button" className="btn btn-sec" style={{ color: 'var(--crit)' }} disabled={eliminando} onClick={eliminar}>
              {eliminando ? 'Eliminando…' : 'Eliminar centro'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

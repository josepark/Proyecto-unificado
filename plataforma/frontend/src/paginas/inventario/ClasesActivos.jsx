import { useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, Fila } from '../../componentes/CamposFormulario';
import { useInventarioMeta } from '../../hooks/useInventarioMeta';

const OPC_MODELO = [
  ['ninguno', 'Solo campos comunes'],
  ['infraestructura', 'Infraestructura de red'],
  ['sistema', 'Sistema de información'],
  ['equipo', 'Equipo de cómputo'],
  ['generico', 'Campos libres (JSON)'],
];

function vacio() {
  return {
    codigo: '', nombre: '', prefijo_id: '', color: '#6b7280', orden: '10',
    activo: true, modelo_detalle: 'ninguno', detalle_schema_json: '{\n  "campos": []\n}',
  };
}

export default function ClasesActivos() {
  const { puedeEditar } = useOutletContext() ?? {};
  const { meta, recargar: recargarMeta } = useInventarioMeta();
  const { datos: clases, cargando, error, recargar } = useApi(
    () => inventarioApi.listarClasesActivo(),
    [],
  );
  const [form, setForm] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [msgError, setMsgError] = useState(null);

  const lista = clases?.results ?? clases ?? [];

  function editar(c) {
    setForm({
      id: c.id,
      codigo: c.codigo,
      nombre: c.nombre,
      prefijo_id: c.prefijo_id,
      color: c.color,
      orden: String(c.orden ?? 0),
      activo: c.activo,
      modelo_detalle: c.modelo_detalle,
      detalle_schema_json: JSON.stringify(c.detalle_schema || { campos: [] }, null, 2),
    });
    setMsgError(null);
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setMsgError(null);
    const body = {
      codigo: form.codigo.trim().toUpperCase(),
      nombre: form.nombre.trim(),
      prefijo_id: form.prefijo_id.trim().toUpperCase(),
      color: form.color,
      orden: Number(form.orden) || 0,
      activo: form.activo,
      modelo_detalle: form.modelo_detalle,
    };
    if (form.modelo_detalle === 'generico') {
      try {
        body.detalle_schema = JSON.parse(form.detalle_schema_json || '{}');
      } catch {
        setMsgError('El esquema JSON no es válido.');
        setGuardando(false);
        return;
      }
    } else {
      body.detalle_schema = {};
    }
    try {
      if (form.id) {
        await inventarioApi.editarClaseActivo(form.id, body);
      } else {
        await inventarioApi.crearClaseActivo(body);
      }
      setForm(null);
      recargar();
      recargarMeta();
    } catch (e) {
      setMsgError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar(c) {
    if (!window.confirm(`¿Eliminar la clase ${c.codigo}? Solo es posible si no hay activos.`)) return;
    try {
      await inventarioApi.eliminarClaseActivo(c.id);
      recargar();
      recargarMeta();
    } catch (e) {
      alert(formatearErrorApi(e));
    }
  }

  return (
    <div>
      <Link to="/inventario/dashboard" className="volver">← Volver al dashboard</Link>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px', flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Clases de activo</h2>
        {puedeEditar && !form && (
          <button type="button" className="btn btn-primary" onClick={() => { setForm(vacio()); setMsgError(null); }}>
            + Nueva clase
          </button>
        )}
      </div>

      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Configure aquí las clases del inventario (INFRA, SIST, EQUI u otras). El formulario de activos y las
        estadísticas se actualizan automáticamente. Las clases con detalle «genérico» usan JSON en el activo.
      </p>

      {form && puedeEditar && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>{form.id ? `Editar ${form.codigo}` : 'Nueva clase'}</h2>
          <form className="cuerpo" onSubmit={guardar}>
            <Fila columnas={3}>
              <Campo label="Código" value={form.codigo} required disabled={Boolean(form.id)}
                onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value.toUpperCase() }))} />
              <Campo label="Nombre" value={form.nombre} required
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} />
              <Campo label="Prefijo ID" value={form.prefijo_id} required placeholder="Ej: SRV"
                onChange={(e) => setForm((f) => ({ ...f, prefijo_id: e.target.value.toUpperCase() }))} />
            </Fila>
            <Fila columnas={3}>
              <Campo label="Color (#hex)" value={form.color}
                onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))} />
              <Campo label="Orden" type="number" value={form.orden}
                onChange={(e) => setForm((f) => ({ ...f, orden: e.target.value }))} />
              <CampoSelect label="Modelo de detalle" opciones={OPC_MODELO} value={form.modelo_detalle}
                onChange={(e) => setForm((f) => ({ ...f, modelo_detalle: e.target.value }))} />
            </Fila>
            <label style={{ fontSize: 13, display: 'block', marginBottom: 12 }}>
              <input type="checkbox" checked={form.activo}
                onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))} /> Clase activa (visible en formularios)
            </label>
            {form.modelo_detalle === 'generico' && (
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                  Esquema de campos (JSON)
                </label>
                <textarea
                  value={form.detalle_schema_json}
                  onChange={(e) => setForm((f) => ({ ...f, detalle_schema_json: e.target.value }))}
                  rows={8}
                  style={{ width: '100%', fontFamily: 'monospace', fontSize: 12 }}
                  placeholder={'{\n  "campos": [\n    {"nombre": "proveedor", "tipo": "texto", "requerido": true}\n  ]\n}'}
                />
                <p style={{ fontSize: 12, color: 'var(--texto-suave)', margin: '6px 0 0' }}>
                  Tipos: texto, entero, decimal, booleano, fecha, opciones (con lista «opciones»).
                </p>
              </div>
            )}
            {msgError && <p style={{ color: 'var(--crit)' }}>{msgError}</p>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={guardando}>
                {guardando ? 'Guardando…' : 'Guardar'}
              </button>
              <button type="button" className="btn btn-sec" onClick={() => setForm(null)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <div className="card"><div className="cuerpo">No se pudieron cargar las clases ({error.message}).</div></div>
      )}

      {cargando ? <p>Cargando…</p> : (
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Prefijo</th>
              <th>Detalle</th>
              <th className="num">Activos</th>
              <th>Estado</th>
              {puedeEditar ? <th /> : null}
            </tr>
          </thead>
          <tbody>
            {lista.map((c) => (
              <tr key={c.id}>
                <td>
                  <span className="clase-badge" style={{ background: c.color || meta?.colores_clase?.[c.codigo] }}>
                    {c.codigo}
                  </span>
                </td>
                <td>{c.nombre}</td>
                <td>{c.prefijo_id}</td>
                <td>{c.modelo_detalle_display || c.modelo_detalle}</td>
                <td className="num">{c.num_activos ?? 0}</td>
                <td>{c.activo ? 'Activa' : 'Inactiva'}</td>
                {puedeEditar ? (
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button type="button" className="btn-sec" onClick={() => editar(c)}>Editar</button>{' '}
                    <button type="button" className="btn-sec" style={{ color: 'var(--crit)' }}
                      disabled={(c.num_activos ?? 0) > 0} onClick={() => eliminar(c)}>Eliminar</button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

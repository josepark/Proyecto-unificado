import { useCallback, useEffect, useState } from 'react';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';

const TIPOS_EVENTO = [
  { value: 'ALTA', label: 'Alta / Puesta en marcha' },
  { value: 'MPRE', label: 'Mantenimiento preventivo' },
  { value: 'MCOR', label: 'Mantenimiento correctivo' },
  { value: 'ACTU', label: 'Actualización (firmware/software)' },
  { value: 'TRAS', label: 'Traslado / Reubicación' },
  { value: 'INCI', label: 'Incidente de seguridad' },
  { value: 'CONF', label: 'Cambio de configuración' },
  { value: 'GARA', label: 'Gestión de garantía / RMA' },
  { value: 'BAJA', label: 'Baja / Retiro' },
  { value: 'OTRO', label: 'Otro' },
];

const FORM_VACIO = {
  fecha: '',
  tipo_evento: 'MPRE',
  titulo: '',
  descripcion: '',
  responsable: '',
  costo: '',
  documento: null,
};

export default function HojaVidaActivo({ activoId, puedeEditar, puedeEliminar }) {
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(FORM_VACIO);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [errorForm, setErrorForm] = useState(null);

  const recargar = useCallback(() => {
    setCargando(true);
    setError(null);
    return inventarioApi
      .listarHojaVida(activoId)
      .then((r) => setEventos(r.results ?? r ?? []))
      .catch((e) => setError(e))
      .finally(() => setCargando(false));
  }, [activoId]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  function setCampo(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  async function enviar(evento) {
    evento.preventDefault();
    setErrorForm(null);
    setEnviando(true);
    try {
      if (form.documento) {
        const fd = new FormData();
        fd.append('activo', String(activoId));
        fd.append('fecha', form.fecha);
        fd.append('tipo_evento', form.tipo_evento);
        fd.append('titulo', form.titulo);
        if (form.descripcion) fd.append('descripcion', form.descripcion);
        if (form.responsable) fd.append('responsable', form.responsable);
        if (form.costo) fd.append('costo', form.costo);
        fd.append('documento', form.documento);
        await inventarioApi.crearEventoHojaVidaArchivo(fd);
      } else {
        await inventarioApi.crearEventoHojaVida({
          activo: Number(activoId),
          fecha: form.fecha,
          tipo_evento: form.tipo_evento,
          titulo: form.titulo,
          descripcion: form.descripcion,
          responsable: form.responsable,
          costo: form.costo || null,
        });
      }
      setForm(FORM_VACIO);
      setMostrarForm(false);
      await recargar();
    } catch (e) {
      setErrorForm(formatearErrorApi(e));
    } finally {
      setEnviando(false);
    }
  }

  async function eliminar(ev) {
    if (!window.confirm(`¿Eliminar el evento «${ev.titulo}» del ${ev.fecha}?`)) return;
    try {
      await inventarioApi.eliminarEventoHojaVida(ev.id);
      await recargar();
    } catch (e) {
      setError(formatearErrorApi(e));
    }
  }

  return (
    <div className="card">
      <h2>Hoja de vida (eventos operativos)</h2>
      <div className="cuerpo">
        {puedeEditar && (
          <div style={{ marginBottom: 12 }}>
            {!mostrarForm ? (
              <button type="button" className="btn btn-sec" onClick={() => setMostrarForm(true)}>
                + Registrar evento
              </button>
            ) : (
              <form onSubmit={enviar} style={{ display: 'grid', gap: 8, maxWidth: 520 }}>
                {errorForm ? <p style={{ color: 'var(--crit)', margin: 0 }}>{errorForm}</p> : null}
                <label>
                  Fecha
                  <input type="date" value={form.fecha} onChange={(e) => setCampo('fecha', e.target.value)} required />
                </label>
                <label>
                  Tipo
                  <select value={form.tipo_evento} onChange={(e) => setCampo('tipo_evento', e.target.value)}>
                    {TIPOS_EVENTO.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Título
                  <input value={form.titulo} onChange={(e) => setCampo('titulo', e.target.value)} required />
                </label>
                <label>
                  Descripción
                  <textarea rows={2} value={form.descripcion} onChange={(e) => setCampo('descripcion', e.target.value)} />
                </label>
                <label>
                  Responsable
                  <input value={form.responsable} onChange={(e) => setCampo('responsable', e.target.value)} />
                </label>
                <label>
                  Costo (COP, opcional)
                  <input type="number" step="0.01" value={form.costo} onChange={(e) => setCampo('costo', e.target.value)} />
                </label>
                <label>
                  Adjunto (acta, factura…)
                  <input type="file" onChange={(e) => setCampo('documento', e.target.files?.[0] || null)} />
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="submit" className="btn btn-primary" disabled={enviando}>
                    {enviando ? 'Guardando…' : 'Guardar evento'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-sec"
                    onClick={() => {
                      setMostrarForm(false);
                      setForm(FORM_VACIO);
                      setErrorForm(null);
                    }}
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {cargando ? (
          <p>Cargando eventos…</p>
        ) : error ? (
          <p style={{ color: 'var(--crit)' }}>No se pudo cargar la hoja de vida ({error.message}).</p>
        ) : !eventos.length ? (
          <p style={{ color: 'var(--texto-suave)', margin: 0 }}>Sin eventos registrados.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Título</th>
                <th>Responsable</th>
                <th>Adjunto</th>
                {puedeEliminar ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {eventos.map((ev) => (
                <tr key={ev.id}>
                  <td>{ev.fecha}</td>
                  <td>{ev.tipo_evento_display}</td>
                  <td>
                    <div>{ev.titulo}</div>
                    {ev.descripcion ? (
                      <div style={{ fontSize: 12, color: 'var(--texto-suave)' }}>{ev.descripcion}</div>
                    ) : null}
                  </td>
                  <td>{ev.responsable || '—'}</td>
                  <td>
                    {ev.documento_url ? (
                      <a href={ev.documento_url} target="_blank" rel="noreferrer">
                        Ver
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
                  {puedeEliminar ? (
                    <td>
                      <button type="button" className="btn btn-sec" style={{ color: 'var(--crit)' }} onClick={() => eliminar(ev)}>
                        Eliminar
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import HojaVidaActivo from './HojaVidaActivo';

const CLASE_COLOR = { INFRA: '#1f6b52', SIST: '#c9a94e', EQUI: '#28407a' };

/** Convierte una clave tecnica del modelo ("fin_soporte_eol") en una
 * etiqueta legible ("Fin soporte eol") sin necesitar un mapa exhaustivo
 * por cada campo de infraestructura/sistema/equipo — los tres bloques
 * comparten esta misma funcion de presentacion generica. */
function etiquetar(clave) {
  const texto = clave.replace(/_/g, ' ');
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function formatearValor(v) {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'Sí' : 'No';
  return String(v);
}

/** Bloque de detalle especifico de clase (infraestructura, sistema o
 * equipo) — el unico de los tres que llega no-nulo en cada activo,
 * segun ActivoDetailSerializer. Se renderiza de forma generica para no
 * duplicar aqui la lista de campos que ya vive en el modelo/serializer. */
function BloqueDetalleClase({ titulo, datos }) {
  if (!datos) return null;
  const entradas = Object.entries(datos).filter(
    ([clave, valor]) => !['id', 'activo', 'accesos', 'accesos_rbac'].includes(clave)
      && valor !== null && valor !== '',
  );
  if (!entradas.length) return null;
  return (
    <div className="card">
      <h2>{titulo}</h2>
      <div className="cuerpo">
        <dl className="def">
          {entradas.map(([clave, valor]) => (
            <div key={clave}>
              <dt>{etiquetar(clave)}</dt>
              <dd>{formatearValor(valor)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

/** Cruce local (RolMCA) vs matriz RBAC en vivo — misma lógica que la ficha
 * del tablero Django retirado (§8.6 README-DESPLIEGUE). */
function AccesosSistema({ sistema }) {
  if (!sistema) return null;

  const { accesos, accesos_rbac, sistema_mca_equivalente: mca } = sistema;

  return (
    <>
      {accesos?.length > 0 && (
        <div className="card">
          <h2>Roles con acceso — registrado en el Inventario</h2>
          <div className="cuerpo">
            <div className="chip-list">
              {accesos.map((a, i) => (
                <span className="chip" key={i} title={String(a.rol)}>
                  {a.rol} ({a.nivel})
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Roles con acceso — según Matriz RBAC (en vivo)</h2>
        <div className="cuerpo">
          {accesos_rbac === null ? (
            <p style={{ color: '#9a1f1f', fontSize: 13, margin: 0 }}>
              No se pudo verificar contra la Matriz RBAC (módulo no disponible, o «
              {mca || '—'}» no coincide con ningún sistema de la matriz).
            </p>
          ) : accesos_rbac.length === 0 ? (
            <p style={{ color: 'var(--texto-suave)', fontSize: 13, margin: 0 }}>
              Sin accesos registrados en la matriz para «{mca}».
            </p>
          ) : (
            <div className="chip-list">
              {accesos_rbac.map((a, i) => (
                <span className="chip" key={i} title={a.denominacion || a.rol}>
                  {a.rol} ({a.nivel})
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function Activo() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { puedeEditar, puedeEliminar } = useOutletContext() ?? {};
  const { datos: a, cargando, error } = useApi(() => inventarioApi.obtenerActivo(id), [id]);
  const { datos: historial, cargando: cargandoHistorial } = useApi(
    () => inventarioApi.historialActivo(id),
    [id],
  );
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState(null);

  async function manejarEliminar() {
    if (!window.confirm(`¿Eliminar el activo ${a.id_activo}? Quedará registrado en la bitácora.`)) return;
    setEliminando(true);
    setErrorEliminar(null);
    try {
      await inventarioApi.eliminarActivo(id);
      navegar('/inventario/dashboard');
    } catch (e) {
      setErrorEliminar(formatearErrorApi(e));
      setEliminando(false);
    }
  }

  if (cargando) return <p>Cargando activo…</p>;

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {error.status === 404 ? (
            <>No se encontró ese activo.</>
          ) : (
            <>No se pudo cargar el activo ({error.message}).</>
          )}{' '}
          <Link to="/inventario/dashboard">Volver al Dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link to="/inventario/dashboard" className="volver">
        ← Volver al Dashboard
      </Link>

      <div className="ficha-cabecera">
        <h2>{a.id_activo}</h2>
        <span className="clase-badge" style={{ background: CLASE_COLOR[a.clase] || '#888' }}>
          {a.clase_display}
        </span>
        <span className={`tag t-${a.nivel_riesgo}`}>{a.nivel_riesgo_display}</span>
      </div>
      <div className="ficha-sub">{a.nombre}</div>

      <div className="acciones-ficha">
        {puedeEditar && (
          <Link className="btn btn-primary" to={`/inventario/activos/${a.id}/editar`}>
            ✎ Editar
          </Link>
        )}
        {puedeEliminar && (
          <button className="btn btn-sec" onClick={manejarEliminar} disabled={eliminando} style={{ color: 'var(--crit)' }}>
            {eliminando ? 'Eliminando…' : '🗑 Eliminar'}
          </button>
        )}
        <a className="btn btn-sec" href={`/api/activos/${a.id}/hojavida.pdf`} target="_blank" rel="noreferrer">
          ⬇ Hoja de vida PDF
        </a>
        <a
          className="btn btn-sec"
          href={`/api/activos/${a.id}/etiqueta.pdf`}
          target="_blank"
          rel="noreferrer"
          title="Etiqueta adhesiva 70x40mm lista para imprimir y pegar"
        >
          🏷️ Etiqueta
        </a>
        <a className="btn btn-sec" href={`/api/activos/${a.id}/qr.png`} download={`QR-${a.id_activo}.png`}>
          ⬇ Descargar QR
        </a>
      </div>
      {errorEliminar && (
        <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginTop: -12, marginBottom: 16 }}>
          Error al eliminar: {errorEliminar}
        </p>
      )}

      <div className="detalle-grid">
        <div className="card">
          <h2>Valoración y riesgo</h2>
          <div className="cuerpo">
            <dl className="def">
              <dt>Confidencialidad · Integridad · Disponibilidad</dt>
              <dd>
                {a.confidencialidad} · {a.integridad} · {a.disponibilidad} (valor {a.valor})
              </dd>
              <dt>Clasificación SI</dt>
              <dd>{a.clasificacion_si_display}</dd>
              <dt>Nivel de riesgo</dt>
              <dd>{a.nivel_riesgo_display}</dd>
              <dt>Procesa datos personales (Ley 1581/2012)</dt>
              <dd>{formatearValor(a.procesa_datos_personales)}</dd>
            </dl>
          </div>
        </div>

        <div className="card">
          <h2>Gestión</h2>
          <div className="cuerpo">
            <dl className="def">
              <dt>Estado</dt>
              <dd>{a.estado_display}</dd>
              <dt>Ciclo de vida</dt>
              <dd>{a.ciclo_vida_display}</dd>
              <dt>Fecha de registro</dt>
              <dd>{formatearValor(a.fecha_registro)}</dd>
              <dt>Propietario</dt>
              <dd>{formatearValor(a.propietario)}</dd>
              <dt>Custodio</dt>
              <dd>{formatearValor(a.custodio)}</dd>
              <dt>Área responsable</dt>
              <dd>{formatearValor(a.area_responsable)}</dd>
            </dl>
          </div>
        </div>

        {(a.rto || a.rpo) && (
          <div className="card">
            <h2>Continuidad</h2>
            <div className="cuerpo">
              <dl className="def">
                <dt>RTO (tiempo objetivo de recuperación)</dt>
                <dd>{formatearValor(a.rto)}</dd>
                <dt>RPO (punto objetivo de recuperación)</dt>
                <dd>{formatearValor(a.rpo)}</dd>
              </dl>
            </div>
          </div>
        )}

        {a.datacenter_info && (
          <div className="card">
            <h2>Ubicación</h2>
            <div className="cuerpo">
              <dl className="def">
                <dt>Centro de datos</dt>
                <dd>
                  {a.datacenter_info.codigo} — {a.datacenter_info.nombre}
                </dd>
                <dt>Ciudad</dt>
                <dd>{a.datacenter_info.ciudad}</dd>
                <dt>Nivel Tier</dt>
                <dd>{a.datacenter_info.tier}</dd>
              </dl>
            </div>
          </div>
        )}

        <BloqueDetalleClase titulo="Detalle de infraestructura" datos={a.infraestructura} />
        <BloqueDetalleClase titulo="Detalle del sistema" datos={a.sistema} />
        <AccesosSistema sistema={a.sistema} />
        <BloqueDetalleClase titulo="Detalle del equipo" datos={a.equipo} />

        {a.amenazas?.length > 0 && (
          <div className="card">
            <h2>Amenazas MITRE ATT&amp;CK asociadas</h2>
            <div className="cuerpo">
              <div className="chip-list">
                {a.amenazas.map((m) => (
                  <a
                    key={m.id}
                    className="chip enlace"
                    href={m.url || `https://attack.mitre.org/`}
                    target="_blank"
                    rel="noreferrer"
                    title={m.nombre}
                  >
                    {m.codigo}
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}

        {a.controles?.length > 0 && (
          <div className="card">
            <h2>Controles ISO / políticas asociados</h2>
            <div className="cuerpo">
              <div className="chip-list">
                {a.controles.map((ctl) => (
                  <span className="chip" key={ctl.id} title={ctl.descripcion}>
                    {ctl.codigo}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {a.dependencias?.length > 0 && (
          <div className="card">
            <h2>Depende de</h2>
            <div className="cuerpo">
              <div className="chip-list">
                {a.dependencias.map((d) => (
                  <Link key={d.id} className="chip enlace" to={`/inventario/activos/${d.id}`}>
                    {d.id_activo}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}

        {(a.notas_seguridad || a.descripcion || a.documentos_relacionados) && (
          <div className="card">
            <h2>Notas y documentación</h2>
            <div className="cuerpo">
              <dl className="def">
                {a.descripcion && (
                  <>
                    <dt>Descripción</dt>
                    <dd>{a.descripcion}</dd>
                  </>
                )}
                {a.notas_seguridad && (
                  <>
                    <dt>Notas de seguridad</dt>
                    <dd>{a.notas_seguridad}</dd>
                  </>
                )}
                {a.documentos_relacionados && (
                  <>
                    <dt>Documentos relacionados</dt>
                    <dd>{a.documentos_relacionados}</dd>
                  </>
                )}
              </dl>
            </div>
          </div>
        )}
      </div>

      <HojaVidaActivo activoId={id} puedeEditar={puedeEditar} puedeEliminar={puedeEliminar} />

      <div className="card">
        <h2>Historial de cambios (bitácora ISO 8.15)</h2>
        <div className="cuerpo">
          {cargandoHistorial ? (
            <p>Cargando historial…</p>
          ) : !historial?.length ? (
            <p>Sin registros de bitácora.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Usuario</th>
                  <th>Cambios</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((h, i) => (
                  <tr key={i}>
                    <td>{new Date(h.fecha).toLocaleString('es-CO')}</td>
                    <td>{h.tipo}</td>
                    <td>{h.usuario}</td>
                    <td>
                      {h.cambios?.length
                        ? h.cambios
                            .map((c) => `${c.campo}: ${c.antes ?? '∅'} → ${c.despues ?? '∅'}`)
                            .join('; ')
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

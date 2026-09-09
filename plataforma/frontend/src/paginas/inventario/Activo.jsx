import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import HojaVidaActivo from './HojaVidaActivo';
import { useInventarioMeta } from '../../hooks/useInventarioMeta';
import { claseTagRiesgoMatriz, etiquetaCobertura } from '../../lib/integracionUi';

const CAMPOS_DETALLE_OCULTOS = new Set([
  'id', 'activo', 'accesos', 'accesos_rbac', 'sistema_rbac_nombre',
  'zona_id', 'vlan_id', 'rack_fk', 'rack_codigo', 'rack_datacenter',
  'unidad_inicio', 'unidad_fin',
]);

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
    ([clave, valor]) => !CAMPOS_DETALLE_OCULTOS.has(clave)
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

/** Accesos canónicos desde la Matriz RBAC (RolMCA/AccesoRol local deprecados). */
function AccesosSistema({ sistema }) {
  if (!sistema) return null;

  const { accesos_rbac, sistema_rbac_nombre, sistema_mca_equivalente: mca } = sistema;
  const etiqueta = sistema_rbac_nombre || mca || '—';

  return (
    <div className="card">
      <h2>Roles con acceso — Matriz RBAC</h2>
      <div className="cuerpo">
        {accesos_rbac === null ? (
          <p style={{ color: '#9a1f1f', fontSize: 13, margin: 0 }}>
            No se pudo verificar contra la Matriz RBAC (módulo no disponible, o «
            {etiqueta}» no está vinculado al catálogo RBAC).
          </p>
        ) : accesos_rbac.length === 0 ? (
          <p style={{ color: 'var(--texto-suave)', fontSize: 13, margin: 0 }}>
            Sin accesos registrados en la matriz para «{etiqueta}».
          </p>
        ) : (
          <>
            <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginTop: 0 }}>
              Sistema vinculado: <b>{etiqueta}</b>
            </p>
            <div className="chip-list">
              {accesos_rbac.map((a, i) => (
                <span className="chip" key={i} title={a.denominacion || a.rol}>
                  {a.rol} ({a.nivel})
                </span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function TarjetaIntegracionRiesgos({ resumen }) {
  if (!resumen) return null;

  if (!resumen.vinculado) {
    return (
      <div className="card">
        <h2>Gestión de Riesgos</h2>
        <div className="cuerpo">
          <p style={{ margin: 0, fontSize: 13, color: 'var(--texto-suave)' }}>
            {resumen.mensaje}
          </p>
        </div>
      </div>
    );
  }

  const url = resumen.url_gestion || `/gestion-riesgos/activos/${resumen.id}`;
  return (
    <div className="card">
      <h2>Gestión de Riesgos</h2>
      <div className="cuerpo">
        <dl className="def">
          <dt>Vulnerabilidades (OpenVAS / Nmap)</dt>
          <dd>
            {resumen.total_vulnerabilidades ?? 0}
            {resumen.vulnerabilidades_criticas > 0 && (
              <span style={{ color: 'var(--crit)', marginLeft: 6 }}>
                ({resumen.vulnerabilidades_criticas} críticas)
              </span>
            )}
          </dd>
          <dt>Cobertura técnica</dt>
          <dd>{etiquetaCobertura(resumen.cobertura_display || resumen.cobertura)}</dd>
          <dt>Riesgo matriz</dt>
          <dd>
            {resumen.riesgo_matriz ? (
              <span className={claseTagRiesgoMatriz(resumen.riesgo_matriz)}>{resumen.riesgo_matriz}</span>
            ) : '—'}
          </dd>
          <dt>Red Team</dt>
          <dd style={{ color: resumen.afectado_red_team ? 'var(--crit)' : undefined }}>
            {resumen.afectado_red_team ? 'Comprometido en campaña' : 'Sin evidencia de compromiso'}
          </dd>
        </dl>
        <Link to={url} className="btn btn-sec" style={{ marginTop: 10, display: 'inline-block' }}>
          Ver ficha en Gestión de Riesgos →
        </Link>
      </div>
    </div>
  );
}

export default function Activo() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { puedeEditar, puedeEliminar } = useOutletContext() ?? {};
  const { coloresClase } = useInventarioMeta();
  const { datos: a, cargando, error } = useApi(() => inventarioApi.obtenerActivo(id), [id]);
  const { datos: historial, cargando: cargandoHistorial } = useApi(
    () => inventarioApi.historialActivo(id),
    [id],
  );
  const { datos: resumenRiesgos } = useApi(() => inventarioApi.resumenRiesgosActivo(id), [id]);
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
        <span className="clase-badge" style={{ background: coloresClase[a.clase] || '#888' }}>
          {a.clase_display}
        </span>
        <span className={`tag t-${a.nivel_riesgo}`}>{a.nivel_riesgo_display}</span>
        {resumenRiesgos?.vinculado && (
          <Link
            to={resumenRiesgos.url_gestion || `/gestion-riesgos/activos/${resumenRiesgos.id}`}
            className="chip enlace"
            style={{ marginLeft: 8 }}
            title="Ver vulnerabilidades, cobertura y PTR en Gestión de Riesgos"
          >
            {resumenRiesgos.total_vulnerabilidades ?? 0} vulns
            {resumenRiesgos.vulnerabilidades_criticas > 0
              ? ` · ${resumenRiesgos.vulnerabilidades_criticas} crít.`
              : ''}
            {resumenRiesgos.riesgo_matriz ? (
              <>
                {' · '}
                <span className={claseTagRiesgoMatriz(resumenRiesgos.riesgo_matriz)} style={{ padding: '1px 6px' }}>
                  {resumenRiesgos.riesgo_matriz}
                </span>
              </>
            ) : null}
          </Link>
        )}
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
        {resumenRiesgos?.vinculado && (
          <Link
            className="btn btn-sec"
            to={resumenRiesgos.url_gestion || `/gestion-riesgos/activos/${resumenRiesgos.id}`}
          >
            ↗ Gestión de Riesgos
          </Link>
        )}
      </div>
      {errorEliminar && (
        <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginTop: -12, marginBottom: 16 }}>
          Error al eliminar: {errorEliminar}
        </p>
      )}

      <div className="detalle-grid">
        <TarjetaIntegracionRiesgos resumen={resumenRiesgos} />

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
        <BloqueDetalleClase titulo="Detalle adicional" datos={a.detalle_extra} />

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

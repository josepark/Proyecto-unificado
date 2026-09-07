import { useEffect, useState } from 'react';
import { useNavigate, useParams, useOutletContext, Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';
import { formatearErrorApi } from '../../api/client';
import { Campo, CampoSelect, CampoTextarea, Fila } from '../../componentes/CamposFormulario';

// Listas de opciones alineadas con ActivoWriteSerializer (DRF) — mismos
// valores válidos que el formulario individual del Inventario.
const OPC = {
  clase: [
    ['INFRA', 'Infraestructura de red'],
    ['SIST', 'Sistema de información'],
    ['EQUI', 'Equipo de cómputo'],
  ],
  clasificacion_si: [
    ['', '—'],
    ['ALTA', 'Altamente Confidencial'],
    ['CONF', 'Confidencial'],
    ['INT', 'Uso Interno'],
    ['PUB', 'Público'],
  ],
  nivel: [
    ['', ''],
    ['0', '0 - N/A'],
    ['1', '1 - Bajo'],
    ['2', '2 - Medio'],
    ['3', '3 - Alto'],
    ['4', '4 - Crítico'],
  ],
  nivel_riesgo: [
    ['SIN', 'Sin valorar'],
    ['BAJO', 'Bajo'],
    ['MED', 'Medio'],
    ['ALTO', 'Alto'],
    ['CRIT', 'Crítico'],
  ],
  estado: [
    ['ACT', 'Activo'],
    ['IMP', 'En implementación'],
    ['INA', 'Inactivo'],
    ['RET', 'Retirado'],
  ],
  ciclo_vida: [
    ['PROD', 'En producción'],
    ['PLAN', 'Planeado'],
    ['MANT', 'En mantenimiento'],
    ['RETI', 'Retirado / Baja'],
  ],
  estado_operativo: [
    ['SD', 'Sin dato'],
    ['OP', 'En operación'],
    ['IMP', 'En implementación'],
    ['NO', 'No operación'],
  ],
  prioridad: [
    ['SIN', 'Sin priorizar'],
    ['ALTA', 'Alta - Inmediata'],
    ['MED', 'Media - Próxima fase'],
    ['BAJA', 'Baja - Pendiente'],
  ],
  tipo_equipo: [
    ['ESC', 'Equipo de escritorio'],
    ['PORT', 'Portátil / Laptop'],
    ['AIO', 'Todo en uno (All-in-one)'],
    ['TAB', 'Tablet'],
    ['OTRO', 'Otro'],
  ],
};

function vacio() {
  return {
    id_activo: '', nombre: '', descripcion: '', clase: 'INFRA',
    clasificacion_si: '', nivel_riesgo: 'SIN',
    confidencialidad: '', integridad: '', disponibilidad: '',
    estado: 'ACT', ciclo_vida: 'PROD', datacenter: '',
    propietario: '', custodio: '', area_responsable: '',
    procesa_datos_personales: false, rto: '', rpo: '',
    documentos_relacionados: '', notas_seguridad: '',
    amenazas: '', controles: '',
    infra: { tipo: '', ip_segmento: '', modelo: '', serial_placa: '',
      fabricante_proveedor: '', version_so_firmware: '',
      fin_soporte_eol: '', hallazgos_abiertos: '', rack: '', unidad_rack: '' },
    sist: { estado_operativo: 'SD', priorizar_analisis: 'SIN', backend: '',
      frontend: '', schema_bd: '', servidor_virtual: '',
      sistema_mca_equivalente: '', version: '', integracion_gateway: '', url: '' },
    equipo: { tipo_equipo: 'ESC', usuario_asignado: '', marca: '', modelo: '',
      serial: '', mac_address: '', ubicacion_fisica: '', sistema_operativo: '',
      ram_gb: '', almacenamiento: '', antivirus_edr: '', ultima_actualizacion_so: '',
      cifrado_disco: false, unido_a_dominio: false, fecha_adquisicion: '', fin_garantia: '' },
  };
}

/** Recompone el estado del formulario a partir de /api/activos/{id}/
 * (ActivoDetailSerializer) — solo toma lo que el formulario edita. */
function desdeActivo(a) {
  const base = vacio();
  return {
    ...base,
    id_activo: a.id_activo || '', nombre: a.nombre || '', descripcion: a.descripcion || '',
    clase: a.clase || 'INFRA', clasificacion_si: a.clasificacion_si || '',
    nivel_riesgo: a.nivel_riesgo || 'SIN',
    confidencialidad: a.confidencialidad ?? '', integridad: a.integridad ?? '',
    disponibilidad: a.disponibilidad ?? '', estado: a.estado || 'ACT',
    ciclo_vida: a.ciclo_vida || 'PROD', datacenter: a.datacenter ?? '',
    propietario: a.propietario || '', custodio: a.custodio || '',
    area_responsable: a.area_responsable || '',
    procesa_datos_personales: !!a.procesa_datos_personales,
    rto: a.rto || '', rpo: a.rpo || '',
    documentos_relacionados: a.documentos_relacionados || '',
    notas_seguridad: a.notas_seguridad || '',
    amenazas: (a.amenazas || []).map((m) => m.codigo).join(', '),
    controles: (a.controles || []).map((c) => c.codigo).join(', '),
    infra: a.infraestructura ? { ...base.infra, ...a.infraestructura } : base.infra,
    sist: a.sistema ? { ...base.sist, ...a.sistema } : base.sist,
    equipo: a.equipo ? { ...base.equipo, ...a.equipo } : base.equipo,
  };
}

function numOrNull(v) {
  return v === '' || v === null || v === undefined ? null : Number(v);
}

export default function ActivoForm() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navegar = useNavigate();
  const { puedeEditar } = useOutletContext() ?? {};

  const { datos: activoExistente, cargando: cargandoActivo, error: errorCarga } = useApi(
    () => (editando ? inventarioApi.obtenerActivo(id) : Promise.resolve(null)),
    [id],
  );
  const { datos: datacenters } = useApi(() => inventarioApi.datacenters(), []);

  const [form, setForm] = useState(editando ? null : vacio());
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (editando && activoExistente) setForm(desdeActivo(activoExistente));
  }, [editando, activoExistente]);

  const set = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));
  const setSub = (bloque, campo, valor) =>
    setForm((f) => ({ ...f, [bloque]: { ...f[bloque], [campo]: valor } }));

  if (editando && (cargandoActivo || !form)) return <p>Cargando activo…</p>;
  if (editando && errorCarga) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar el activo a editar. <Link to="/inventario/dashboard">Volver</Link>
        </div>
      </div>
    );
  }
  // El servidor es quien realmente lo impide (ActivoWriteSerializer exige
  // sesión de rol Dinamizador/Administrador) — este aviso solo evita que
  // alguien sin ese rol llene un formulario entero para que se lo rechacen
  // recién al guardar (mismo criterio que ya usa Shell.jsx para RBAC).
  if (puedeEditar === false) {
    return (
      <div className="card">
        <div className="cuerpo">
          No tenés permiso para {editando ? 'editar' : 'crear'} activos con tu rol actual.{' '}
          <Link to={editando ? `/inventario/activos/${id}` : '/inventario/dashboard'}>Volver</Link>
        </div>
      </div>
    );
  }

  async function guardar(ev) {
    ev.preventDefault();
    setGuardando(true);
    setError(null);
    const body = {
      nombre: form.nombre, descripcion: form.descripcion, clase: form.clase,
      clasificacion_si: form.clasificacion_si, nivel_riesgo: form.nivel_riesgo,
      confidencialidad: numOrNull(form.confidencialidad),
      integridad: numOrNull(form.integridad),
      disponibilidad: numOrNull(form.disponibilidad),
      estado: form.estado, ciclo_vida: form.ciclo_vida,
      datacenter: form.datacenter ? Number(form.datacenter) : null,
      propietario: form.propietario, custodio: form.custodio,
      area_responsable: form.area_responsable,
      procesa_datos_personales: form.procesa_datos_personales,
      rto: form.rto, rpo: form.rpo,
      documentos_relacionados: form.documentos_relacionados,
      notas_seguridad: form.notas_seguridad,
      amenazas_codigos: form.amenazas.split(',').map((s) => s.trim()).filter(Boolean),
      controles_codigos: form.controles.split(',').map((s) => s.trim()).filter(Boolean),
    };
    if (form.id_activo.trim()) body.id_activo = form.id_activo.trim();

    if (form.clase === 'INFRA') {
      body.infraestructura = {
        ...form.infra,
        fin_soporte_eol: form.infra.fin_soporte_eol || null,
        hallazgos_abiertos: numOrNull(form.infra.hallazgos_abiertos),
      };
    } else if (form.clase === 'SIST') {
      body.sistema = { ...form.sist };
    } else if (form.clase === 'EQUI') {
      body.equipo = {
        ...form.equipo,
        ram_gb: numOrNull(form.equipo.ram_gb),
        fecha_adquisicion: form.equipo.fecha_adquisicion || null,
        fin_garantia: form.equipo.fin_garantia || null,
        ultima_actualizacion_so: form.equipo.ultima_actualizacion_so || null,
      };
    }

    try {
      const resultado = editando
        ? await inventarioApi.editarActivo(id, body)
        : await inventarioApi.crearActivo(body);
      navegar(`/inventario/activos/${resultado.id}`);
    } catch (e) {
      setError(formatearErrorApi(e));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <Link to={editando ? `/inventario/activos/${id}` : '/inventario/dashboard'} className="volver">
        ← Cancelar
      </Link>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>
        {editando ? `Editar ${form.id_activo}` : 'Nuevo activo'}
      </h2>

      <form onSubmit={guardar}>
        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Identificación</h2>
          <div className="cuerpo">
            <Fila>
              <Campo
                label={`ID Activo ${editando ? '' : '(automático si se deja vacío)'}`}
                value={form.id_activo}
                readOnly={editando}
                onChange={(e) => set('id_activo', e.target.value)}
              />
              <CampoSelect
                label="Clase *"
                opciones={OPC.clase}
                value={form.clase}
                onChange={(e) => set('clase', e.target.value)}
              />
            </Fila>
            <div style={{ marginBottom: 12 }}>
              <Campo label="Nombre *" value={form.nombre} required onChange={(e) => set('nombre', e.target.value)} />
            </div>
            <CampoTextarea
              label="Descripción"
              value={form.descripcion}
              onChange={(e) => set('descripcion', e.target.value)}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Valoración C-I-D</h2>
          <div className="cuerpo">
            <Fila>
              <CampoSelect
                label="Clasificación SI"
                opciones={OPC.clasificacion_si}
                value={form.clasificacion_si}
                onChange={(e) => set('clasificacion_si', e.target.value)}
              />
              <CampoSelect
                label="Nivel de riesgo"
                opciones={OPC.nivel_riesgo}
                value={form.nivel_riesgo}
                onChange={(e) => set('nivel_riesgo', e.target.value)}
              />
            </Fila>
            <Fila>
              <CampoSelect
                label="Confidencialidad"
                opciones={OPC.nivel}
                value={String(form.confidencialidad)}
                onChange={(e) => set('confidencialidad', e.target.value)}
              />
              <CampoSelect
                label="Integridad"
                opciones={OPC.nivel}
                value={String(form.integridad)}
                onChange={(e) => set('integridad', e.target.value)}
              />
            </Fila>
            <div style={{ maxWidth: 'calc(50% - 6px)' }}>
              <CampoSelect
                label="Disponibilidad"
                opciones={OPC.nivel}
                value={String(form.disponibilidad)}
                onChange={(e) => set('disponibilidad', e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Ubicación</h2>
          <div className="cuerpo">
            <CampoSelect
              label="Centro de datos"
              value={String(form.datacenter ?? '')}
              onChange={(e) => set('datacenter', e.target.value)}
              opciones={[
                ['', '— Sin centro de datos —'],
                ...(datacenters?.results ?? datacenters ?? []).map((d) => [String(d.id), `${d.codigo} — ${d.nombre}`]),
              ]}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Gobernanza (ISO 5.9)</h2>
          <div className="cuerpo">
            <Fila>
              <Campo label="Propietario" value={form.propietario} onChange={(e) => set('propietario', e.target.value)} />
              <Campo label="Custodio" value={form.custodio} onChange={(e) => set('custodio', e.target.value)} />
            </Fila>
            <Campo
              label="Área responsable"
              value={form.area_responsable}
              onChange={(e) => set('area_responsable', e.target.value)}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Datos personales / Continuidad / Ciclo de vida</h2>
          <div className="cuerpo">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <input
                type="checkbox"
                style={{ width: 'auto' }}
                checked={form.procesa_datos_personales}
                onChange={(e) => set('procesa_datos_personales', e.target.checked)}
              />
              Procesa datos personales (Ley 1581/2012)
            </label>
            <Fila>
              <Campo label="RTO" placeholder="Ej: 4 horas" value={form.rto} onChange={(e) => set('rto', e.target.value)} />
              <Campo label="RPO" placeholder="Ej: 1 hora" value={form.rpo} onChange={(e) => set('rpo', e.target.value)} />
            </Fila>
            <Fila>
              <CampoSelect
                label="Ciclo de vida"
                opciones={OPC.ciclo_vida}
                value={form.ciclo_vida}
                onChange={(e) => set('ciclo_vida', e.target.value)}
              />
              <CampoSelect
                label="Estado"
                opciones={OPC.estado}
                value={form.estado}
                onChange={(e) => set('estado', e.target.value)}
              />
            </Fila>
          </div>
        </div>

        {form.clase === 'INFRA' && (
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Detalle de infraestructura de red</h2>
            <div className="cuerpo">
              <Fila>
                <Campo label="Tipo" value={form.infra.tipo} onChange={(e) => setSub('infra', 'tipo', e.target.value)} />
                <Campo
                  label="IP / Segmento"
                  value={form.infra.ip_segmento}
                  onChange={(e) => setSub('infra', 'ip_segmento', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo label="Modelo" value={form.infra.modelo} onChange={(e) => setSub('infra', 'modelo', e.target.value)} />
                <Campo
                  label="Serial / Placa"
                  value={form.infra.serial_placa}
                  onChange={(e) => setSub('infra', 'serial_placa', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo label="Rack" value={form.infra.rack} onChange={(e) => setSub('infra', 'rack', e.target.value)} />
                <Campo
                  label="Unidad de rack (U)"
                  value={form.infra.unidad_rack}
                  onChange={(e) => setSub('infra', 'unidad_rack', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Fabricante / Proveedor"
                  value={form.infra.fabricante_proveedor}
                  onChange={(e) => setSub('infra', 'fabricante_proveedor', e.target.value)}
                />
                <Campo
                  label="Versión SO / Firmware"
                  value={form.infra.version_so_firmware}
                  onChange={(e) => setSub('infra', 'version_so_firmware', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Fin soporte (EOL)"
                  type="date"
                  value={form.infra.fin_soporte_eol || ''}
                  onChange={(e) => setSub('infra', 'fin_soporte_eol', e.target.value)}
                />
                <Campo
                  label="Hallazgos abiertos"
                  type="number"
                  value={form.infra.hallazgos_abiertos ?? ''}
                  onChange={(e) => setSub('infra', 'hallazgos_abiertos', e.target.value)}
                />
              </Fila>
            </div>
          </div>
        )}

        {form.clase === 'SIST' && (
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Detalle de sistema de información</h2>
            <div className="cuerpo">
              <Fila>
                <CampoSelect
                  label="Estado operativo"
                  opciones={OPC.estado_operativo}
                  value={form.sist.estado_operativo}
                  onChange={(e) => setSub('sist', 'estado_operativo', e.target.value)}
                />
                <CampoSelect
                  label="Prioridad de análisis"
                  opciones={OPC.prioridad}
                  value={form.sist.priorizar_analisis}
                  onChange={(e) => setSub('sist', 'priorizar_analisis', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Backend (framework)"
                  placeholder="Ej: Django REST Framework"
                  value={form.sist.backend}
                  onChange={(e) => setSub('sist', 'backend', e.target.value)}
                />
                <Campo
                  label="Frontend"
                  placeholder="Ej: React"
                  value={form.sist.frontend}
                  onChange={(e) => setSub('sist', 'frontend', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Schema BD"
                  value={form.sist.schema_bd}
                  onChange={(e) => setSub('sist', 'schema_bd', e.target.value)}
                />
                <Campo
                  label="Servidor virtual"
                  value={form.sist.servidor_virtual}
                  onChange={(e) => setSub('sist', 'servidor_virtual', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Sistema MCA equivalente"
                  value={form.sist.sistema_mca_equivalente}
                  onChange={(e) => setSub('sist', 'sistema_mca_equivalente', e.target.value)}
                />
                <Campo
                  label="Versión del sistema"
                  value={form.sist.version}
                  onChange={(e) => setSub('sist', 'version', e.target.value)}
                />
              </Fila>
              <div style={{ marginBottom: 12 }}>
                <Campo
                  label="Integración con Gateway"
                  placeholder="Ej: REST nativo → Gateway directo"
                  value={form.sist.integracion_gateway}
                  onChange={(e) => setSub('sist', 'integracion_gateway', e.target.value)}
                />
              </div>
              <Campo
                label="URL"
                placeholder="https://…"
                value={form.sist.url}
                onChange={(e) => setSub('sist', 'url', e.target.value)}
              />
            </div>
          </div>
        )}

        {form.clase === 'EQUI' && (
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Detalle de equipo de cómputo</h2>
            <div className="cuerpo">
              <Fila>
                <CampoSelect
                  label="Tipo de equipo"
                  opciones={OPC.tipo_equipo}
                  value={form.equipo.tipo_equipo}
                  onChange={(e) => setSub('equipo', 'tipo_equipo', e.target.value)}
                />
                <Campo
                  label="Usuario asignado"
                  value={form.equipo.usuario_asignado}
                  onChange={(e) => setSub('equipo', 'usuario_asignado', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo label="Marca" value={form.equipo.marca} onChange={(e) => setSub('equipo', 'marca', e.target.value)} />
                <Campo label="Modelo" value={form.equipo.modelo} onChange={(e) => setSub('equipo', 'modelo', e.target.value)} />
              </Fila>
              <Fila>
                <Campo label="Número de serie" value={form.equipo.serial} onChange={(e) => setSub('equipo', 'serial', e.target.value)} />
                <Campo
                  label="Dirección MAC"
                  placeholder="AA:BB:CC:DD:EE:FF"
                  value={form.equipo.mac_address}
                  onChange={(e) => setSub('equipo', 'mac_address', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Ubicación física / sede"
                  value={form.equipo.ubicacion_fisica}
                  onChange={(e) => setSub('equipo', 'ubicacion_fisica', e.target.value)}
                />
                <Campo
                  label="Sistema operativo"
                  placeholder="Ej: Windows 11 Pro"
                  value={form.equipo.sistema_operativo}
                  onChange={(e) => setSub('equipo', 'sistema_operativo', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="RAM (GB)"
                  type="number"
                  value={form.equipo.ram_gb ?? ''}
                  onChange={(e) => setSub('equipo', 'ram_gb', e.target.value)}
                />
                <Campo
                  label="Almacenamiento"
                  placeholder="Ej: 512GB SSD"
                  value={form.equipo.almacenamiento}
                  onChange={(e) => setSub('equipo', 'almacenamiento', e.target.value)}
                />
              </Fila>
              <Fila>
                <Campo
                  label="Antivirus / EDR instalado"
                  value={form.equipo.antivirus_edr}
                  onChange={(e) => setSub('equipo', 'antivirus_edr', e.target.value)}
                />
                <Campo
                  label="Última actualización del SO"
                  type="date"
                  value={form.equipo.ultima_actualizacion_so || ''}
                  onChange={(e) => setSub('equipo', 'ultima_actualizacion_so', e.target.value)}
                />
              </Fila>
              <Fila>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input
                    type="checkbox"
                    style={{ width: 'auto' }}
                    checked={form.equipo.cifrado_disco}
                    onChange={(e) => setSub('equipo', 'cifrado_disco', e.target.checked)}
                  />
                  Disco cifrado (BitLocker/LUKS)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input
                    type="checkbox"
                    style={{ width: 'auto' }}
                    checked={form.equipo.unido_a_dominio}
                    onChange={(e) => setSub('equipo', 'unido_a_dominio', e.target.checked)}
                  />
                  Unido al dominio / SSO corporativo
                </label>
              </Fila>
              <Fila>
                <Campo
                  label="Fecha de adquisición"
                  type="date"
                  value={form.equipo.fecha_adquisicion || ''}
                  onChange={(e) => setSub('equipo', 'fecha_adquisicion', e.target.value)}
                />
                <Campo
                  label="Fin de garantía"
                  type="date"
                  value={form.equipo.fin_garantia || ''}
                  onChange={(e) => setSub('equipo', 'fin_garantia', e.target.value)}
                />
              </Fila>
            </div>
          </div>
        )}

        <div className="card" style={{ marginBottom: 14 }}>
          <h2>Amenazas, controles y trazabilidad</h2>
          <div className="cuerpo">
            <div style={{ marginBottom: 12 }}>
              <Campo
                label="Amenazas MITRE (códigos separados por coma)"
                placeholder="T1486, T1190"
                value={form.amenazas}
                onChange={(e) => set('amenazas', e.target.value)}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <Campo
                label="Controles ISO / Políticas (códigos separados por coma)"
                placeholder="8.13, POL-SI-009"
                value={form.controles}
                onChange={(e) => set('controles', e.target.value)}
              />
            </div>
            <CampoTextarea
              label="Documentos SGSI relacionados"
              style={{ marginBottom: 12 }}
              value={form.documentos_relacionados}
              onChange={(e) => set('documentos_relacionados', e.target.value)}
            />
            <CampoTextarea
              label="Notas de seguridad"
              value={form.notas_seguridad}
              onChange={(e) => set('notas_seguridad', e.target.value)}
            />
          </div>
        </div>

        {error && (
          <p style={{ color: 'var(--crit)', fontWeight: 'bold', marginBottom: 12 }}>Error: {error}</p>
        )}

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear activo'}
          </button>
          <Link
            to={editando ? `/inventario/activos/${id}` : '/inventario/dashboard'}
            className="btn btn-sec"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}

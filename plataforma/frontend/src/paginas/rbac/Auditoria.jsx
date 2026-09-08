import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';
import { mensajeErrorRbac } from './rbacUtil';

export default function Auditoria() {
  const [busqueda, setBusqueda] = useState('');
  const [entidad, setEntidad] = useState('');
  const [accion, setAccion] = useState('');
  const [pagina, setPagina] = useState(1);
  const { datos: catalogos } = useApi(() => rbacApi.catalogos(), []);
  const { datos, cargando, error } = useApi(
    () => rbacApi.auditoria({
      ...(busqueda ? { q: busqueda } : {}),
      ...(entidad ? { entidad } : {}),
      ...(accion ? { accion } : {}),
      pagina,
    }),
    [busqueda, entidad, accion, pagina],
  );
  const [verificando, setVerificando] = useState(false);
  const [resultadoVerif, setResultadoVerif] = useState(null);

  function actualizarFiltro(setter) {
    return (valor) => {
      setter(valor);
      setPagina(1);
    };
  }

  async function verificar() {
    setVerificando(true);
    setResultadoVerif(null);
    try {
      const r = await rbacApi.verificarCadena();
      setResultadoVerif(r);
    } catch (e) {
      setResultadoVerif({ integra: false, error: e.message });
    } finally {
      setVerificando(false);
    }
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          {mensajeErrorRbac('auditoría', error)}
        </div>
      </div>
    );
  }

  const registros = datos?.registros ?? [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 16px', flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0, color: 'var(--verde-profundo)' }}>Bitácora de auditoría</h2>
        <button className="btn btn-sec" onClick={verificar} disabled={verificando}>
          {verificando ? 'Verificando…' : 'Verificar integridad de la cadena'}
        </button>
      </div>

      <p style={{ fontSize: 13, color: 'var(--texto-suave)', marginTop: 0 }}>
        Registro encadenado por hash SHA-256: cada entrada sella la anterior, de modo que cualquier alteración externa
        rompe la cadena (ISO/IEC 27002:2022 — 8.15). {datos?.total ?? 0} movimiento(s) en total.
      </p>

      {resultadoVerif && (
        <p style={{ fontWeight: 'bold', marginBottom: 12, color: resultadoVerif.integra ? 'var(--bajo)' : 'var(--crit)' }}>
          {resultadoVerif.integra
            ? `Cadena íntegra: ${resultadoVerif.detalle} registro(s) verificados sin alteraciones.`
            : `Cadena rota: se detectó una alteración en el registro #${resultadoVerif.detalle ?? '?'}${resultadoVerif.error ? ` (${resultadoVerif.error})` : ''}.`}
        </p>
      )}

      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          placeholder="Buscar por nombre, detalle o responsable…"
          value={busqueda}
          onChange={(e) => actualizarFiltro(setBusqueda)(e.target.value)}
          style={{ flex: 1, minWidth: 220 }}
        />
        <select value={entidad} onChange={(e) => actualizarFiltro(setEntidad)(e.target.value)}>
          <option value="">Todas las entidades</option>
          {(catalogos?.entidades_auditoria ?? []).map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
        <select value={accion} onChange={(e) => actualizarFiltro(setAccion)(e.target.value)}>
          <option value="">Todas las acciones</option>
          {(catalogos?.acciones_auditoria ?? []).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      {cargando ? (
        <p>Cargando bitácora…</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Fecha</th>
              <th>Entidad</th>
              <th>Acción</th>
              <th>Detalle</th>
              <th>Responsable</th>
              <th>Hash</th>
            </tr>
          </thead>
          <tbody>
            {registros.map((l) => (
              <tr key={l.id}>
                <td>{l.id}</td>
                <td>{l.fecha}</td>
                <td>{l.entidad}</td>
                <td>{l.accion}</td>
                <td>{l.detalle}</td>
                <td>{l.responsable}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 11 }} title={l.hash}>
                  {l.hash.slice(0, 10)}…
                </td>
              </tr>
            ))}
            {!registros.length && (
              <tr>
                <td colSpan={7} className="sub">
                  Ningún movimiento coincide con el filtro aplicado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {datos?.total_paginas > 1 && (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 14 }}>
          {pagina > 1 && (
            <button className="btn btn-sec" onClick={() => setPagina((p) => p - 1)}>
              « Anterior
            </button>
          )}
          <span style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
            Página {pagina} de {datos.total_paginas}
          </span>
          {pagina < datos.total_paginas && (
            <button className="btn btn-sec" onClick={() => setPagina((p) => p + 1)}>
              Siguiente »
            </button>
          )}
        </div>
      )}
    </div>
  );
}

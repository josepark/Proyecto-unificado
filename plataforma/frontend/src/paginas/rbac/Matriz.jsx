import { useRef, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { rbacApi } from '../../api/rbac';

const NIVEL_COLOR = {
  A: '#b3261e', C: '#0b57a4', M: '#0e7c66', L: '#5f6a64', T: '#6d4ea0', '—': '#c9d0ca',
};

export default function Matriz() {
  const { puedeEditar } = useOutletContext();
  const { datos, cargando, error, recargar } = useApi(() => rbacApi.matriz(), []);
  const [editando, setEditando] = useState(null); // `${rolId}:${sistemaId}` o null
  const [guardando, setGuardando] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [resaltado, setResaltado] = useState(null);
  const columnasRef = useRef({});

  function irASistema(ev) {
    if (ev.key !== 'Enter') return;
    ev.preventDefault();
    const q = busqueda.trim().toLowerCase();
    if (!q) return;
    const encontrado = (datos?.sistemas ?? []).find((s) => s.nombre.toLowerCase().includes(q));
    if (!encontrado) return;
    columnasRef.current[encontrado.id]?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    setResaltado(encontrado.id);
    setTimeout(() => setResaltado(null), 2200);
  }

  if (error) {
    return (
      <div className="card">
        <div className="cuerpo">
          No se pudo cargar la Matriz RBAC ({error.status === 401 ? 'inicie sesión con rol Dinamizador o Administrador' : error.message}).
        </div>
      </div>
    );
  }
  if (cargando) return <p>Cargando matriz…</p>;

  const { roles, sistemas, celdas, niveles } = datos;

  async function cambiarNivel(rolId, sistemaId, nivel) {
    setGuardando(true);
    try {
      await rbacApi.editarCeldaMatriz(rolId, sistemaId, nivel);
      await recargar();
    } catch (e) {
      alert(e.message);
    } finally {
      setGuardando(false);
      setEditando(null);
    }
  }

  return (
    <div>
      <h2 style={{ margin: '4px 0 8px', color: 'var(--verde-profundo)' }}>Matriz de Control de Acceso</h2>
      <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
        <input
          placeholder="Buscar sistema… (Enter para ir)"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          onKeyDown={irASistema}
          style={{ maxWidth: 260 }}
        />
        <Link to="/rbac/matriz/comparar" style={{ fontSize: 13 }}>
          Comparar dos roles →
        </Link>
      </div>
      <p style={{ fontSize: 12, color: 'var(--texto-suave)', marginBottom: 12 }}>
        {roles.length} roles × {sistemas.length} sistemas.{' '}
        {niveles.map((n) => (
          <span key={n.codigo} style={{ marginRight: 10 }}>
            <span
              style={{
                display: 'inline-block', width: 10, height: 10, borderRadius: 2,
                background: NIVEL_COLOR[n.codigo], marginRight: 4, verticalAlign: 'middle',
              }}
            />
            {n.codigo} = {n.nombre}
          </span>
        ))}
      </p>

      <div style={{ overflow: 'auto', border: '1px solid var(--borde)', borderRadius: 10, maxHeight: '70vh' }}>
        <table style={{ borderRadius: 0 }}>
          <thead>
            <tr>
              <th style={{ position: 'sticky', left: 0, zIndex: 2, background: 'var(--verde-profundo)' }}>Rol</th>
              {sistemas.map((s) => (
                <th
                  key={s.id}
                  ref={(el) => { columnasRef.current[s.id] = el; }}
                  title={s.nombre}
                  style={{
                    writingMode: 'vertical-rl', textAlign: 'left', minWidth: 30,
                    background: resaltado === s.id ? '#fdf6e3' : undefined,
                    color: resaltado === s.id ? '#5c4a12' : undefined,
                  }}
                >
                  {s.nombre.length > 18 ? s.nombre.slice(0, 18) + '…' : s.nombre}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id}>
                <td style={{ position: 'sticky', left: 0, background: '#fff', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                  {r.abreviatura}
                </td>
                {sistemas.map((s) => {
                  const clave = `${r.id}:${s.id}`;
                  const nivel = celdas[clave] || '—';
                  const esEditable = puedeEditar && editando === clave;
                  return (
                    <td
                      key={s.id}
                      onClick={() => puedeEditar && !guardando && setEditando(clave)}
                      style={{
                        textAlign: 'center', cursor: puedeEditar ? 'pointer' : 'default',
                        background: esEditable ? '#fff' : resaltado === s.id ? '#fdf6e3' : undefined,
                      }}
                    >
                      {esEditable ? (
                        <select
                          autoFocus
                          defaultValue={nivel}
                          disabled={guardando}
                          onBlur={() => setEditando(null)}
                          onChange={(e) => cambiarNivel(r.id, s.id, e.target.value)}
                          style={{ padding: '2px 4px', fontSize: 11 }}
                        >
                          {niveles.map((n) => (
                            <option key={n.codigo} value={n.codigo}>{n.codigo}</option>
                          ))}
                        </select>
                      ) : (
                        <span
                          style={{
                            display: 'inline-block', width: 20, height: 20, lineHeight: '20px',
                            borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 'bold',
                            background: NIVEL_COLOR[nivel],
                          }}
                        >
                          {nivel === '—' ? '' : nivel}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

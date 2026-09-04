import { useApi } from '../../hooks/useApi';
import { inventarioApi } from '../../api/inventario';

const SEV_CLASE = { crit: 't-CRIT', alto: 't-ALTO', medio: 't-MEDIO', bajo: 't-BAJO' };
const SEV_TEXTO = { crit: 'Crítico', alto: 'Alto', medio: 'Medio', bajo: 'Bajo' };

export default function Alertas() {
  const { datos, cargando, error } = useApi(() => inventarioApi.alertas(), []);

  if (cargando) return <p>Cargando alertas…</p>;
  if (error) return <div className="card"><div className="cuerpo">No se pudieron cargar las alertas ({error.message}).</div></div>;

  const grupos = (datos?.grupos ?? []).filter((g) => g.items.length > 0);

  return (
    <div>
      <h2 style={{ margin: '4px 0 16px', color: 'var(--verde-profundo)' }}>Alertas</h2>

      {grupos.length === 0 && (
        <div className="card">
          <div className="cuerpo">Sin alertas activas por ahora.</div>
        </div>
      )}

      {grupos.map((g) => (
        <div key={g.clave} className="card" style={{ marginBottom: 14 }}>
          <h2>
            {g.titulo} <span style={{ float: 'right' }}>{g.items.length}</span>
          </h2>
          <div className="cuerpo">
            {g.items.map((it, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  padding: '8px 0',
                  borderTop: i > 0 ? '1px solid var(--borde)' : 'none',
                }}
              >
                <b style={{ minWidth: 78 }}>{it.id_activo}</b>
                <span style={{ flex: 1, color: '#444' }}>{it.nombre} — {it.detalle}</span>
                <span
                  className={`tag ${SEV_CLASE[it.severidad] || ''}`}
                  style={{ textTransform: 'uppercase' }}
                >
                  {SEV_TEXTO[it.severidad] || it.severidad}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

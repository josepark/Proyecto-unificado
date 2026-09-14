/** Aviso inline para errores de escritura (sustituye window.alert en RBAC). */
export default function BannerErrorMutacion({ error, onCerrar }) {
  if (!error) return null;
  return (
    <div
      className="card"
      style={{ marginBottom: 12, borderColor: 'var(--crit)' }}
      role="alert"
    >
      <div className="cuerpo" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, color: 'var(--crit)' }}>
        <span style={{ flex: 1 }}>{error}</span>
        {onCerrar ? (
          <button
            type="button"
            className="btn-sec"
            style={{ padding: '2px 8px', fontSize: 11 }}
            onClick={onCerrar}
            aria-label="Cerrar aviso"
          >
            ×
          </button>
        ) : null}
      </div>
    </div>
  );
}

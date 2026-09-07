/** Módulo externo SUIIN-SGSI-RIESGOS — mismo patrón que dashboard.html
 * embebe /riesgos/?embed=1. El PTR sigue siendo su propia SPA; aquí solo
 * se integra en la shell unificada sin duplicar pantallas. */
export default function ModuloRiesgosPTR() {
  return (
    <div className="modulo-externo">
      <iframe
        src="/riesgos/?embed=1"
        title="Gestión de Riesgos y PTR — SUIIN-SGSI-RIESGOS"
      />
    </div>
  );
}

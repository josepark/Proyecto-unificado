/* Módulo externo PTR — iframe a la SPA de SUIIN-SGSI-RIESGOS. */
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

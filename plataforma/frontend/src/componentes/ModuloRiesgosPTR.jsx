import { Routes, Route, useOutletContext, Navigate } from 'react-router-dom';
import { AuthProvider } from '@riesgos/context/AuthContext';
import { PlataformaProvider, useRiesgosTo } from '@riesgos/context/PlataformaContext';
import Layout from '@riesgos/components/Layout';
import RutaProtegida from '@riesgos/components/RutaProtegida';
import Dashboard from '@riesgos/pages/Dashboard';
import Activos from '@riesgos/pages/Activos';
import Vulnerabilidades from '@riesgos/pages/Vulnerabilidades';
import ActivoDetalle from '@riesgos/pages/ActivoDetalle';
import RiesgosContextuales from '@riesgos/pages/RiesgosContextuales';
import RedTeam from '@riesgos/pages/RedTeam';
import PlanTratamiento from '@riesgos/pages/PlanTratamiento';
import RiesgosActivo from '@riesgos/pages/RiesgosActivo';
import ImportarExcel from '@riesgos/pages/ImportarExcel';
import Cumplimiento from '@riesgos/pages/Cumplimiento';
import Catalogos from '@riesgos/pages/Catalogos';
import { tieneModulo } from '../lib/modulosPlataforma';
import '@riesgos/index-plataforma.css';

function RedirigirPanelRiesgos() {
  const to = useRiesgosTo('');
  return <Navigate to={to} replace />;
}

/** PTR nativo en la SPA unificada — sin iframe; comparte sesión vía JWT/cookie. */
export default function ModuloRiesgosPTR() {
  const { autenticado, cargando, modulos } = useOutletContext() ?? {};

  if (autenticado && !cargando && !tieneModulo(modulos, 'riesgos')) {
    return (
      <div className="card">
        <div className="cuerpo">
          Su cuenta no tiene acceso al proyecto <b>Gestión de Riesgos y PTR</b>.
        </div>
      </div>
    );
  }

  return (
    <PlataformaProvider anidado>
      <div className="modulo-riesgos-nativo">
        <AuthProvider plataformaAutenticada={!!autenticado} sesionCargando={!!cargando} unificado>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route element={<RutaProtegida />}>
                <Route path="activos" element={<Activos />} />
                <Route path="vulnerabilidades" element={<Vulnerabilidades />} />
                <Route path="activos/:id" element={<ActivoDetalle />} />
                <Route path="riesgos-contextuales" element={<RiesgosContextuales />} />
                <Route path="red-team" element={<RedTeam />} />
                <Route path="riesgos-activo" element={<RiesgosActivo />} />
                <Route path="plan-tratamiento" element={<PlanTratamiento />} />
                <Route path="importar" element={<ImportarExcel />} />
                <Route path="cumplimiento" element={<Cumplimiento />} />
                <Route path="catalogos" element={<Catalogos />} />
              </Route>
              <Route path="*" element={<RedirigirPanelRiesgos />} />
            </Route>
          </Routes>
        </AuthProvider>
      </div>
    </PlataformaProvider>
  );
}

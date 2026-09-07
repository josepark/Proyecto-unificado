import { Routes, Route, useOutletContext } from 'react-router-dom';
import { AuthProvider } from '@riesgos/context/AuthContext';
import { PlataformaProvider } from '@riesgos/context/PlataformaContext';
import Layout from '@riesgos/components/Layout';
import RutaProtegida from '@riesgos/components/RutaProtegida';
import Dashboard from '@riesgos/pages/Dashboard';
import Activos from '@riesgos/pages/Activos';
import Vulnerabilidades from '@riesgos/pages/Vulnerabilidades';
import ActivoDetalle from '@riesgos/pages/ActivoDetalle';
import RiesgosContextuales from '@riesgos/pages/RiesgosContextuales';
import RedTeam from '@riesgos/pages/RedTeam';
import PlanTratamiento from '@riesgos/pages/PlanTratamiento';
import Cumplimiento from '@riesgos/pages/Cumplimiento';
import Catalogos from '@riesgos/pages/Catalogos';
import '@riesgos/index-plataforma.css';

/** PTR nativo en la SPA unificada — sin iframe; comparte sesión vía JWT/cookie. */
export default function ModuloRiesgosPTR() {
  const { autenticado, cargando } = useOutletContext() ?? {};

  return (
    <PlataformaProvider anidado>
      <div className="modulo-riesgos-nativo">
        <AuthProvider plataformaAutenticada={!!autenticado} sesionCargando={!!cargando}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route element={<RutaProtegida />}>
                <Route path="activos" element={<Activos />} />
                <Route path="vulnerabilidades" element={<Vulnerabilidades />} />
                <Route path="activos/:id" element={<ActivoDetalle />} />
                <Route path="riesgos-contextuales" element={<RiesgosContextuales />} />
                <Route path="red-team" element={<RedTeam />} />
                <Route path="plan-tratamiento" element={<PlanTratamiento />} />
                <Route path="cumplimiento" element={<Cumplimiento />} />
                <Route path="catalogos" element={<Catalogos />} />
              </Route>
            </Route>
          </Routes>
        </AuthProvider>
      </div>
    </PlataformaProvider>
  );
}

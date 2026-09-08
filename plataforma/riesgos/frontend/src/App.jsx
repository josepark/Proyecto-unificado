import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import RutaProtegida from "./components/RutaProtegida";
import Dashboard from "./pages/Dashboard";
import Activos from "./pages/Activos";
import Vulnerabilidades from "./pages/Vulnerabilidades";
import ActivoDetalle from "./pages/ActivoDetalle";
import RiesgosContextuales from "./pages/RiesgosContextuales";
import RedTeam from "./pages/RedTeam";
import PlanTratamiento from "./pages/PlanTratamiento";
import RiesgosActivo from "./pages/RiesgosActivo";
import ImportarExcel from "./pages/ImportarExcel";
import Cumplimiento from "./pages/Cumplimiento";
import Catalogos from "./pages/Catalogos";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            {/* Mismo criterio de acceso que RBAC: sin sesión, solo el Panel
                general (arriba) es navegable — el resto queda bloqueado aquí,
                no solo oculto del menú, para que tampoco se llegue por URL
                directa. */}
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
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

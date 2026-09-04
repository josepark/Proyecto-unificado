import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Shell from './componentes/Shell';
import ModuloInventario from './componentes/ModuloInventario';
import ModuloRBAC from './componentes/ModuloRBAC';
import Dashboard from './paginas/inventario/Dashboard';
import Activo from './paginas/inventario/Activo';
import ActivoForm from './paginas/inventario/ActivoForm';
import ImportarActivos from './paginas/inventario/ImportarActivos';
import PanelEjecutivo from './paginas/inventario/PanelEjecutivo';
import Alertas from './paginas/inventario/Alertas';
import Riesgos from './paginas/inventario/Riesgos';
import CentroDatos from './paginas/inventario/CentroDatos';
import DatacenterForm from './paginas/inventario/DatacenterForm';
import DiagramaForm from './paginas/inventario/DiagramaForm';
import Bitacora from './paginas/inventario/Bitacora';
import Roles from './paginas/rbac/Roles';
import RolForm from './paginas/rbac/RolForm';
import Usuarios from './paginas/rbac/Usuarios';
import UsuarioForm from './paginas/rbac/UsuarioForm';
import Matriz from './paginas/rbac/Matriz';
import MatrizComparar from './paginas/rbac/MatrizComparar';
import Sistemas from './paginas/rbac/Sistemas';
import SistemaForm from './paginas/rbac/SistemaForm';
import Excepciones from './paginas/rbac/Excepciones';
import ExcepcionMasiva from './paginas/rbac/ExcepcionMasiva';
import Auditoria from './paginas/rbac/Auditoria';
import Inicio from './paginas/rbac/Inicio';

// Fase 3 completa (README sección 9.5): cada módulo tiene su propia
// sub-navegación (ModuloInventario/ModuloRBAC), igual que ya hacía el
// tablero original. Ficha de detalle de activo, formularios de
// Activo/Rol/Usuario/Sistema/Datacenter/Diagrama, Excepciones (individual
// y masiva), Auditoría, Riesgos, Centro de datos y Bitácora ya portados
// (Fase 1/2/3). Pendiente (Fase 4): tablero "Inicio" propio de RBAC,
// pruebas de frontend (Vitest), y decidir si el login se migra a React.
export default function App() {
  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route path="/" element={<Shell />}>
          <Route index element={<Navigate to="/inventario" replace />} />

          <Route path="inventario" element={<ModuloInventario />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="activos/nuevo" element={<ActivoForm />} />
            <Route path="activos/importar" element={<ImportarActivos />} />
            <Route path="activos/:id" element={<Activo />} />
            <Route path="activos/:id/editar" element={<ActivoForm />} />
            <Route path="panel-ejecutivo" element={<PanelEjecutivo />} />
            <Route path="riesgos" element={<Riesgos />} />
            <Route path="alertas" element={<Alertas />} />
            <Route path="centro-datos" element={<CentroDatos />} />
            <Route path="centro-datos/datacenters/nuevo" element={<DatacenterForm />} />
            <Route path="centro-datos/datacenters/:id/editar" element={<DatacenterForm />} />
            <Route path="centro-datos/diagramas/nuevo" element={<DiagramaForm />} />
            <Route path="centro-datos/diagramas/:id/editar" element={<DiagramaForm />} />
            <Route path="bitacora" element={<Bitacora />} />
          </Route>

          <Route path="rbac" element={<ModuloRBAC />}>
            <Route index element={<Navigate to="inicio" replace />} />
            <Route path="inicio" element={<Inicio />} />
            <Route path="roles" element={<Roles />} />
            <Route path="roles/nuevo" element={<RolForm />} />
            <Route path="roles/:id/editar" element={<RolForm />} />
            <Route path="usuarios" element={<Usuarios />} />
            <Route path="usuarios/nuevo" element={<UsuarioForm />} />
            <Route path="usuarios/:id/editar" element={<UsuarioForm />} />
            <Route path="matriz" element={<Matriz />} />
            <Route path="matriz/comparar" element={<MatrizComparar />} />
            <Route path="sistemas" element={<Sistemas />} />
            <Route path="sistemas/nuevo" element={<SistemaForm />} />
            <Route path="sistemas/:id/editar" element={<SistemaForm />} />
            <Route path="excepciones" element={<Excepciones />} />
            <Route path="excepciones/masiva" element={<ExcepcionMasiva />} />
            <Route path="auditoria" element={<Auditoria />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

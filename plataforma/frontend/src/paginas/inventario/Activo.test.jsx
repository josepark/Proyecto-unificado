import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Activo from './Activo';

// Patrón de permisos por rol: Shell.jsx provee {puedeEditar, puedeEliminar}
// via <Outlet context={...}>, y cada página los lee con useOutletContext().
// Para probarlo sin montar todo el árbol de Shell, se envuelve la ruta de
// prueba en un <Outlet> propio que provee el contexto que se quiera
// simular — mismo mecanismo, un solo nivel más simple.
const ACTIVO_FIXTURE = {
  id: 7, id_activo: 'RED-003', nombre: 'Firewall perimetral', clase: 'INFRA',
  clase_display: 'Infraestructura de red', nivel_riesgo: 'CRIT', nivel_riesgo_display: 'Crítico',
  clasificacion_si_display: 'Altamente Confidencial', estado_display: 'Activo',
  ciclo_vida_display: 'En producción', confidencialidad: 4, integridad: 4, disponibilidad: 4, valor: 12,
  procesa_datos_personales: false, fecha_registro: '2026-01-01', propietario: '', custodio: '',
  area_responsable: '', rto: '', rpo: '', datacenter_info: null, infraestructura: null, sistema: null,
  equipo: null, amenazas: [], controles: [], dependencias: [], notas_seguridad: '', descripcion: '',
  documentos_relacionados: '',
};

beforeEach(() => {
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/historial/')) return ok([]);
    if (u.includes('/hojavida/')) {
      return ok([
        {
          id: 10,
          fecha: '2026-02-01',
          tipo_evento: 'MPRE',
          tipo_evento_display: 'Mantenimiento preventivo',
          titulo: 'Revisión trimestral',
          descripcion: '',
          responsable: 'Operaciones',
          documento_url: null,
        },
      ]);
    }
    return ok(ACTIVO_FIXTURE);
  });
});
function ok(data) {
  return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => data };
}

function renderConContexto(contexto) {
  return render(
    <MemoryRouter initialEntries={['/inventario/activos/7']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/inventario/activos/:id" element={<Activo />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('Activo — guardas de rol', () => {
  it('Consultor (sin permisos) no ve Editar ni Eliminar', async () => {
    renderConContexto({ puedeEditar: false, puedeEliminar: false });
    await screen.findByText('RED-003');
    expect(screen.queryByRole('link', { name: /Editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Eliminar/i })).not.toBeInTheDocument();
    // pero el contenido de solo lectura sigue disponible
    expect(screen.getByRole('link', { name: /Hoja de vida PDF/i })).toBeInTheDocument();
  });

  it('Dinamizador (puedeEditar) ve Editar pero no Eliminar', async () => {
    renderConContexto({ puedeEditar: true, puedeEliminar: false });
    await screen.findByText('RED-003');
    expect(screen.getByRole('link', { name: /Editar/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Eliminar/i })).not.toBeInTheDocument();
  });

  it('Administrador (puedeEditar y puedeEliminar) ve ambos botones', async () => {
    renderConContexto({ puedeEditar: true, puedeEliminar: true });
    await screen.findByText('RED-003');
    expect(screen.getByRole('link', { name: /Editar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Eliminar/i })).toBeInTheDocument();
  });

  it('muestra eventos de hoja de vida del activo', async () => {
    renderConContexto({ puedeEditar: false, puedeEliminar: false });
    await screen.findByText('Revisión trimestral');
    expect(screen.getByText(/Mantenimiento preventivo/i)).toBeInTheDocument();
  });
});

describe('Activo — cruce Inventario ↔ RBAC', () => {
  it('muestra accesos locales y RBAC en vivo para sistemas', async () => {
    global.fetch = vi.fn(async (url) => {
      const u = String(url);
      if (u.includes('/historial/')) return ok([]);
      return ok({
        ...ACTIVO_FIXTURE,
        id_activo: 'SIS-001',
        nombre: 'Portal académico',
        clase: 'SIST',
        clase_display: 'Sistema de información',
        sistema: {
          estado_operativo: 'Producción',
          sistema_mca_equivalente: 'Portal',
          accesos: [{ rol: 'DTG', nivel: 'A' }],
          accesos_rbac: [{ rol: 'DTG', denominacion: 'Dinamizador', nivel: 'C' }],
        },
      });
    });

    renderConContexto({ puedeEditar: false, puedeEliminar: false });
    await screen.findByText('SIS-001');
    expect(screen.getByText(/registrado en el Inventario/i)).toBeInTheDocument();
    expect(screen.getByText(/según Matriz RBAC/i)).toBeInTheDocument();
    expect(screen.getByText('DTG (A)')).toBeInTheDocument();
    expect(screen.getByText('DTG (C)')).toBeInTheDocument();
  });

  it('avisa cuando RBAC no responde o no hay coincidencia', async () => {
    global.fetch = vi.fn(async (url) => {
      const u = String(url);
      if (u.includes('/historial/')) return ok([]);
      return ok({
        ...ACTIVO_FIXTURE,
        id_activo: 'SIS-002',
        clase: 'SIST',
        clase_display: 'Sistema de información',
        sistema: {
          sistema_mca_equivalente: 'Desconocido',
          accesos: [],
          accesos_rbac: null,
        },
      });
    });

    renderConContexto({ puedeEditar: false, puedeEliminar: false });
    await screen.findByText('SIS-002');
    expect(screen.getByText(/No se pudo verificar contra la Matriz RBAC/i)).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';

beforeEach(() => {
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/meta/')) {
      return ok({
        clases: [
          { codigo: 'INFRA', nombre: 'Infraestructura', color: '#1f6b52' },
          { codigo: 'SIST', nombre: 'Sistemas', color: '#c9a94e' },
        ],
        colores_clase: { INFRA: '#1f6b52', SIST: '#c9a94e' },
      });
    }
    if (u.includes('/estadisticas/')) {
      return ok({
        total_activos: 2,
        por_nivel_riesgo: {},
        por_clase: { SIST: 1, INFRA: 1 },
        clases: [
          { codigo: 'INFRA', nombre: 'Infraestructura', color: '#1f6b52' },
          { codigo: 'SIST', nombre: 'Sistemas', color: '#c9a94e' },
        ],
        datos_personales: 0,
      });
    }
    if (u.includes('/activos/')) {
      return ok({
        results: [
          { id: 1, id_activo: 'SIS-001', nombre: 'Portal', clase: 'SIST', nivel_riesgo: 'MED', nivel_riesgo_display: 'Medio', propietario: 'TI' },
          { id: 2, id_activo: 'RED-003', nombre: 'Firewall', clase: 'INFRA', nivel_riesgo: 'CRIT', nivel_riesgo_display: 'Crítico', propietario: 'Redes' },
        ],
      });
    }
    return ok({});
  });
});

function ok(data) {
  return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => data };
}

function renderDashboard(contexto = { puedeEditar: true }) {
  return render(
    <MemoryRouter initialEntries={['/inventario/dashboard']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/inventario/dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('Dashboard — exportación y etiquetas', () => {
  it('muestra enlace de exportar inventario a Excel', async () => {
    renderDashboard();
    const enlace = await screen.findByRole('link', { name: /Exportar Excel/i });
    expect(enlace).toHaveAttribute('href', '/api/exportar/inventario.xlsx');
  });

  it('muestra etiquetas en lote cuando hay activos seleccionados', async () => {
    renderDashboard();
    await screen.findByText('SIS-001');
    screen.getByLabelText('Seleccionar SIS-001').click();
    const enlace = await screen.findByRole('link', { name: /Etiquetas \(1\)/i });
    expect(enlace).toHaveAttribute('href', '/api/etiquetas/lote.pdf?ids=1');
  });
});

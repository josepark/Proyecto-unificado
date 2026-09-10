import { render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ModuloRiesgosPTR from './ModuloRiesgosPTR';

function ShellConSesion({ autenticado = true, cargando = false }) {
  return (
    <Outlet
      context={{
        autenticado,
        cargando,
        puedeEditar: autenticado,
        puedeEliminar: false,
        modulos: ['riesgos'],
      }}
    />
  );
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/token-jwt/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ token: 'jwt-test', username: 'admin', roles: ['Administrador'] }),
      };
    }
    if (u.includes('/dashboard/resumen/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          kpis: {
            activos_total: 1,
            vulnerabilidades_abiertas: 0,
            riesgos_criticos: 0,
            acciones_total: 0,
            acciones_cerradas: 0,
          },
          heatmap_probabilidad_impacto: [],
          campanas_red_team: [],
          activos_criticos_top: [],
        }),
      };
    }
    if (u.includes('/alertas/resumen/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          total_vencidas: 0,
          total_por_vencer: 0,
          acciones_vencidas: [],
          riesgos_activo_vencidos: [],
          acciones_por_vencer: [],
          riesgos_activo_por_vencer: [],
        }),
      };
    }
    return { ok: true, status: 200, json: async () => ({}) };
  }));
});

describe('ModuloRiesgosPTR', () => {
  it('renderiza el panel nativo sin iframe', async () => {
    render(
      <MemoryRouter initialEntries={['/gestion-riesgos']}>
        <Routes>
          <Route element={<ShellConSesion />}>
            <Route path="/gestion-riesgos/*" element={<ModuloRiesgosPTR />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(document.querySelector('iframe')).toBeNull();
    expect(document.querySelector('.modulo-riesgos-nativo')).toBeTruthy();
    expect(await screen.findByText(/Panel general/i)).toBeInTheDocument();
  });

  it('sin proyecto riesgos muestra puerta con enlace al módulo asignado', () => {
    render(
      <MemoryRouter initialEntries={['/gestion-riesgos']}>
        <Routes>
          <Route
            element={(
              <Outlet
                context={{
                  autenticado: true,
                  cargando: false,
                  puedeEditar: true,
                  puedeEliminar: false,
                  modulos: ['inventario'],
                }}
              />
            )}
          >
            <Route path="/gestion-riesgos/*" element={<ModuloRiesgosPTR />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText(/no tiene acceso al proyecto/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Ir a mi proyecto asignado/i })).toHaveAttribute(
      'href',
      '/inventario/dashboard',
    );
  });
});

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ModuloRiesgosPTR from './ModuloRiesgosPTR';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/token-jwt/')) {
      return { ok: false, status: 401, json: async () => ({ detail: 'no session' }) };
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
          <Route path="/gestion-riesgos/*" element={<ModuloRiesgosPTR />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(document.querySelector('iframe')).toBeNull();
    expect(document.querySelector('.modulo-riesgos-nativo')).toBeTruthy();
    expect(await screen.findByText(/Panel general/i)).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Inicio from './Inicio';

const INICIO_FIXTURE = {
  stats: { roles: 27, sistemas: 12, accesos: 180, usuarios: 8 },
  riesgo: [{ nombre: 'Alto', n: 5, color: '#d97706' }],
  max_riesgo: 5,
  mfa_pct: 75,
  mfa_ok: 3,
  mfa_total: 4,
  dias_alerta: 7,
  proximos_vencimientos: [],
  alertas_mfa: [],
  criticos: [{ abreviatura: 'ADM', denominacion: 'Administrador', n_admin: 4 }],
  temporales: [],
  revocados: [],
  log: [{ id: 1, fecha: '2026-03-01', entidad: 'Rol', accion: 'Editar', detalle: 'ADM' }],
};

beforeEach(() => {
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/csrf')) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({ csrf_token: 'tok' }),
      };
    }
    if (u.includes('/inicio')) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => INICIO_FIXTURE,
      };
    }
    return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({}) };
  });
});

describe('Inicio RBAC', () => {
  it('muestra KPIs del tablero devueltos por /rbac/api/inicio', async () => {
    render(
      <MemoryRouter initialEntries={['/rbac/inicio']}>
        <Routes>
          <Route path="/rbac/inicio" element={<Inicio />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('27')).toBeInTheDocument();
    expect(screen.getByText('Roles definidos')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
  });
});

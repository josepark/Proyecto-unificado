import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Riesgos from './Riesgos';

// Patrón para páginas de solo lectura que consumen inventarioApi: se
// simula fetch() directamente (mismo mecanismo que ya usa toda la app a
// través de src/api/client.js), en vez de simular el módulo de la API.
// Así la prueba también verifica que el cliente HTTP real construye bien
// la URL y procesa la respuesta.
const ACTIVO_EJEMPLO = {
  id: 7, id_activo: 'RED-003', nombre: 'Firewall perimetral', clase: 'INFRA',
  probabilidad: 4, impacto: 4, score: 16, nivel: 'ALTO', nivel_registrado: 'CRIT',
};
const RIESGOS_FIXTURE = {
  activos: [ACTIVO_EJEMPLO],
  matriz: { '4,4': 1 },
  por_nivel: { ALTO: 1 },
  sin_valorar: 0,
};
const COBERTURA_FIXTURE = {
  total_controles: 21, controles_usados: 10, total_activos: 38, activos_con_control: 20,
  cobertura_activos_pct: 52.6,
  detalle: [{ codigo: '8.13', descripcion: 'Copias de respaldo', num_activos: 5 }],
};

function mockFetchJson(url) {
  const u = String(url);
  if (u.includes('/cobertura/')) return COBERTURA_FIXTURE;
  if (u.includes('/riesgos/')) return RIESGOS_FIXTURE;
  return {};
}

beforeEach(() => {
  global.fetch = vi.fn(async (url) => ({
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
    json: async () => mockFetchJson(url),
  }));
});

function renderConRuta(ui) {
  return render(
    <MemoryRouter initialEntries={['/inventario/riesgos']}>
      <Routes>
        <Route path="/inventario/riesgos" element={ui} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Riesgos', () => {
  it('muestra el activo devuelto por /api/riesgos/', async () => {
    renderConRuta(<Riesgos />);
    expect(await screen.findByText('RED-003')).toBeInTheDocument();
  });

  it('marca la diferencia cuando el nivel calculado no coincide con el registrado', async () => {
    renderConRuta(<Riesgos />);
    expect(await screen.findByText(/≠ registrado \(CRIT\)/)).toBeInTheDocument();
  });

  it('muestra la cobertura de controles real', async () => {
    renderConRuta(<Riesgos />);
    expect(await screen.findByText(/10\/21/)).toBeInTheDocument();
  });
});

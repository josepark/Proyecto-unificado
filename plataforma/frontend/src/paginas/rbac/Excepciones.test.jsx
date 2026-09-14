import { render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Excepciones from './Excepciones';

vi.mock('../../api/rbac', () => ({
  rbacApi: {
    listarExcepciones: vi.fn(),
    catalogos: vi.fn(),
    listarUsuarios: vi.fn(),
    listarSistemas: vi.fn(),
    crearExcepcion: vi.fn(),
    eliminarExcepcion: vi.fn(),
  },
}));

import { rbacApi } from '../../api/rbac';

beforeEach(() => {
  vi.mocked(rbacApi.listarExcepciones).mockResolvedValue({
    filas: [{
      usuario_id: 1,
      sistema_id: 2,
      usuario: 'Ana Pérez',
      usuario_estado: 'Activo',
      sistema: 'Portal',
      rol: 'ADM',
      nivel_rol: 'L',
      nivel_excepcion: 'A',
      motivo: 'Proyecto temporal',
      fecha_fin: null,
      vencida: false,
    }],
    total_vigentes: 1,
    total_vencidas: 0,
  });
  vi.mocked(rbacApi.catalogos).mockResolvedValue({
    niveles_acceso: [{ codigo: 'L', nombre: 'Lectura' }],
  });
  vi.mocked(rbacApi.listarUsuarios).mockResolvedValue([]);
  vi.mocked(rbacApi.listarSistemas).mockResolvedValue([]);
});

function renderExcepciones(contexto = { puedeEditar: true }) {
  return render(
    <MemoryRouter initialEntries={['/rbac/excepciones']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/rbac/excepciones" element={<Excepciones />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('Excepciones RBAC', () => {
  it('lista excepciones vigentes', async () => {
    renderExcepciones();
    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument();
    expect(screen.getByText('Proyecto temporal')).toBeInTheDocument();
  });

  it('muestra botón de nueva excepción solo si puede editar', async () => {
    renderExcepciones({ puedeEditar: false });
    await screen.findByText('Ana Pérez');
    expect(screen.queryByRole('button', { name: /Nueva excepción/i })).not.toBeInTheDocument();
  });
});

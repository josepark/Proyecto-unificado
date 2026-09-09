import { render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Matriz from './Matriz';

vi.mock('../../api/rbac', () => ({
  rbacApi: {
    catalogos: vi.fn(),
    heatmapMatriz: vi.fn(),
    matriz: vi.fn(),
    editarCeldaMatriz: vi.fn(),
  },
}));

import { rbacApi } from '../../api/rbac';

const MATRIZ = {
  roles: [{ id: 1, abreviatura: 'ADM', denominacion: 'Admin', grupo: 'TI' }],
  sistemas: [{ id: 10, nombre: 'Portal', categoria: 'Apps' }],
  celdas: { '1:10': 'A' },
  niveles: [
    { codigo: 'A', nombre: 'Admin', descripcion: 'Administrador' },
    { codigo: '—', nombre: 'Ninguno', descripcion: '' },
  ],
};

beforeEach(() => {
  vi.mocked(rbacApi.catalogos).mockResolvedValue({ grupos_rol: [], categorias_sistema: [] });
  vi.mocked(rbacApi.heatmapMatriz).mockResolvedValue([]);
  vi.mocked(rbacApi.matriz).mockResolvedValue(MATRIZ);
});

function renderMatriz(contexto = { puedeEditar: true, soloLecturaRbac: false }) {
  return render(
    <MemoryRouter initialEntries={['/rbac/matriz']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/rbac/matriz" element={<Matriz />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('Matriz RBAC', () => {
  it('muestra la grilla con rol y sistema', async () => {
    renderMatriz();
    expect(await screen.findByText('Matriz de Control de Acceso')).toBeInTheDocument();
    expect(screen.getByText('ADM')).toBeInTheDocument();
    expect(screen.getByText('Portal')).toBeInTheDocument();
  });

  it('indica modo consulta para Consultor', async () => {
    renderMatriz({ puedeEditar: false, soloLecturaRbac: true });
    await screen.findByText(/Modo consulta/i);
  });
});

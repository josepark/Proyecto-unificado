import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import UsuariosPlataforma from './UsuariosPlataforma';

vi.mock('../../api/inventario', () => ({
  inventarioApi: {
    listarUsuariosPlataforma: vi.fn(),
    metaUsuariosPlataforma: vi.fn(),
    editarUsuarioPlataforma: vi.fn(),
    eliminarUsuarioPlataforma: vi.fn(),
  },
}));

import { inventarioApi } from '../../api/inventario';

beforeEach(() => {
  vi.mocked(inventarioApi.listarUsuariosPlataforma).mockResolvedValue({
    results: [
      {
        id: 1,
        username: 'ana',
        nombre_completo: 'Ana Mesa',
        area: 'UAIIN',
        rol: 'Consultor',
        email: 'ana@cric.org.co',
        is_active: true,
            is_superuser: false,
            modulos_acceso: ['inventario', 'rbac'],
          },
    ],
  });
  vi.mocked(inventarioApi.metaUsuariosPlataforma).mockResolvedValue({
    roles: ['Consultor', 'Dinamizador', 'Administrador'],
    areas: ['UAIIN'],
    modulos: ['inventario', 'rbac', 'riesgos'],
  });
});

function renderConContexto(contexto) {
  return render(
    <MemoryRouter initialEntries={['/inventario/usuarios']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/inventario/usuarios" element={<UsuariosPlataforma />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('UsuariosPlataforma', () => {
  it('muestra aviso si no es administrador', () => {
    renderConContexto({ puedeEliminar: false });
    expect(screen.getByText(/requiere rol/i)).toBeInTheDocument();
  });

  it('lista cuentas para administrador', async () => {
    renderConContexto({ puedeEliminar: true });
    await waitFor(() => {
      expect(screen.getByText('ana')).toBeInTheDocument();
    });
    expect(screen.getByText('UAIIN')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /nueva cuenta/i })).toBeInTheDocument();
  });
});

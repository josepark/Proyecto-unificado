import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import UsuarioPlataformaForm from './UsuarioPlataformaForm';

vi.mock('../../api/inventario', () => ({
  inventarioApi: {
    metaUsuariosPlataforma: vi.fn(() =>
      Promise.resolve({ roles: ['Consultor'], areas: [], modulos: ['inventario', 'rbac', 'riesgos'] }),
    ),
  },
}));

vi.mock('../../hooks/useApi', () => ({
  useApi: (fn) => {
    const key = String(fn);
    if (key.includes('meta')) {
      return {
        datos: { roles: ['Consultor'], areas: [], modulos: ['inventario', 'rbac', 'riesgos'] },
        cargando: false,
        error: null,
      };
    }
    return { datos: null, cargando: false, error: null, recargar: vi.fn() };
  },
}));

function renderNuevo() {
  return render(
    <MemoryRouter initialEntries={['/inventario/usuarios/nuevo']}>
      <Routes>
        <Route element={<Outlet context={{ puedeEliminar: true }} />}>
          <Route path="/inventario/usuarios/nuevo" element={<UsuarioPlataformaForm />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('UsuarioPlataformaForm — alta', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('muestra formulario limpio al crear', () => {
    renderNuevo();
    expect(screen.getByLabelText(/Usuario \(login\)/i)).toHaveValue('');
    expect(screen.getByLabelText(/Rol en la plataforma/i)).toHaveValue('');
    const checks = screen.getAllByRole('checkbox').filter(
      (el) => el.closest('label')?.textContent?.includes('Inventario')
        || el.closest('label')?.textContent?.includes('RBAC')
        || el.closest('label')?.textContent?.includes('Riesgos'),
    );
    expect(checks.length).toBe(3);
    checks.forEach((c) => expect(c).not.toBeChecked());
    expect(screen.getByText(/ningún proyecto seleccionado/i)).toBeInTheDocument();
  });
});

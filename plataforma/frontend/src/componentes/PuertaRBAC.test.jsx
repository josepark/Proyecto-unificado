import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import PuertaRBAC from './PuertaRBAC';

function renderConContexto(contexto) {
  return render(
    <MemoryRouter initialEntries={['/rbac/inicio']}>
      <Routes>
        <Route element={<Outlet context={contexto} />}>
          <Route path="/rbac/inicio" element={<PuertaRBAC />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('PuertaRBAC', () => {
  it('Consultor ve mensaje de acceso restringido, no la sub-navegación RBAC', () => {
    renderConContexto({ puedeEditar: false, autenticado: true });
    expect(screen.getByText(/Matriz de Control de Acceso/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^Roles$/i })).not.toBeInTheDocument();
  });

  it('Anónimo ve enlace para iniciar sesión', () => {
    renderConContexto({ puedeEditar: false, autenticado: false });
    expect(screen.getByRole('link', { name: /Iniciar sesión/i })).toHaveAttribute(
      'href',
      '/login/?next=/app/rbac/inicio',
    );
  });
});

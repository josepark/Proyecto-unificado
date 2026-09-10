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
  it('Consultor entra en modo consulta (solo lectura)', () => {
    renderConContexto({
      puedeEditar: false,
      autenticado: true,
      roles: ['Consultor'],
      soloLecturaRbac: true,
      modulos: ['rbac'],
    });
    expect(screen.getByText(/Modo consulta RBAC/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Roles$/i })).toBeInTheDocument();
  });

  it('Anónimo ve enlace para iniciar sesión', () => {
    renderConContexto({ puedeEditar: false, autenticado: false });
    expect(screen.getByRole('link', { name: /Iniciar sesión/i })).toHaveAttribute(
      'href',
      '/login?next=%2Frbac%2Finicio',
    );
  });

  it('Dinamizador entra al módulo cuando la sesión confirma puedeEditar', () => {
    renderConContexto({ puedeEditar: true, autenticado: true, modulos: ['rbac'] });
    expect(screen.getByRole('link', { name: /^Roles$/i })).toBeInTheDocument();
  });
});

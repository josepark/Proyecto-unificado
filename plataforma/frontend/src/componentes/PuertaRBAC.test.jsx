import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('Consultor ve mensaje de acceso restringido, no la sub-navegación RBAC', () => {
    renderConContexto({ puedeEditar: false, autenticado: true });
    expect(screen.getByText(/Matriz de Control de Acceso/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^Roles$/i })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('Anónimo ve enlace para iniciar sesión', () => {
    renderConContexto({ puedeEditar: false, autenticado: false });
    expect(screen.getByRole('link', { name: /Iniciar sesión/i })).toHaveAttribute(
      'href',
      '/login?next=/rbac/inicio',
    );
  });

  it('Dinamizador autorizado por /api/auth-rbac/ entra al módulo', async () => {
    vi.mocked(fetch).mockResolvedValue({ status: 204 });
    renderConContexto({ puedeEditar: true, autenticado: true });
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /^Roles$/i })).toBeInTheDocument();
    });
    expect(fetch).toHaveBeenCalledWith('/api/auth-rbac/', { credentials: 'same-origin' });
  });

  it('Muestra aviso si /api/auth-rbac/ rechaza la sesión', async () => {
    vi.mocked(fetch).mockResolvedValue({ status: 401 });
    renderConContexto({ puedeEditar: true, autenticado: true });
    expect(await screen.findByText(/No se pudo autorizar el acceso a RBAC/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^Roles$/i })).not.toBeInTheDocument();
  });
});

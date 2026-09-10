import { render, screen } from '@testing-library/react';
import { MemoryRouter, useOutletContext } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ModuloInventario from './ModuloInventario';

const { contextoBase } = vi.hoisted(() => ({
  contextoBase: {
    autenticado: true,
    modulos: ['inventario'],
    alertasUnificadas: {
      total_consolidado: 3,
      vinculacion: {
        disponible: true,
        sin_espejo_riesgos: 2,
        huerfanos_riesgos: 1,
      },
    },
  },
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet" />,
    useOutletContext: vi.fn(() => contextoBase),
  };
});

describe('ModuloInventario — badges Ola 6', () => {
  beforeEach(() => {
    vi.mocked(useOutletContext).mockReturnValue(contextoBase);
  });
  it('muestra badge de alertas y de sincronización en pestañas', () => {
    render(
      <MemoryRouter initialEntries={['/inventario/dashboard']}>
        <ModuloInventario />
      </MemoryRouter>,
    );
    expect(screen.getByText('Centro de alertas')).toBeInTheDocument();
    expect(screen.getByText('Valoración inherente')).toBeInTheDocument();
    const badges = document.querySelectorAll('.badge-modulo');
    expect(badges.length).toBe(2);
    expect(badges[0].textContent).toBe('↻3');
    expect(badges[1].textContent).toBe('3');
  });

  it('sin sesión muestra puerta de login en lugar del dashboard', () => {
    vi.mocked(useOutletContext).mockReturnValue({
      autenticado: false,
      alertasUnificadas: { total_consolidado: 0, vinculacion: { disponible: false } },
    });
    render(
      <MemoryRouter initialEntries={['/inventario/dashboard']}>
        <ModuloInventario />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: /Iniciar sesión/i })).toHaveAttribute(
      'href',
      '/login?next=%2Finventario%2Fdashboard',
    );
    expect(screen.queryByTestId('outlet')).not.toBeInTheDocument();
  });

  it('admin sin inventario en cuentas de acceso solo ve esa pestaña', () => {
    vi.mocked(useOutletContext).mockReturnValue({
      autenticado: true,
      modulos: ['rbac'],
      puedeEliminar: true,
      alertasUnificadas: { total_consolidado: 0, vinculacion: { disponible: false } },
    });
    render(
      <MemoryRouter initialEntries={['/inventario/usuarios']}>
        <ModuloInventario />
      </MemoryRouter>,
    );
    expect(screen.getByText('Cuentas de acceso')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.getByTestId('outlet')).toBeInTheDocument();
  });
});

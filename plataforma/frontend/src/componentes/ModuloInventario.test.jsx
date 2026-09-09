import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import ModuloInventario from './ModuloInventario';

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet" />,
    useOutletContext: () => ({
      alertasUnificadas: {
        total_consolidado: 3,
        vinculacion: {
          disponible: true,
          sin_espejo_riesgos: 2,
          huerfanos_riesgos: 1,
        },
      },
    }),
  };
});

describe('ModuloInventario — badges Ola 6', () => {
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
});

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Shell from './Shell';

vi.mock('../hooks/useSesion', () => ({
  useSesion: vi.fn(),
}));

vi.mock('../api/rbac', () => ({
  rbacApi: { resumen: vi.fn() },
}));

import { useSesion } from '../hooks/useSesion';
import { rbacApi } from '../api/rbac';

beforeEach(() => {
  vi.mocked(rbacApi.resumen).mockResolvedValue({ pendientes_total: 3 });
});

describe('Shell — pestañas de módulo', () => {
  it('muestra las tres pestañas de módulo como el tablero Django', () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'dinamizador',
      puedeEditar: true,
      puedeEliminar: false,
      cargando: false,
    });
    render(
      <MemoryRouter initialEntries={['/inventario/dashboard']}>
        <Shell />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: /Inventario/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Matriz RBAC/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Gestión de Riesgos y PTR/i })).toBeInTheDocument();
  });

  it('muestra badge de pendientes RBAC solo cuando puedeEditar', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'dinamizador',
      puedeEditar: true,
      puedeEliminar: false,
      cargando: false,
    });
    render(
      <MemoryRouter initialEntries={['/inventario/dashboard']}>
        <Shell />
      </MemoryRouter>,
    );
    expect(await screen.findByText('3')).toHaveClass('badge-modulo');
    expect(rbacApi.resumen).toHaveBeenCalled();
  });
});

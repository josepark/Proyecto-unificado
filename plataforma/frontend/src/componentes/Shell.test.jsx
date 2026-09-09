import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Shell from './Shell';
import { SesionProvider } from '../hooks/useSesion';

vi.mock('../hooks/useSesion', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useSesion: vi.fn(),
  };
});

vi.mock('../api/rbac', () => ({
  rbacApi: { resumen: vi.fn() },
}));

vi.mock('../api/inventario', () => ({
  inventarioApi: { alertasUnificadas: vi.fn() },
}));

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    consultarSesionInventario: vi.fn(),
  };
});

import { useSesion } from '../hooks/useSesion';
import { rbacApi } from '../api/rbac';
import { inventarioApi } from '../api/inventario';
import { consultarSesionInventario } from '../api/client';

function renderShell(initial = '/inventario/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <SesionProvider>
        <Shell />
      </SesionProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(rbacApi.resumen).mockResolvedValue({
    pendientes_total: 3,
    desglose_pendientes: {
      proximos_vencimientos: 1,
      alertas_mfa: 1,
      roles_certificacion_vencida: 1,
      excepciones_vencidas: 0,
    },
  });
  vi.mocked(inventarioApi.alertasUnificadas).mockResolvedValue({
    total_consolidado: 8,
    resumen: { inventario: 4, rbac: 3, riesgos: 2, inventario_criticas: 1 },
  });
  vi.mocked(consultarSesionInventario).mockResolvedValue({
    autenticado: true,
    puede_editar: true,
    usuario: 'dinamizador',
    roles: ['Dinamizador'],
  });
});

describe('Shell — pestañas de módulo', () => {
  it('muestra las tres pestañas de módulo como el tablero Django', () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'dinamizador',
      puedeEditar: true,
      puedeEliminar: false,
      cargando: false,
      recargar: vi.fn(),
    });
    renderShell();
    expect(screen.getByRole('link', { name: /Inventario/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Matriz RBAC/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Gestión de Riesgos y PTR/i })).toBeInTheDocument();
  });

  it('muestra badge de pendientes RBAC cuando puede editar o es Consultor', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'dinamizador',
      puedeEditar: true,
      puedeEliminar: false,
      cargando: false,
      roles: ['Dinamizador'],
      recargar: vi.fn(),
    });
    renderShell();
    expect(await screen.findByText('3')).toHaveClass('badge-modulo');
    expect(rbacApi.resumen).toHaveBeenCalled();
  });

  it('muestra badge de pendientes RBAC también para Consultor (solo lectura)', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'consultor',
      puedeEditar: false,
      puedeEliminar: false,
      cargando: false,
      roles: ['Consultor'],
      recargar: vi.fn(),
    });
    renderShell();
    expect(await screen.findByText('3')).toHaveClass('badge-modulo');
    expect(rbacApi.resumen).toHaveBeenCalled();
  });

  it('muestra badges de alertas unificadas en Inventario y Riesgos', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      usuario: 'dinamizador',
      puedeEditar: true,
      puedeEliminar: false,
      cargando: false,
      roles: ['Dinamizador'],
      recargar: vi.fn(),
    });
    renderShell();
    const badges = await screen.findAllByText('8');
    expect(badges.some((el) => el.classList.contains('badge-modulo'))).toBe(true);
    expect(await screen.findByText('2')).toHaveClass('badge-modulo');
    expect(inventarioApi.alertasUnificadas).toHaveBeenCalled();
  });
});

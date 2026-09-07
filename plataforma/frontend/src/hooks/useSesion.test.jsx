import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { eventosApi } from '../api/client';
import { SesionProvider, useSesion } from './useSesion';

vi.mock('../api/inventario', () => ({
  inventarioApi: { sesion: vi.fn() },
}));

import { inventarioApi } from '../api/inventario';

function Sonda() {
  const { autenticado, usuario, puedeEditar, cargando } = useSesion();
  return (
    <div>
      <span data-testid="cargando">{String(cargando)}</span>
      <span data-testid="autenticado">{String(autenticado)}</span>
      <span data-testid="usuario">{usuario ?? '—'}</span>
      <span data-testid="editar">{String(puedeEditar)}</span>
    </div>
  );
}

describe('SesionProvider', () => {
  beforeEach(() => {
    vi.mocked(inventarioApi.sesion).mockResolvedValue({
      autenticado: true,
      usuario: 'admin',
      roles: ['Administrador'],
      puede_editar: true,
      puede_eliminar: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('carga la sesión al montar', async () => {
    render(
      <SesionProvider>
        <Sonda />
      </SesionProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('cargando')).toHaveTextContent('false'));
    expect(screen.getByTestId('usuario')).toHaveTextContent('admin');
    expect(inventarioApi.sesion).toHaveBeenCalled();
  });

  it('aplica sesion-actualizada sin otra petición de red', async () => {
    render(
      <SesionProvider>
        <Sonda />
      </SesionProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('cargando')).toHaveTextContent('false'));
    const llamadas = vi.mocked(inventarioApi.sesion).mock.calls.length;

    eventosApi.dispatchEvent(
      new CustomEvent('sesion-actualizada', {
        detail: {
          autenticado: false,
          usuario: null,
          roles: [],
          puede_editar: false,
          puede_eliminar: false,
        },
      }),
    );

    await waitFor(() => expect(screen.getByTestId('autenticado')).toHaveTextContent('false'));
    expect(screen.getByTestId('editar')).toHaveTextContent('false');
    expect(vi.mocked(inventarioApi.sesion).mock.calls.length).toBe(llamadas);
  });
});

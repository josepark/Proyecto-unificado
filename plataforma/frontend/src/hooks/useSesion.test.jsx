import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { eventosApi } from '../api/client';
import { SesionProvider, useSesion } from './useSesion';

vi.mock('../api/inventario', () => ({
  inventarioApi: { sesion: vi.fn() },
}));

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    obtenerSesionConfiable: vi.fn(),
  };
});

import { inventarioApi } from '../api/inventario';
import { obtenerSesionConfiable } from '../api/client';

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

const SESION_ADMIN = {
  autenticado: true,
  usuario: 'admin',
  roles: ['Administrador'],
  puede_editar: true,
  puede_eliminar: true,
};

describe('SesionProvider', () => {
  beforeEach(() => {
    vi.mocked(obtenerSesionConfiable).mockResolvedValue(SESION_ADMIN);
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
    expect(obtenerSesionConfiable).toHaveBeenCalled();
  });

  it('confirma cierre de sesión antes de aplicar sesion-actualizada con autenticado false', async () => {
    render(
      <SesionProvider>
        <Sonda />
      </SesionProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('cargando')).toHaveTextContent('false'));

    vi.mocked(obtenerSesionConfiable).mockResolvedValue({
      autenticado: false,
      usuario: null,
      roles: [],
      puede_editar: false,
      puede_eliminar: false,
    });

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
    expect(obtenerSesionConfiable).toHaveBeenCalled();
  });

  it('ignora un autenticado false puntual si la re-lectura confirma sesión activa', async () => {
    vi.mocked(obtenerSesionConfiable).mockResolvedValue(SESION_ADMIN);

    render(
      <SesionProvider>
        <Sonda />
      </SesionProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('autenticado')).toHaveTextContent('true'));
  });
});

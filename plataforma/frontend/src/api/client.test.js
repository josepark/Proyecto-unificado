import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { crearCliente, eventosApi, consultarSesionInventario } from './client';

describe('client — manejo de 401', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('no emite sesion-vencida en 401 de RBAC si la sesión del Inventario sigue activa', async () => {
    const vencida = vi.fn();
    const actualizada = vi.fn();
    eventosApi.addEventListener('sesion-vencida', vencida);
    eventosApi.addEventListener('sesion-actualizada', actualizada);

    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'No autorizado' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          autenticado: true,
          usuario: 'admin',
          roles: ['Consultor'],
          puede_editar: false,
          puede_eliminar: false,
        }),
      });

    const rbac = crearCliente({
      base: '/rbac/api',
      csrf: { tipo: 'token', endpoint: '/csrf', campo: 'csrf_token', header: 'X-CSRF-Token' },
    });

    await expect(rbac.get('/inicio')).rejects.toMatchObject({ status: 401 });
    expect(vencida).not.toHaveBeenCalled();
    expect(actualizada).toHaveBeenCalledTimes(1);

    eventosApi.removeEventListener('sesion-vencida', vencida);
    eventosApi.removeEventListener('sesion-actualizada', actualizada);
  });

  it('emite sesion-vencida en 401 de RBAC cuando la sesión del Inventario ya no existe', async () => {
    const vencida = vi.fn();

    eventosApi.addEventListener('sesion-vencida', vencida);

    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'No autorizado' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ autenticado: false, usuario: null, roles: [], puede_editar: false, puede_eliminar: false }),
      });

    const rbac = crearCliente({
      base: '/rbac/api',
      csrf: { tipo: 'token', endpoint: '/csrf', campo: 'csrf_token', header: 'X-CSRF-Token' },
    });

    await expect(rbac.get('/inicio')).rejects.toMatchObject({ status: 401 });
    expect(vencida).toHaveBeenCalledTimes(1);

    eventosApi.removeEventListener('sesion-vencida', vencida);
  });

  it('consultarSesionInventario devuelve autenticado false si la petición falla', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('network'));
    await expect(consultarSesionInventario()).resolves.toEqual({ autenticado: false });
  });
});

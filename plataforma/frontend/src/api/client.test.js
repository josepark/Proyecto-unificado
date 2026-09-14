import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { crearCliente, eventosApi, consultarSesionInventario } from './client';

describe('client — manejo de 401', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('ignora 401 de RBAC — no toca el estado global de sesión', async () => {
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
        json: async () => ({ autenticado: false, puede_editar: false }),
      });

    const rbac = crearCliente({
      base: '/rbac/api',
      csrf: { tipo: 'token', endpoint: '/csrf', campo: 'csrf_token', header: 'X-CSRF-Token' },
    });

    await expect(rbac.get('/inicio')).rejects.toMatchObject({ status: 401 });
    expect(vencida).not.toHaveBeenCalled();
    expect(actualizada).not.toHaveBeenCalled();

    eventosApi.removeEventListener('sesion-vencida', vencida);
    eventosApi.removeEventListener('sesion-actualizada', actualizada);
  });

  it('emite sesion-vencida en 401 del Inventario cuando la sesión ya no existe', async () => {
    const vencida = vi.fn();

    eventosApi.addEventListener('sesion-vencida', vencida);

    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'No autenticado' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ autenticado: false, usuario: null, roles: [], puede_editar: false, puede_eliminar: false }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ autenticado: false, usuario: null, roles: [], puede_editar: false, puede_eliminar: false }),
      });

    const inventario = crearCliente({
      base: '/api',
      csrf: { tipo: 'cookie', cookie: 'csrftoken', header: 'X-CSRFToken' },
    });

    await expect(inventario.get('/activos/')).rejects.toMatchObject({ status: 401 });
    expect(vencida).toHaveBeenCalledTimes(1);

    eventosApi.removeEventListener('sesion-vencida', vencida);
  });

  it('403 del Inventario no cierra la sesión global (permiso, no autenticación)', async () => {
    const vencida = vi.fn();
    const actualizada = vi.fn();
    eventosApi.addEventListener('sesion-vencida', vencida);
    eventosApi.addEventListener('sesion-actualizada', actualizada);

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'No tiene permiso' }),
    });

    const inventario = crearCliente({
      base: '/api',
      csrf: { tipo: 'cookie', cookie: 'csrftoken', header: 'X-CSRFToken' },
    });

    await expect(inventario.get('/activos/meta/')).rejects.toMatchObject({ status: 403 });
    expect(vencida).not.toHaveBeenCalled();
    expect(actualizada).not.toHaveBeenCalled();

    eventosApi.removeEventListener('sesion-vencida', vencida);
    eventosApi.removeEventListener('sesion-actualizada', actualizada);
  });

  it('reintenta GET de RBAC tras 401 si la sesión del Inventario sigue activa', async () => {
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
          puede_editar: true,
          usuario: 'admin',
          roles: ['Administrador'],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({ ok: true }),
      });

    const rbac = crearCliente({
      base: '/rbac/api',
      csrf: { tipo: 'token', endpoint: '/csrf', campo: 'csrf_token', header: 'X-CSRF-Token' },
    });

    await expect(rbac.get('/inicio')).resolves.toEqual({ ok: true });
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it('consultarSesionInventario devuelve autenticado false si la petición falla', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('network'));
    await expect(consultarSesionInventario()).resolves.toEqual({ autenticado: false });
  });
});

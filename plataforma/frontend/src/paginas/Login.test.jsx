import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Login from './Login';

const recargar = vi.fn().mockResolvedValue(undefined);

vi.mock('../hooks/useSesion', () => ({
  useSesion: () => ({ autenticado: false, cargando: false, recargar }),
}));

vi.mock('../api/inventario', () => ({
  inventarioApi: {
    sesion: vi.fn().mockResolvedValue({ autenticado: false }),
    login: vi.fn(),
  },
}));

import { inventarioApi } from '../api/inventario';

describe('Login', () => {
  beforeEach(() => {
    vi.mocked(inventarioApi.login).mockReset();
    recargar.mockClear();
  });

  it('muestra error de servidor cuando el backend no responde (502)', async () => {
    vi.mocked(inventarioApi.login).mockRejectedValue({ status: 502, message: 'Bad Gateway' });
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText(/Contraseña/i), { target: { value: 'x' } });
    fireEvent.click(screen.getByRole('button', { name: /Ingresar/i }));
    expect(await screen.findByText(/No se pudo contactar al servidor/i)).toBeInTheDocument();
  });

  it('muestra error cuando las credenciales son inválidas', async () => {
    vi.mocked(inventarioApi.login).mockRejectedValue({
      status: 401,
      message: 'Unauthorized',
      data: { detail: 'Usuario o contraseña incorrectos.' },
    });
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'consultor' } });
    fireEvent.change(screen.getByLabelText(/Contraseña/i), { target: { value: 'mala' } });
    fireEvent.click(screen.getByRole('button', { name: /Ingresar/i }));
    expect(await screen.findByText(/incorrectos/i)).toBeInTheDocument();
  });

  it('tras login exitoso recarga sesión y navega al destino next=', async () => {
    vi.mocked(inventarioApi.login).mockResolvedValue({ autenticado: true, usuario: 'admin' });
    render(
      <MemoryRouter initialEntries={['/login?next=/rbac/inicio']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/rbac/inicio" element={<div>Tablero RBAC</div>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText(/Contraseña/i), { target: { value: 'ok' } });
    fireEvent.click(screen.getByRole('button', { name: /Ingresar/i }));
    await waitFor(() => expect(inventarioApi.login).toHaveBeenCalledWith('admin', 'ok'));
    expect(recargar).toHaveBeenCalled();
    expect(await screen.findByText('Tablero RBAC')).toBeInTheDocument();
  });
});

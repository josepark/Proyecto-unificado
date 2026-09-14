import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import RutaInicio from './RutaInicio';

vi.mock('../hooks/useSesion', () => ({
  useSesion: vi.fn(),
}));

import { useSesion } from '../hooks/useSesion';

function renderInicio() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<RutaInicio />} />
        <Route path="/login" element={<div>Página login</div>} />
        <Route path="/inventario/dashboard" element={<div>Dashboard inventario</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RutaInicio', () => {
  it('sin sesión redirige a login', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: false,
      modulos: [],
      cargando: false,
    });
    renderInicio();
    expect(await screen.findByText('Página login')).toBeInTheDocument();
  });

  it('cuenta sin proyectos muestra aviso', () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      modulos: [],
      cargando: false,
    });
    renderInicio();
    expect(screen.getByText(/Sin proyectos asignados/i)).toBeInTheDocument();
    expect(screen.getByText(/Administrador del SGSI/i)).toBeInTheDocument();
  });

  it('con proyectos redirige al primero asignado', async () => {
    vi.mocked(useSesion).mockReturnValue({
      autenticado: true,
      modulos: ['inventario'],
      cargando: false,
    });
    renderInicio();
    expect(await screen.findByText('Dashboard inventario')).toBeInTheDocument();
  });
});

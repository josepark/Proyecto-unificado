import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ActivoForm from './ActivoForm';

// Patrón para formularios de escritura (Activo/Rol/Usuario/Sistema/
// Datacenter/Diagrama comparten esta misma forma): simular fetch()
// distinguiendo por método HTTP, para poder probar tanto la carga inicial
// como el envío del formulario contra el mismo mock.
beforeEach(() => {
  global.fetch = vi.fn(async (url, opciones) => {
    const u = String(url);
    if (u.includes('/datacenters/')) {
      return ok({ count: 0, results: [] });
    }
    if (opciones?.method === 'POST' && u.endsWith('/activos/')) {
      const body = JSON.parse(opciones.body);
      if (!body.nombre) {
        return respuesta(400, { nombre: ['Este campo no puede estar en blanco.'] });
      }
      return respuesta(201, { id: 999, id_activo: 'RED-099', ...body });
    }
    return ok({});
  });
});

function ok(data) {
  return respuesta(200, data);
}
function respuesta(status, data) {
  return {
    ok: status < 400,
    status,
    headers: { get: () => 'application/json' },
    json: async () => data,
  };
}

function renderFormulario() {
  return render(
    <MemoryRouter initialEntries={['/inventario/activos/nuevo']}>
      <Routes>
        <Route path="/inventario/activos/nuevo" element={<ActivoForm />} />
        <Route path="/inventario/activos/:id" element={<div>DESTINO-FICHA</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ActivoForm (crear)', () => {
  it('muestra el error de validación del backend si falta el nombre', async () => {
    renderFormulario();
    fireEvent.submit(screen.getByRole('button', { name: /crear activo/i }).closest('form'));
    expect(await screen.findByText(/no puede estar en blanco/)).toBeInTheDocument();
    // y no navega — el formulario sigue visible
    expect(screen.getByRole('button', { name: /crear activo/i })).toBeInTheDocument();
  });

  it('crea el activo y navega a su ficha cuando el envío es válido', async () => {
    renderFormulario();
    fireEvent.change(screen.getByLabelText(/Nombre \*/), {
      target: { value: 'Servidor de pruebas' },
    });
    fireEvent.submit(screen.getByRole('button', { name: /crear activo/i }).closest('form'));

    await waitFor(() => expect(screen.getByText('DESTINO-FICHA')).toBeInTheDocument());
  });
});

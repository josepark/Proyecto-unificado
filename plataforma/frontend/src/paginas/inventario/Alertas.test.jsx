import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Alertas from './Alertas';

const FIXTURE = {
  total_consolidado: 12,
  resumen: { inventario: 4, inventario_criticas: 1, rbac: 3, riesgos: 5 },
  inventario: {
    total_alertas: 4,
    alertas_criticas: 1,
    grupos: [{
      clave: 'eol',
      titulo: 'Fin de soporte próximo',
      items: [{ id: 7, id_activo: 'SRV-01', nombre: 'Servidor', detalle: 'EOL vence', severidad: 'alto' }],
    }],
  },
  rbac: {
    disponible: true,
    pendientes_total: 3,
    desglose_pendientes: { proximos_vencimientos: 1, alertas_mfa: 2, roles_certificacion_vencida: 0, excepciones_vencidas: 0 },
  },
  riesgos: {
    disponible: true,
    total_vencidas: 2,
    total_por_vencer: 1,
    activos_sin_cobertura: 1,
    vulnerabilidades_criticas: 1,
    activos_comprometidos: 0,
  },
};

beforeEach(() => {
  global.fetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
    json: async () => FIXTURE,
  }));
});

describe('Alertas — centro unificado', () => {
  it('muestra KPIs por módulo y total consolidado', async () => {
    render(
      <MemoryRouter>
        <Alertas />
      </MemoryRouter>,
    );
    await screen.findByText('Centro de alertas');
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Total señales')).toBeInTheDocument();
    expect(screen.getByText('RBAC')).toBeInTheDocument();
  });

  it('enlaza alertas de inventario a la ficha del activo', async () => {
    render(
      <MemoryRouter>
        <Alertas />
      </MemoryRouter>,
    );
    const enlace = await screen.findByRole('link', { name: 'SRV-01' });
    expect(enlace).toHaveAttribute('href', '/inventario/activos/7');
  });

  it('muestra secciones de integración RBAC y Riesgos', async () => {
    render(
      <MemoryRouter>
        <Alertas />
      </MemoryRouter>,
    );
    await screen.findByText('Integración');
    expect(screen.getAllByText(/Matriz RBAC/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Gestión de Riesgos/i).length).toBeGreaterThan(0);
  });
});

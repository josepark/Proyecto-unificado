import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CampoCodigosCatalogo } from './CampoCodigosCatalogo';

const ITEMS = [
  { codigo: 'T1486', nombre: 'Data Encrypted for Impact', tipo: 'TE' },
  { codigo: 'T1190', nombre: 'Exploit Public-Facing Application', tipo: 'TE' },
  { codigo: 'TA0040', nombre: 'Impact', tipo: 'TA' },
];

describe('CampoCodigosCatalogo', () => {
  it('muestra sugerencias al escribir un prefijo MITRE', () => {
    const onChange = vi.fn();
    render(
      <CampoCodigosCatalogo
        label="Amenazas"
        value="T"
        onChange={onChange}
        items={ITEMS}
        filtrarItem={(a) => a.tipo === 'TE'}
      />,
    );
    fireEvent.focus(screen.getByLabelText(/Amenazas/i));
    expect(screen.getByText(/T1486/)).toBeInTheDocument();
    expect(screen.getByText(/T1190/)).toBeInTheDocument();
    expect(screen.queryByText(/TA0040/)).not.toBeInTheDocument();
  });

  it('inserta el código elegido en el valor', () => {
    const onChange = vi.fn();
    render(
      <CampoCodigosCatalogo
        label="Amenazas"
        value="T14"
        onChange={onChange}
        items={ITEMS}
        filtrarItem={(a) => a.tipo === 'TE'}
      />,
    );
    fireEvent.focus(screen.getByLabelText(/Amenazas/i));
    fireEvent.click(screen.getByRole('option', { name: /T1486/i }));
    expect(onChange).toHaveBeenCalledWith('T1486, ');
  });
});

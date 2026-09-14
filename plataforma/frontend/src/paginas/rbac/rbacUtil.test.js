import { describe, it, expect } from 'vitest';
import { modoFormularioRbac, ENLACES_ALERTAS_RBAC } from './rbacUtil';

describe('rbacUtil', () => {
  it('Consultor en ficha existente entra en solo lectura', () => {
    const m = modoFormularioRbac({ puedeEditar: false, soloLecturaRbac: true }, true);
    expect(m.soloLectura).toBe(true);
    expect(m.bloquearCreacion).toBe(false);
  });

  it('Consultor en ruta /nuevo bloquea creación', () => {
    const m = modoFormularioRbac({ puedeEditar: false, soloLecturaRbac: true }, false);
    expect(m.bloquearCreacion).toBe(true);
  });

  it('Dinamizador edita con normalidad', () => {
    const m = modoFormularioRbac({ puedeEditar: true, soloLecturaRbac: false }, true);
    expect(m.soloLectura).toBe(false);
    expect(m.bloqueado).toBe(false);
  });

  it('expone enlaces profundos de alertas', () => {
    expect(ENLACES_ALERTAS_RBAC.excepciones_vencidas).toContain('vencidas=1');
  });
});

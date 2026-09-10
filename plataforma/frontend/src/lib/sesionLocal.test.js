import { describe, expect, it, beforeEach } from 'vitest';
import { limpiarCredencialesLocales, sincronizarUsuarioActivo } from './sesionLocal';

describe('sesionLocal', () => {
  beforeEach(() => {
    limpiarCredencialesLocales();
  });

  it('limpia tokens al cerrar sesión', () => {
    localStorage.setItem('suiin_token', 'x');
    limpiarCredencialesLocales();
    expect(localStorage.getItem('suiin_token')).toBeNull();
  });

  it('descarta JWT al cambiar de usuario', () => {
    sincronizarUsuarioActivo('ana');
    localStorage.setItem('suiin_token', 'jwt-ana');
    sincronizarUsuarioActivo('pedro');
    expect(localStorage.getItem('suiin_token')).toBeNull();
    expect(sessionStorage.getItem('suiin_usuario_activo')).toBe('pedro');
  });
});

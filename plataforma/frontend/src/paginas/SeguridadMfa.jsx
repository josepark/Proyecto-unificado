import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { inventarioApi } from '../api/inventario';
import { useSesion } from '../hooks/useSesion';

export default function SeguridadMfa() {
  const { autenticado, cargando, usuario } = useSesion();
  const [mfaActivo, setMfaActivo] = useState(false);
  const [qr, setQr] = useState('');
  const [codigo, setCodigo] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [procesando, setProcesando] = useState(false);

  useEffect(() => {
    if (!autenticado) return;
    inventarioApi.mfaEstado()
      .then((d) => setMfaActivo(!!d.mfa_habilitado))
      .catch(() => {});
  }, [autenticado]);

  async function iniciarConfiguracion() {
    setError('');
    setMensaje('');
    setProcesando(true);
    try {
      const datos = await inventarioApi.mfaConfigurar();
      setQr(datos.qr_png_b64 || '');
      setMensaje('Escanee el código QR con su autenticador (Google Authenticator, Authy, etc.) e ingrese el código de 6 dígitos.');
    } catch (err) {
      setError(err.data?.detail || err.message || 'No se pudo iniciar la configuración.');
    } finally {
      setProcesando(false);
    }
  }

  async function activar() {
    setError('');
    setMensaje('');
    setProcesando(true);
    try {
      await inventarioApi.mfaActivar(codigo);
      setMfaActivo(true);
      setQr('');
      setCodigo('');
      setMensaje('MFA activado. El próximo inicio de sesión pedirá el código TOTP.');
    } catch (err) {
      setError(err.data?.detail || err.message || 'Código incorrecto.');
    } finally {
      setProcesando(false);
    }
  }

  async function desactivar() {
    setError('');
    setMensaje('');
    setProcesando(true);
    try {
      await inventarioApi.mfaDesactivar(codigo);
      setMfaActivo(false);
      setQr('');
      setCodigo('');
      setMensaje('MFA desactivado.');
    } catch (err) {
      setError(err.data?.detail || err.message || 'No se pudo desactivar.');
    } finally {
      setProcesando(false);
    }
  }

  if (cargando) {
    return <p className="login-cargando">Verificando sesión…</p>;
  }

  if (!autenticado) {
    return (
      <div className="modulo-restringido">
        <p>Debe iniciar sesión para configurar MFA.</p>
        <Link className="btn btn-primary" to="/login">Iniciar sesión</Link>
      </div>
    );
  }

  return (
    <div className="pagina-contenido" style={{ maxWidth: 520 }}>
      <h1>Autenticación en dos pasos (MFA)</h1>
      <p>Cuenta: <b>{usuario}</b></p>
      <p>
        Estado: {mfaActivo ? 'activo' : 'inactivo'}
      </p>

      {error ? <div className="login-error">{error}</div> : null}
      {mensaje ? <div className="aviso-info">{mensaje}</div> : null}

      {!mfaActivo && !qr ? (
        <button type="button" className="btn btn-primary" disabled={procesando} onClick={iniciarConfiguracion}>
          Configurar MFA
        </button>
      ) : null}

      {qr ? (
        <div>
          <img src={`data:image/png;base64,${qr}`} alt="Código QR MFA" width={200} height={200} />
          <label htmlFor="mfa-codigo">Código de verificación</label>
          <input
            id="mfa-codigo"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <button type="button" className="btn btn-primary" disabled={procesando} onClick={activar}>
            Activar MFA
          </button>
        </div>
      ) : null}

      {mfaActivo ? (
        <div>
          <label htmlFor="mfa-desactivar">Código actual para desactivar</label>
          <input
            id="mfa-desactivar"
            inputMode="numeric"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <button type="button" className="btn btn-secondary" disabled={procesando} onClick={desactivar}>
            Desactivar MFA
          </button>
        </div>
      ) : null}

      <p style={{ marginTop: '1.5rem' }}>
        <Link to="/">← Volver al inicio</Link>
      </p>
    </div>
  );
}

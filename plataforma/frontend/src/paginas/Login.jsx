import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { inventarioApi } from '../api/inventario';
import { useSesion } from '../hooks/useSesion';
import { rutaInicioModulos } from '../lib/modulosPlataforma';
import { sincronizarUsuarioActivo } from '../lib/sesionLocal';

function rutaSegura(next, modulos) {
  if (!next || !next.startsWith('/') || next.startsWith('//')) {
    return rutaInicioModulos(modulos, { autenticado: true });
  }
  return next;
}

export default function Login() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { recargar, autenticado, cargando, modulos } = useSesion();
  const destino = rutaSegura(params.get('next'), modulos);

  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [codigoMfa, setCodigoMfa] = useState('');
  const [pasoMfa, setPasoMfa] = useState(false);
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    inventarioApi.sesion().catch(() => {});
  }, []);

  useEffect(() => {
    if (!cargando && autenticado) navigate(destino, { replace: true });
  }, [autenticado, cargando, destino, navigate]);

  async function enviar(evento) {
    evento.preventDefault();
    setError('');
    setEnviando(true);
    try {
      const sesionLogin = await inventarioApi.login(
        usuario,
        clave,
        pasoMfa ? codigoMfa : undefined,
      );
      sincronizarUsuarioActivo(sesionLogin.usuario || usuario.trim());
      await recargar();
      navigate(rutaSegura(params.get('next'), sesionLogin.modulos), { replace: true });
    } catch (err) {
      if (err.data?.requiere_mfa) {
        setPasoMfa(true);
        setError('Introduzca el código de su autenticador.');
      } else if (err.status === 429) {
        setError('Acceso bloqueado temporalmente por demasiados intentos fallidos.');
      } else if (err.status >= 500 || !err.status) {
        setError(
          'No se pudo contactar al servidor de autenticación (error '
          + (err.status || 'de red')
          + '). Verifique que los contenedores estén en ejecución: docker compose ps',
        );
      } else {
        setError(err.data?.detail || err.message || 'Usuario o contraseña incorrectos.');
      }
    } finally {
      setEnviando(false);
    }
  }

  if (cargando || autenticado) {
    return (
      <div className="login-pagina">
        <p className="login-cargando">Verificando sesión…</p>
      </div>
    );
  }

  return (
    <div className="login-pagina">
      <div className="login-caja">
        <div className="login-cabecera">
          <div className="anillo">
            <span>SU</span>
          </div>
          <div>
            <h1>Soluciones SUIIN</h1>
            <div className="sub">Inventario de Activos SGSI · Matriz RBAC · Riesgos</div>
          </div>
        </div>

        <form className="login-formulario" onSubmit={enviar}>
          {error ? <div className="login-error">{error}</div> : null}
          {!pasoMfa ? (
            <>
              <label htmlFor="login-usuario">Usuario</label>
              <input
                id="login-usuario"
                name="username"
                autoComplete="username"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                required
              />
              <label htmlFor="login-clave">Contraseña</label>
              <input
                id="login-clave"
                name="password"
                type="password"
                autoComplete="current-password"
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                required
              />
            </>
          ) : (
            <>
              <p className="login-mfa-aviso">Verificación en dos pasos para <b>{usuario}</b></p>
              <label htmlFor="login-mfa">Código del autenticador</label>
              <input
                id="login-mfa"
                name="codigo_mfa"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={codigoMfa}
                onChange={(e) => setCodigoMfa(e.target.value)}
                required
              />
              <button
                type="button"
                className="btn btn-link login-volver"
                onClick={() => { setPasoMfa(false); setCodigoMfa(''); setError(''); }}
              >
                ← Volver a usuario y contraseña
              </button>
            </>
          )}
          <button type="submit" className="btn btn-primary login-enviar" disabled={enviando}>
            {enviando ? 'Ingresando…' : pasoMfa ? 'Verificar código' : 'Ingresar'}
          </button>
        </form>

        <div className="login-pie">
          Acceso restringido · Roles: Consultor · Dinamizador · Administrador
          <br />
          <Link to="/inventario/panel-ejecutivo">← Panel ejecutivo (consulta pública)</Link>
        </div>
      </div>
    </div>
  );
}

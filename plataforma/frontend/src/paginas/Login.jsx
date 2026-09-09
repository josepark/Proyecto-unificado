import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { inventarioApi } from '../api/inventario';
import { useSesion } from '../hooks/useSesion';

function rutaSegura(next) {
  if (!next || !next.startsWith('/') || next.startsWith('//')) return '/inventario/dashboard';
  return next;
}

export default function Login() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { recargar, autenticado, cargando } = useSesion();
  const destino = rutaSegura(params.get('next'));

  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
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
      await inventarioApi.login(usuario, clave);
      await recargar();
      // Si el módulo de riesgos sigue montado (p. ej. login en modal futuro),
      // o tras volver a /gestion-riesgos, dispara SSO sin esperar otro ciclo.
      window.dispatchEvent(new CustomEvent('suiin-sesion-plataforma'));
      navigate(destino, { replace: true });
    } catch (err) {
      if (err.status === 429) {
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
          <button type="submit" className="btn btn-primary login-enviar" disabled={enviando}>
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>

        <div className="login-pie">
          Acceso restringido · Roles: Consultor · Dinamizador · Administrador
          <br />
          <Link to="/inventario/dashboard">← Volver al tablero (solo consulta)</Link>
        </div>
      </div>
    </div>
  );
}

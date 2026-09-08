import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import endpoints, { consultarSesionInventario } from "../api/endpoints";

const AuthContext = createContext(null);

const INTERVALO_REVALIDACION_MS = 3 * 60 * 1000;
const EVENTO_SESION_PLATAFORMA = "suiin-sesion-plataforma";
const ROLES_ESCRITURA = new Set(["Dinamizador", "Administrador"]);

function guardarCredenciales(token, esquema, origen = null) {
  localStorage.setItem("suiin_token", token);
  localStorage.setItem("suiin_auth_scheme", esquema);
  if (origen) localStorage.setItem("suiin_auth_origen", origen);
  else localStorage.removeItem("suiin_auth_origen");
}

function borrarCredenciales() {
  localStorage.removeItem("suiin_token");
  localStorage.removeItem("suiin_auth_scheme");
  localStorage.removeItem("suiin_auth_origen");
}

function limpiarSiEraSSO() {
  const esquemaActual = localStorage.getItem("suiin_auth_scheme");
  const origenActual = localStorage.getItem("suiin_auth_origen");
  if (!localStorage.getItem("suiin_token") || (esquemaActual === "Bearer" && origenActual === "sso")) {
    borrarCredenciales();
    return true;
  }
  return false;
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function aplicarPerfil(data, setUser, setRoles, setPuedeEditar) {
  const userRoles = data.roles || [];
  setUser({ username: data.username, is_staff: data.is_staff ?? userRoles.includes("Administrador") });
  setRoles(userRoles);
  setPuedeEditar(data.puede_editar ?? (!userRoles.length || userRoles.some((r) => ROLES_ESCRITURA.has(r))));
}

export function AuthProvider({
  children,
  plataformaAutenticada = false,
  sesionCargando = false,
  unificado = false,
}) {
  const [user, setUser] = useState(null);
  const [roles, setRoles] = useState([]);
  const [puedeEditar, setPuedeEditar] = useState(true);
  const [checking, setChecking] = useState(true);
  const ssoEnVuelo = useRef(null);

  const intentarSSO = useCallback(
    async ({ verificarSesion = unificado } = {}) => {
      if (ssoEnVuelo.current) return ssoEnVuelo.current;

      const promesa = (async () => {
        if (verificarSesion) {
          const sesion = await consultarSesionInventario();
          if (!sesion.autenticado) {
            if (limpiarSiEraSSO()) setUser(null);
            return false;
          }
        }

        try {
          const data = await endpoints.ssoJWT();
          guardarCredenciales(data.token, "Bearer", "sso");
          aplicarPerfil(data, setUser, setRoles, setPuedeEditar);
          return true;
        } catch {
          if (limpiarSiEraSSO()) setUser(null);
          return false;
        }
      })().finally(() => {
        ssoEnVuelo.current = null;
      });

      ssoEnVuelo.current = promesa;
      return promesa;
    },
    [unificado],
  );

  const sincronizarSSO = useCallback(
    async (reintentos = 1) => {
      for (let i = 0; i < reintentos; i += 1) {
        const ok = await intentarSSO();
        if (ok) return true;
        if (i < reintentos - 1) await esperar(400);
      }
      return false;
    },
    [intentarSSO],
  );

  useEffect(() => {
    if (unificado && sesionCargando) return;

    let cancelado = false;

    async function bootstrap() {
      const token = localStorage.getItem("suiin_token");
      const esquema = localStorage.getItem("suiin_auth_scheme");
      const origen = localStorage.getItem("suiin_auth_origen");

      if (token && !(esquema === "Bearer" && origen === "sso")) {
        try {
          const res = await endpoints.me();
          if (!cancelado) aplicarPerfil(res.data, setUser, setRoles, setPuedeEditar);
        } catch {
          if (!cancelado) {
            borrarCredenciales();
            setRoles([]);
            setPuedeEditar(true);
          }
        } finally {
          if (!cancelado) setChecking(false);
        }
        return;
      }

      if (unificado && !plataformaAutenticada) {
        if (origen === "sso") {
          borrarCredenciales();
          setUser(null);
        }
        if (!cancelado) setChecking(false);
        return;
      }

      // Restaurar usuario desde JWT SSO guardado mientras se revalida — evita
      // pantalla de "requiere sesión" al volver de RBAC/Inventario al módulo.
      if (token && esquema === "Bearer" && origen === "sso" && unificado && plataformaAutenticada) {
        try {
          const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
          if (payload.username) {
            aplicarPerfil(
              { username: payload.username, roles: payload.roles || [], is_staff: payload.roles?.includes("Administrador") },
              setUser,
              setRoles,
              setPuedeEditar,
            );
          }
        } catch {
          // sigue abajo con sincronizarSSO
        }
      }

      const reintentos = unificado && plataformaAutenticada ? 2 : 1;
      try {
        await sincronizarSSO(reintentos);
      } catch {
        // No bloquear la UI si falla la sincronización SSO (p. ej. red puntual).
      } finally {
        if (!cancelado) setChecking(false);
      }
    }

    bootstrap();
    return () => {
      cancelado = true;
    };
  }, [sincronizarSSO, unificado, sesionCargando, plataformaAutenticada]);

  useEffect(() => {
    if (!unificado) return;
    function alActualizarSesionPlataforma() {
      sincronizarSSO(2);
    }
    window.addEventListener(EVENTO_SESION_PLATAFORMA, alActualizarSesionPlataforma);
    return () => window.removeEventListener(EVENTO_SESION_PLATAFORMA, alActualizarSesionPlataforma);
  }, [sincronizarSSO, unificado]);

  useEffect(() => {
    const id = setInterval(() => {
      const esquema = localStorage.getItem("suiin_auth_scheme");
      const origen = localStorage.getItem("suiin_auth_origen");
      if (esquema === "Bearer" && origen === "sso") intentarSSO();
    }, INTERVALO_REVALIDACION_MS);
    return () => clearInterval(id);
  }, [intentarSSO]);

  const login = useCallback(async (username, password) => {
    try {
      const data = await endpoints.ssoJWTLogin(username, password);
      guardarCredenciales(data.token, "Bearer");
      aplicarPerfil(data, setUser, setRoles, setPuedeEditar);
      return;
    } catch {
      // Sigue con login propio de riesgos.
    }

    const res = await endpoints.login(username, password);
    guardarCredenciales(res.data.token, "Token");
    aplicarPerfil({ ...res.data, roles: [], puede_editar: true }, setUser, setRoles, setPuedeEditar);
  }, []);

  const logout = useCallback(() => {
    const esquema = localStorage.getItem("suiin_auth_scheme");
    if (esquema === "Token") {
      endpoints.logout().catch(() => {});
    }
    borrarCredenciales();
    setUser(null);
    setRoles([]);
    setPuedeEditar(true);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        roles,
        puedeEditar,
        checking,
        isAuthenticated: !!user,
        plataformaAutenticada: unificado ? plataformaAutenticada : false,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}

export { EVENTO_SESION_PLATAFORMA };

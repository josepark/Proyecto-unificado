import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import endpoints from "../api/endpoints";

const AuthContext = createContext(null);

// Cada tres minutos, un JWT obtenido por sesión única silenciosa se
// re-verifica contra el Inventario (no solo su propia validez) — ver
// justificación completa más abajo, en el useEffect que lo usa.
const INTERVALO_REVALIDACION_MS = 3 * 60 * 1000;

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

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const revalidando = useRef(false);

  const intentarSSO = useCallback(() => {
    if (revalidando.current) return Promise.resolve(); // evita solapes si el intervalo dispara mientras otro sigue en vuelo
    revalidando.current = true;
    return endpoints
      .ssoJWT()
      .then((res) => {
        guardarCredenciales(res.data.token, "Bearer", "sso");
        setUser({ username: res.data.username, is_staff: res.data.roles?.includes("Administrador") ?? false });
      })
      .catch(() => {
        // Solo se descartan credenciales si eran de sesión única silenciosa
        // (origen "sso") — un login manual (cuenta propia de riesgos, o
        // credenciales del Inventario tecleadas a mano) no depende de que la
        // cookie del Inventario siga viva en este momento, y no debe perderse
        // solo porque este chequeo de fondo no encontró esa cookie.
        const esquemaActual = localStorage.getItem("suiin_auth_scheme");
        const origenActual = localStorage.getItem("suiin_auth_origen");
        if (!localStorage.getItem("suiin_token") || (esquemaActual === "Bearer" && origenActual === "sso")) {
          borrarCredenciales();
          setUser(null);
        }
      })
      .finally(() => {
        revalidando.current = false;
      });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("suiin_token");
    const esquema = localStorage.getItem("suiin_auth_scheme");
    const origen = localStorage.getItem("suiin_auth_origen");

    if (token && !(esquema === "Bearer" && origen === "sso")) {
      // Cuenta propia de riesgos, o sesión única obtenida a mano con
      // credenciales del Inventario (login() más abajo) — ninguna de las dos
      // depende de la cookie del Inventario en este instante, se valida solo
      // la validez propia del token.
      endpoints
        .me()
        .then((res) => setUser(res.data))
        .catch(() => borrarCredenciales())
        .finally(() => setChecking(false));
      return;
    }

    // Sin credenciales guardadas, o un JWT que si vino de sesión única
    // silenciosa: en ambos casos se re-verifica contra el Inventario ahora
    // mismo, no solo contra la validez propia del JWT ya guardado.
    //
    // Hallazgo real (captura del usuario, 2026-08-25): cerrar sesión en el
    // Inventario no cerraba la de riesgos — el JWT silencioso, todavía sin
    // vencer, seguía validando correctamente contra /api/auth/me/ (que solo
    // mira la firma y el vencimiento del token, no si la cookie que lo
    // originó sigue viva), así que el panel embebido seguía mostrando el
    // menú completo con la sesión vieja después de cerrar sesión arriba.
    intentarSSO().finally(() => setChecking(false));
  }, [intentarSSO]);

  useEffect(() => {
    // Mientras la pestaña/iframe de riesgos queda abierta sin recargar (caso
    // normal en el panel embebido: el Inventario no destruye el iframe al
    // cambiar de pestaña, solo lo oculta — ver Layout.jsx), el chequeo de
    // montaje de arriba no vuelve a correr solo. Este intervalo cubre cerrar
    // sesión en el Inventario en OTRA pestaña mientras esta sigue abierta.
    const id = setInterval(() => {
      const esquema = localStorage.getItem("suiin_auth_scheme");
      const origen = localStorage.getItem("suiin_auth_origen");
      if (esquema === "Bearer" && origen === "sso") intentarSSO();
    }, INTERVALO_REVALIDACION_MS);
    return () => clearInterval(id);
  }, [intentarSSO]);

  const login = useCallback(async (username, password) => {
    // Se intenta primero como cuenta del Inventario (mismo usuario y clave que
    // /login/ de la plataforma) — es el caso normal en el despliegue
    // unificado, y evita que quien ya tiene cuenta ahí necesite crear otra
    // aparte solo para riesgos. Si el Inventario no está disponible (riesgos
    // corriendo de forma independiente) o esas credenciales no existen ahí,
    // se cae al login propio de riesgos sin que la persona tenga que elegir
    // cuál usar — simplemente funciona con cualquiera de las dos cuentas.
    try {
      const res = await endpoints.ssoJWTLogin(username, password);
      // origen null (no "sso"): esto fue una entrada manual de credenciales,
      // no el chequeo silencioso — no debe perderse solo porque más tarde no
      // haya cookie del Inventario en este navegador (ver intentarSSO).
      guardarCredenciales(res.data.token, "Bearer");
      setUser({ username: res.data.username, is_staff: res.data.roles?.includes("Administrador") ?? false });
      return;
    } catch {
      // Sigue abajo con el login propio de riesgos — sin mostrar este error
      // todavía, para no confundir con un problema que en realidad no aplica
      // si la persona sí tiene cuenta propia de riesgos.
    }

    const res = await endpoints.login(username, password);
    guardarCredenciales(res.data.token, "Token");
    setUser({ username: res.data.username, is_staff: res.data.is_staff });
  }, []);

  const logout = useCallback(() => {
    const esquema = localStorage.getItem("suiin_auth_scheme");
    if (esquema === "Token") {
      endpoints.logout().catch(() => {}); // invalida el token propio en el servidor
    }
    // Un JWT de sesión única no se "cierra" del lado de riesgos — expira solo
    // y, mientras tanto, cerrar sesión acá simplemente deja de usarlo; para
    // cerrar la sesión de verdad hay que hacerlo en el Inventario (lo cual,
    // desde este cambio, este mismo panel detecta solo en un rato).
    borrarCredenciales();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, checking, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}

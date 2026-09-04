import { useState } from "react";
import { useAuth } from "../context/AuthContext";

/**
 * Envuelve manejadores de eventos que requieren sesión iniciada. Si el usuario no
 * está autenticado, abre el modal de login en vez de ejecutar la acción.
 *
 *   const { guard, loginOpen, setLoginOpen } = useAuthGuard();
 *   <button onClick={guard(() => abrirFormulario())}>+ Nuevo</button>
 *   <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
 */
export function useAuthGuard() {
  const { isAuthenticated } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);

  function guard(action) {
    return (...args) => {
      if (!isAuthenticated) {
        setLoginOpen(true);
        return;
      }
      return action(...args);
    };
  }

  return { guard, loginOpen, setLoginOpen, isAuthenticated };
}

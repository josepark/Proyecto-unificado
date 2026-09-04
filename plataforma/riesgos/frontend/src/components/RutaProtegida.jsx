import { Outlet } from "react-router-dom";
import { Lock, LogIn } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import LoginModal from "./LoginModal";

// Mismo cálculo que Layout.jsx (no se comparte como prop para no acoplar
// ambos componentes innecesariamente — es una lectura de la URL, no estado).
const EMBEBIDO = new URLSearchParams(window.location.search).get("embed") === "1";

/**
 * Envuelve las rutas que deben quedar bloqueadas sin sesión — mismo criterio
 * de acceso que ya usa RBAC en el Inventario ("La Matriz de Control de Acceso
 * requiere una sesión con rol Dinamizador o Administrador"). El Panel general
 * (Dashboard) queda FUERA de este envoltorio a propósito: es la única página
 * navegable en modo consulta sin iniciar sesión.
 *
 * Esto es solo la capa de navegación/UX — el backend
 * (EscrituraSegunRolDePlataforma) sigue siendo la autoridad real sobre qué se
 * puede leer o escribir; esta pantalla evita que alguien sin sesión llegue
 * por URL directa a una página que el menú ya no le muestra.
 */
export default function RutaProtegida() {
  const { isAuthenticated } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);

  if (!isAuthenticated) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center px-8 py-24 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-base-850/80 border border-base-700/60">
          <Lock className="h-5 w-5 text-base-300" />
        </div>
        <h2 className="mt-4 text-base font-semibold text-base-100">Esta sección requiere sesión</h2>
        {EMBEBIDO ? (
          // Misma razón que en Layout.jsx: dentro del Inventario es la misma
          // sesión (JWT único) — si todavía no se sincronizó, un botón de
          // "Iniciar sesión" aparte aquí daría la impresión equivocada de que
          // este módulo pide credenciales propias.
          <p className="mt-2 text-[13px] leading-relaxed text-base-300">
            La sesión del Inventario todavía no se ha sincronizado con este panel.
            Si acaba de iniciar sesión, recargue la página; si el problema sigue,
            revise la sesión desde el Inventario.
          </p>
        ) : (
          <>
            <p className="mt-2 text-[13px] leading-relaxed text-base-300">
              Inicie sesión para ver Activos, Vulnerabilidades, Riesgos contextuales,
              Campañas Red Team, Plan de tratamiento, Cumplimiento ISO 27001 y Catálogos.
              El Panel general sigue disponible sin sesión, en modo consulta.
            </p>
            <button
              onClick={() => setLoginOpen(true)}
              className="mt-5 flex items-center gap-2 rounded-lg bg-cric-green-600 px-4 py-2 text-[13px] font-medium text-base-100 transition-colors hover:bg-cric-green-500"
            >
              <LogIn className="h-3.5 w-3.5" />
              Iniciar sesión
            </button>
            <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
          </>
        )}
      </div>
    );
  }

  return <Outlet />;
}

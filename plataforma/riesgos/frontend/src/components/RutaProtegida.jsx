import { Outlet, Link, useLocation } from "react-router-dom";
import { Lock, LogIn } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { usePlataforma } from "../context/PlataformaContext";
import LoginModal from "./LoginModal";

function esModoEmbebido(anidado) {
  if (anidado) return true;
  return new URLSearchParams(window.location.search).get("embed") === "1";
}

/**
 * Envuelve las rutas que deben quedar bloqueadas sin sesión — mismo criterio
 * de acceso que ya usa RBAC en el Inventario ("La Matriz de Control de Acceso
 * requiere una sesión con rol Dinamizador o Administrador"). El Panel general
 * (Dashboard) queda FUERA de este envoltorio a propósito: es la única página
 * navegable en modo consulta sin iniciar sesión.
 */
export default function RutaProtegida() {
  const { isAuthenticated, checking, plataformaAutenticada } = useAuth();
  const { anidado } = usePlataforma();
  const ubicacion = useLocation();
  const [loginOpen, setLoginOpen] = useState(false);
  const embebido = esModoEmbebido(anidado);
  const sincronizando = embebido && plataformaAutenticada && (checking || !isAuthenticated);
  const rutaTrasLogin = `${ubicacion.pathname}${ubicacion.search}`;

  if (sincronizando) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center px-8 py-24 text-center">
        <p className="text-[13px] text-base-300">Sincronizando sesión con el Inventario…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center px-8 py-24 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-base-850/80 border border-base-700/60">
          <Lock className="h-5 w-5 text-base-300" />
        </div>
        <h2 className="mt-4 text-base font-semibold text-base-100">Esta sección requiere sesión</h2>
        {embebido ? (
          <p className="mt-2 text-[13px] leading-relaxed text-base-300">
            Use{' '}
            <Link
              to={`/login?next=${encodeURIComponent(rutaTrasLogin)}`}
              className="text-cric-green-400 hover:underline"
            >
              Iniciar sesión
            </Link>{' '}
            en la barra superior para ver Activos, Vulnerabilidades y el resto de la gestión.
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

import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard, ShieldAlert, ServerCog, Bug, Users, ClipboardList, Radar, LogIn, LogOut, UserCircle2, ShieldCheck, ArrowLeftCircle, ListChecks,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePlataforma, useRiesgosTo } from "../context/PlataformaContext";
import LoginModal from "./LoginModal";

const ENLACE_PLATAFORMA =
  import.meta.env.BASE_URL !== "/" && !import.meta.env.VITE_PLATAFORMA_UNIFICADA ? "/" : null;

function esModoEmbebido(anidado) {
  if (anidado) return true;
  return new URLSearchParams(window.location.search).get("embed") === "1";
}

const NAV_ITEMS = [
  { segment: "", label: "Panel general", icon: LayoutDashboard, end: true },
  { segment: "activos", label: "Activos", icon: ServerCog },
  { segment: "vulnerabilidades", label: "Vulnerabilidades", icon: Bug },
  { segment: "riesgos-contextuales", label: "Riesgos contextuales", icon: Users },
  { segment: "red-team", label: "Campañas Red Team", icon: Radar },
  { segment: "plan-tratamiento", label: "Plan de tratamiento", icon: ClipboardList },
  { segment: "cumplimiento", label: "Cumplimiento ISO 27001", icon: ShieldCheck },
  { segment: "catalogos", label: "Catálogos", icon: ListChecks },
];

/** Enlaces del menú siempre desde la raíz del módulo — evita rutas rotas tipo
 * /gestion-riesgos/activos/vulnerabilidades al navegar desde un detalle. */
function EnlaceNav({ segment, label, icon: Icon, end }) {
  const to = useRiesgosTo(segment);
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors ${
          isActive
            ? "bg-cric-green-600/20 text-cric-green-400"
            : "text-base-300 hover:bg-base-800 hover:text-base-100"
        }`
      }
    >
      <Icon className="h-4 w-4" strokeWidth={2} />
      {label}
    </NavLink>
  );
}

export default function Layout() {
  const { user, isAuthenticated, logout, checking, plataformaAutenticada } = useAuth();
  const { anidado } = usePlataforma();
  const [loginOpen, setLoginOpen] = useState(false);
  const EMBEBIDO = esModoEmbebido(anidado);
  const sincronizandoSesion = EMBEBIDO && plataformaAutenticada && checking && !isAuthenticated;

  // Mismo criterio de acceso que ya usa RBAC: sin sesión, solo se navega el
  // Panel general (modo consulta) — el resto del menú aparece recién con la
  // sesión iniciada. Esto es solo visibilidad de navegación, no el permiso
  // real: el backend (EscrituraSegunRolDePlataforma) sigue siendo quien
  // decide qué se puede escribir, esto solo cambia qué es cómodo de
  // descubrir desde el menú antes de iniciar sesión.
  const itemsVisibles = isAuthenticated ? NAV_ITEMS : NAV_ITEMS.filter((item) => item.end);

  const asideClass = EMBEBIDO
    ? "flex w-52 shrink-0 flex-col border-r border-base-700/60 bg-base-900/95"
    : "fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-base-700/60 bg-base-900/80 backdrop-blur-md";

  return (
    <div className={EMBEBIDO ? "flex min-h-[68vh]" : "flex min-h-screen"}>
      <aside className={asideClass}>
        {EMBEBIDO && (
          <div className="border-b border-base-700/60 px-4 py-3">
            <p className="font-display text-[12px] font-semibold text-base-100">Gestión de Riesgos</p>
            <p className="text-[10px] text-base-300">Plan de Tratamiento (PTR)</p>
          </div>
        )}
        {!EMBEBIDO && (
          <div className="flex items-center gap-2.5 border-b border-base-700/60 px-5 py-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cric-green-600">
              <ShieldAlert className="h-5 w-5 text-base-100" strokeWidth={2} />
            </div>
            <div className="leading-tight">
              <p className="font-display text-[13px] font-semibold text-base-100">SUIIN-SGSI</p>
              <p className="text-[11px] text-base-300">Gestión de Riesgos</p>
            </div>
          </div>
        )}

        <nav className="flex-1 space-y-1 px-3 py-4">
          {itemsVisibles.map(({ segment, label, icon, end }) => (
            <EnlaceNav key={segment || "panel"} segment={segment} label={label} icon={icon} end={end} />
          ))}
          {!isAuthenticated && (
            <p className="px-3 pt-3 text-[11px] leading-relaxed text-base-300/60">
              {sincronizandoSesion ? (
                'Sincronizando sesión con el Inventario…'
              ) : EMBEBIDO ? (
                <>
                  Use{' '}
                  <Link
                    to={`/login?next=${encodeURIComponent('/gestion-riesgos')}`}
                    className="text-cric-green-400 hover:underline"
                  >
                    Iniciar sesión
                  </Link>{' '}
                  en la barra superior para ver Activos, Vulnerabilidades y el resto de la gestión.
                </>
              ) : (
                'Inicie sesión para ver Activos, Vulnerabilidades y el resto de la gestión.'
              )}
            </p>
          )}
        </nav>

        {/* Dentro del Inventario (embebido), la sesión ya se ve y se
            controla arriba, en la barra del propio Inventario ("Sesión:
            admin (roles) · Salir") — mostrar acá TAMBIÉN "admin" con su
            propio botón de "Cerrar sesión" (con o sin sesión activa) seguía
            dando la impresión de dos inicios de sesión separados, aunque
            técnicamente sea la misma (JWT único). Ya se había quitado el
            botón de "Iniciar sesión" duplicado sin sesión; con sesión activa
            quedaba el mismo problema al revés — "admin" + un segundo botón
            de "Salir" aparte. En modo embebido, este bloque completo ya no
            se muestra en ningún caso; solo aparece en acceso directo
            (`/riesgos/` fuera del Inventario), donde sí es la única forma
            de ver/cerrar la sesión. */}
        {!EMBEBIDO && (
          <div className="border-t border-base-700/60 px-4 py-4">
            {isAuthenticated ? (
              <div className="flex items-center justify-between rounded-lg bg-base-850/60 px-3 py-2">
                <span className="flex items-center gap-2 text-[12px] text-base-100">
                  <UserCircle2 className="h-4 w-4 text-cric-green-400" />
                  {user.username}
                </span>
                <button onClick={logout} className="text-base-300 hover:text-[#e0475a]" title="Cerrar sesión">
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setLoginOpen(true)}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-base-700/60 px-3 py-2 text-[12px] font-medium text-base-300 transition-colors hover:border-cric-green-500/50 hover:text-cric-green-400"
              >
                <LogIn className="h-3.5 w-3.5" />
                Iniciar sesión
              </button>
            )}
            <p className="mt-3 text-[11px] leading-relaxed text-base-300/70">
              Consejo Regional Indígena del Cauca
              <br />
              SUIIN
            </p>
            {ENLACE_PLATAFORMA && (
              <a
                href={ENLACE_PLATAFORMA}
                className="mt-3 flex items-center gap-1.5 text-[11px] text-base-300/70 hover:text-cric-green-400"
              >
                <ArrowLeftCircle className="h-3.5 w-3.5" />
                Volver a Soluciones SUIIN
              </a>
            )}
          </div>
        )}
      </aside>

      <div className={EMBEBIDO ? "min-w-0 flex-1 overflow-x-auto" : "flex-1 pl-64"}>
        <Outlet />
      </div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}

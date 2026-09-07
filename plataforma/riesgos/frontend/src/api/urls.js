/** Resuelve bases de API para la SPA unificada o para riesgos standalone. */

export function enPlataformaUnificada() {
  const flag = import.meta.env.VITE_PLATAFORMA_UNIFICADA;
  if (flag && flag !== "0" && flag !== "false") return true;
  if (typeof window !== "undefined") {
    return window.location.pathname.startsWith("/gestion-riesgos");
  }
  return false;
}

export function resolverBaseRiesgos() {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  if (enPlataformaUnificada()) return "/riesgos/api";
  return "http://localhost:8000/api";
}

export function resolverBaseInventario() {
  if (import.meta.env.VITE_INVENTARIO_BASE_URL) return import.meta.env.VITE_INVENTARIO_BASE_URL;
  if (enPlataformaUnificada()) return "/api";
  return "http://localhost:8000/api";
}

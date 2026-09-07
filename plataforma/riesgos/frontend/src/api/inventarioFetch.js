/** Peticiones al Inventario con fetch + credentials (igual que la SPA unificada). */
import { inventarioBaseURL } from "./client";

export function leerCookie(nombre) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function peticionInventario(ruta, opciones = {}) {
  const headers = { ...(opciones.headers || {}) };
  if (opciones.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const respuesta = await fetch(`${inventarioBaseURL}${ruta}`, {
    ...opciones,
    credentials: "same-origin",
    headers,
  });

  if (!respuesta.ok) {
    let cuerpo = null;
    try {
      cuerpo = await respuesta.json();
    } catch {
      cuerpo = null;
    }
    const error = new Error(cuerpo?.detail || respuesta.statusText);
    error.status = respuesta.status;
    error.data = cuerpo;
    throw error;
  }

  if (respuesta.status === 204) return null;
  const tipo = respuesta.headers.get("content-type") || "";
  return tipo.includes("application/json") ? respuesta.json() : respuesta.text();
}

export async function consultarSesionInventario() {
  try {
    return await peticionInventario("/sesion/");
  } catch {
    return { autenticado: false };
  }
}

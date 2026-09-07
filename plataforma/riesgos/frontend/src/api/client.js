import axios from "axios";

// En desarrollo, Vite corre en :5173 y Django en :8000 (ver README).
// En producción, sirva el frontend detrás del mismo dominio/proxy que /api/
// o defina VITE_API_BASE_URL en un archivo .env.
const baseURL =
  import.meta.env.VITE_API_BASE_URL
  || (import.meta.env.VITE_PLATAFORMA_UNIFICADA ? "/riesgos/api" : "http://localhost:8000/api");
export { baseURL as apiBaseURL };

export const inventarioBaseURL =
  import.meta.env.VITE_INVENTARIO_BASE_URL
  || (import.meta.env.VITE_PLATAFORMA_UNIFICADA ? "/api" : "http://localhost:8000/api");

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// Adjunta el esquema y valor guardados (Token propio de riesgos, o Bearer del
// JWT de plataforma tras una sesión única exitosa) a cada request saliente.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("suiin_token");
  const esquema = localStorage.getItem("suiin_auth_scheme") || "Token";
  if (token) {
    config.headers.Authorization = `${esquema} ${token}`;
  }
  return config;
});

export default api;

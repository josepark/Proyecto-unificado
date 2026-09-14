import axios from "axios";
import { resolverBaseInventario, resolverBaseRiesgos } from "./urls";

const baseURL = resolverBaseRiesgos();
export { baseURL as apiBaseURL };

export const inventarioBaseURL = resolverBaseInventario();

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

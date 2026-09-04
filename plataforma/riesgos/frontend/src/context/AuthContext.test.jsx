import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import endpoints from "../api/endpoints";

// endpoints.js hace llamadas HTTP reales (axios) — se reemplaza todo el
// módulo por dobles de prueba controlados, no se golpea ninguna red real.
vi.mock("../api/endpoints", () => ({
  default: {
    ssoJWT: vi.fn(),
    ssoJWTLogin: vi.fn(),
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

/** Componente mínimo que expone el contexto para poder leerlo/accionarlo desde las pruebas. */
function SondaAuth() {
  const { user, checking, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="checking">{String(checking)}</span>
      <span data-testid="autenticado">{String(isAuthenticated)}</span>
      <span data-testid="usuario">{user?.username ?? "ninguno"}</span>
      <button onClick={() => login("ana", "clave")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderizar() {
  return render(
    <AuthProvider>
      <SondaAuth />
    </AuthProvider>
  );
}

async function esperarQueTermineDeVerificar() {
  await waitFor(() => expect(screen.getByTestId("checking")).toHaveTextContent("false"));
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("AuthProvider — sin credenciales guardadas", () => {
  it("intenta sesión única silenciosa (SSO) al montar", async () => {
    endpoints.ssoJWT.mockResolvedValue({ data: { token: "jwt-1", username: "ana", roles: ["Consultor"] } });

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(endpoints.ssoJWT).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("usuario")).toHaveTextContent("ana");
    expect(localStorage.getItem("suiin_auth_scheme")).toBe("Bearer");
    expect(localStorage.getItem("suiin_auth_origen")).toBe("sso");
  });

  it("si el SSO falla (sin sesión en el Inventario), queda sin autenticar sin mostrar error", async () => {
    endpoints.ssoJWT.mockRejectedValue(new Error("401"));

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    expect(localStorage.getItem("suiin_token")).toBeNull();
  });
});

describe("AuthProvider — credencial Token guardada (cuenta propia de riesgos)", () => {
  beforeEach(() => {
    localStorage.setItem("suiin_token", "tok-propio");
    localStorage.setItem("suiin_auth_scheme", "Token");
  });

  it("valida contra /api/auth/me/ y NO intenta SSO", async () => {
    endpoints.me.mockResolvedValue({ data: { username: "consultor_local", is_staff: false } });

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(endpoints.me).toHaveBeenCalledTimes(1);
    expect(endpoints.ssoJWT).not.toHaveBeenCalled();
    expect(screen.getByTestId("usuario")).toHaveTextContent("consultor_local");
  });

  it("si el token propio ya no es válido, se descarta sin caer al SSO", async () => {
    endpoints.me.mockRejectedValue(new Error("401"));

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(endpoints.ssoJWT).not.toHaveBeenCalled();
    expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    expect(localStorage.getItem("suiin_token")).toBeNull();
  });
});

describe("AuthProvider — credencial Bearer con origen manual (login con credenciales del Inventario tecleadas a mano)", () => {
  beforeEach(() => {
    localStorage.setItem("suiin_token", "jwt-manual");
    localStorage.setItem("suiin_auth_scheme", "Bearer");
    // sin suiin_auth_origen — así queda tras login() con ssoJWTLogin, ver más abajo
  });

  it("valida contra /api/auth/me/ y NO se re-verifica contra el SSO silencioso", async () => {
    endpoints.me.mockResolvedValue({ data: { username: "admin_manual", is_staff: true } });

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(endpoints.me).toHaveBeenCalledTimes(1);
    expect(endpoints.ssoJWT).not.toHaveBeenCalled();
    expect(screen.getByTestId("usuario")).toHaveTextContent("admin_manual");
  });
});

describe("AuthProvider — credencial Bearer con origen 'sso' (el caso que causaba el bug real)", () => {
  beforeEach(() => {
    localStorage.setItem("suiin_token", "jwt-sso-viejo");
    localStorage.setItem("suiin_auth_scheme", "Bearer");
    localStorage.setItem("suiin_auth_origen", "sso");
  });

  it("al montar, se re-verifica contra el Inventario en vez de solo confiar en el token guardado", async () => {
    endpoints.ssoJWT.mockResolvedValue({ data: { token: "jwt-sso-nuevo", username: "admin", roles: ["Administrador"] } });

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(endpoints.ssoJWT).toHaveBeenCalledTimes(1);
    expect(endpoints.me).not.toHaveBeenCalled(); // no se valida el JWT viejo directo, se re-pide al Inventario
    expect(screen.getByTestId("usuario")).toHaveTextContent("admin");
  });

  it("regresión del bug real: si el Inventario ya cerró sesión, se descarta el JWT aunque no haya vencido", async () => {
    // El JWT viejo en sí seguiría siendo válido (no vencido) — lo que cambió
    // es que el Inventario ya no tiene sesión activa que lo respalde.
    endpoints.ssoJWT.mockRejectedValue(new Error("401 - sin sesión en el Inventario"));

    renderizar();
    await esperarQueTermineDeVerificar();

    expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    expect(localStorage.getItem("suiin_token")).toBeNull();
    expect(localStorage.getItem("suiin_auth_origen")).toBeNull();
  });

  it("se re-verifica de nuevo pasados los 3 minutos, sin necesidad de recargar la página", async () => {
    endpoints.ssoJWT.mockResolvedValue({ data: { token: "jwt-sso-nuevo", username: "admin", roles: [] } });
    renderizar();
    await esperarQueTermineDeVerificar();
    expect(endpoints.ssoJWT).toHaveBeenCalledTimes(1);

    // El Inventario cierra sesión en OTRA pestaña mientras esta sigue abierta.
    endpoints.ssoJWT.mockRejectedValue(new Error("401"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3 * 60 * 1000);
    });

    expect(endpoints.ssoJWT).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getByTestId("autenticado")).toHaveTextContent("false"));
  });

  it("antes de los 3 minutos, no vuelve a llamar al Inventario", async () => {
    endpoints.ssoJWT.mockResolvedValue({ data: { token: "jwt-sso-nuevo", username: "admin", roles: [] } });
    renderizar();
    await esperarQueTermineDeVerificar();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2 * 60 * 1000);
    });
    expect(endpoints.ssoJWT).toHaveBeenCalledTimes(1);
  });
});

describe("AuthProvider — login()", () => {
  it("login manual con credenciales del Inventario NO marca origen 'sso' (no debe quedar sujeto a la revalidación periódica)", async () => {
    endpoints.ssoJWT.mockRejectedValue(new Error("401")); // sin sesión previa
    endpoints.ssoJWTLogin.mockResolvedValue({ data: { token: "jwt-x", username: "ana", roles: ["Dinamizador"] } });

    renderizar();
    await esperarQueTermineDeVerificar();

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => expect(screen.getByTestId("usuario")).toHaveTextContent("ana"));
    expect(localStorage.getItem("suiin_auth_scheme")).toBe("Bearer");
    expect(localStorage.getItem("suiin_auth_origen")).toBeNull();
  });

  it("si las credenciales no son del Inventario, cae al login propio de riesgos (esquema Token)", async () => {
    endpoints.ssoJWT.mockRejectedValue(new Error("401"));
    endpoints.ssoJWTLogin.mockRejectedValue(new Error("esas credenciales no existen en el Inventario"));
    endpoints.login.mockResolvedValue({ data: { token: "tok-y", username: "consultor_local", is_staff: false } });

    renderizar();
    await esperarQueTermineDeVerificar();

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => expect(screen.getByTestId("usuario")).toHaveTextContent("consultor_local"));
    expect(localStorage.getItem("suiin_auth_scheme")).toBe("Token");
  });
});

describe("AuthProvider — logout()", () => {
  it("borra las credenciales guardadas y deja de estar autenticado", async () => {
    localStorage.setItem("suiin_token", "tok-propio");
    localStorage.setItem("suiin_auth_scheme", "Token");
    endpoints.me.mockResolvedValue({ data: { username: "consultor_local", is_staff: false } });
    endpoints.logout.mockResolvedValue({});

    renderizar();
    await esperarQueTermineDeVerificar();
    expect(screen.getByTestId("autenticado")).toHaveTextContent("true");

    await act(async () => {
      screen.getByText("logout").click();
    });

    expect(screen.getByTestId("autenticado")).toHaveTextContent("false");
    expect(localStorage.getItem("suiin_token")).toBeNull();
  });
});

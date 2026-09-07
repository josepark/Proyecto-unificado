import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { usePlataforma } from "../context/PlataformaContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../context/PlataformaContext", () => ({
  usePlataforma: vi.fn(),
}));

vi.mock("./LoginModal", () => ({
  default: ({ open }) => (open ? <div data-testid="login-modal-abierto" /> : null),
}));

async function montarConRuta({ ruta = "/activos", embebido = false } = {}) {
  usePlataforma.mockReturnValue({ anidado: embebido, prefijo: "/gestion-riesgos" });

  const { default: RutaProtegida } = await import("./RutaProtegida");

  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route element={<RutaProtegida />}>
          <Route path={ruta} element={<div data-testid="contenido-protegido">Contenido real de la página</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  window.history.pushState({}, "", "/");
});

describe("RutaProtegida — con sesión", () => {
  it("deja pasar y muestra el contenido real de la página (Outlet)", async () => {
    useAuth.mockReturnValue({ isAuthenticated: true, checking: false, plataformaAutenticada: true });

    await montarConRuta();

    expect(screen.getByTestId("contenido-protegido")).toBeInTheDocument();
    expect(screen.queryByText("Esta sección requiere sesión")).not.toBeInTheDocument();
  });
});

describe("RutaProtegida — plataforma unificada sincronizando SSO", () => {
  it("muestra aviso de sincronización mientras el JWT de riesgos llega", async () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      checking: true,
      plataformaAutenticada: true,
    });

    await montarConRuta({ embebido: true });

    expect(screen.getByText(/Sincronizando sesión/)).toBeInTheDocument();
    expect(screen.queryByText("Esta sección requiere sesión")).not.toBeInTheDocument();
  });
});

describe("RutaProtegida — sin sesión, acceso directo (no embebido)", () => {
  it("bloquea el contenido y muestra el aviso, no el Outlet", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false, checking: false, plataformaAutenticada: false });

    await montarConRuta({ embebido: false });

    expect(screen.queryByTestId("contenido-protegido")).not.toBeInTheDocument();
    expect(screen.getByText("Esta sección requiere sesión")).toBeInTheDocument();
  });

  it("ofrece un botón propio de Iniciar sesión", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false, checking: false, plataformaAutenticada: false });

    await montarConRuta({ embebido: false });

    expect(screen.getByText("Iniciar sesión")).toBeInTheDocument();
  });

  it("abre el modal de login al hacer clic", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    useAuth.mockReturnValue({ isAuthenticated: false, checking: false, plataformaAutenticada: false });

    await montarConRuta({ embebido: false });

    expect(screen.queryByTestId("login-modal-abierto")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Iniciar sesión"));
    expect(screen.getByTestId("login-modal-abierto")).toBeInTheDocument();
  });
});

describe("RutaProtegida — sin sesión, modo embebido (plataforma unificada)", () => {
  it("bloquea el contenido y enlaza al login del shell, sin modal propio", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false, checking: false, plataformaAutenticada: false });

    await montarConRuta({ embebido: true });

    expect(screen.queryByTestId("contenido-protegido")).not.toBeInTheDocument();
    expect(screen.getByText("Esta sección requiere sesión")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Iniciar sesión/i })).toHaveAttribute("href", "/login?next=%2Factivos");
    expect(screen.queryByRole("button", { name: /Iniciar sesión/i })).not.toBeInTheDocument();
  });
});

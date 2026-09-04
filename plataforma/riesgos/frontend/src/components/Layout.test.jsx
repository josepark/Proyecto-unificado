import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

// LoginModal tiene su propia lógica de formulario — se simula acá para que
// estas pruebas se queden enfocadas en Layout (mismo criterio que ya se usó
// en RutaProtegida.test.jsx).
vi.mock("./LoginModal", () => ({
  default: ({ open }) => (open ? <div data-testid="login-modal-abierto" /> : null),
}));

async function montarLayout({ embebido = false } = {}) {
  vi.resetModules();
  // Layout.jsx calcula EMBEBIDO desde window.location.search al cargar el
  // módulo — con vi.resetModules() se fuerza una re-evaluación fresca de esa
  // constante en cada prueba (mismo patrón que RutaProtegida.test.jsx).
  window.history.pushState({}, "", embebido ? "/?embed=1" : "/");
  const { default: Layout } = await import("./Layout");

  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<div>contenido</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Layout — menú según sesión", () => {
  it("sin sesión, el menú solo navega a Panel general", async () => {
    useAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: vi.fn() });
    await montarLayout();

    expect(screen.getByText("Panel general")).toBeInTheDocument();
    expect(screen.queryByText("Vulnerabilidades")).not.toBeInTheDocument();
    expect(screen.queryByText("Plan de tratamiento")).not.toBeInTheDocument();
  });

  it("con sesión, el menú completo está disponible", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout();

    expect(screen.getByText("Vulnerabilidades")).toBeInTheDocument();
    expect(screen.getByText("Plan de tratamiento")).toBeInTheDocument();
    expect(screen.getByText("Catálogos")).toBeInTheDocument();
  });
});

describe("Layout — bloque de sesión propio, embebido dentro del Inventario", () => {
  // Hallazgo real (captura del usuario, 2026-08-25): dentro del Inventario,
  // la sesión ya se ve y se controla en la barra propia del Inventario
  // ("Sesión: admin (roles) · Salir") — mostrar ACÁ TAMBIÉN "admin" con su
  // propio botón de "Cerrar sesión" daba la impresión de dos inicios de
  // sesión separados, aunque técnicamente sea la misma (JWT único).

  it("con sesión activa, NO muestra el usuario ni un botón de cerrar sesión propio", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: true });

    expect(screen.queryByText("admin")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Cerrar sesión")).not.toBeInTheDocument();
  });

  it("sin sesión, NO muestra ningún botón de iniciar sesión propio", async () => {
    useAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: vi.fn() });
    await montarLayout({ embebido: true });

    expect(screen.queryByText("Iniciar sesión")).not.toBeInTheDocument();
  });

  it("no muestra el bloque de marca 'SUIIN-SGSI' de arriba", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: true });

    expect(screen.queryByText("SUIIN-SGSI")).not.toBeInTheDocument();
  });

  it("no muestra el pie 'Consejo Regional Indígena del Cauca'", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: true });

    expect(screen.queryByText(/Consejo Regional/)).not.toBeInTheDocument();
  });

  it("aun así, la navegación completa sigue disponible con sesión", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: true });

    expect(screen.getByText("Vulnerabilidades")).toBeInTheDocument();
    expect(screen.getByText("Plan de tratamiento")).toBeInTheDocument();
  });
});

describe("Layout — bloque de sesión propio, acceso directo (no embebido)", () => {
  it("con sesión activa, SÍ muestra el usuario y el botón de cerrar sesión", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: false });

    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByTitle("Cerrar sesión")).toBeInTheDocument();
  });

  it("sin sesión, SÍ muestra el botón de iniciar sesión (es la única forma de entrar en modo independiente)", async () => {
    useAuth.mockReturnValue({ user: null, isAuthenticated: false, logout: vi.fn() });
    await montarLayout({ embebido: false });

    expect(screen.getByText("Iniciar sesión")).toBeInTheDocument();
  });

  it("muestra el bloque de marca 'SUIIN-SGSI'", async () => {
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: vi.fn() });
    await montarLayout({ embebido: false });

    expect(screen.getByText("SUIIN-SGSI")).toBeInTheDocument();
  });

  it("clic en cerrar sesión llama a logout()", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const logoutMock = vi.fn();
    useAuth.mockReturnValue({ user: { username: "admin" }, isAuthenticated: true, logout: logoutMock });
    await montarLayout({ embebido: false });

    await userEvent.click(screen.getByTitle("Cerrar sesión"));

    expect(logoutMock).toHaveBeenCalledTimes(1);
  });
});

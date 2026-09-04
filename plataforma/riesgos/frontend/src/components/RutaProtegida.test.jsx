import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

// LoginModal tiene su propia lógica de formulario/envío — se simula acá para
// que estas pruebas se queden enfocadas en RutaProtegida, no en el modal.
vi.mock("./LoginModal", () => ({
  default: ({ open }) => (open ? <div data-testid="login-modal-abierto" /> : null),
}));

async function montarConRuta({ ruta = "/activos", embebido = false } = {}) {
  vi.resetModules();
  const url = embebido ? `${ruta}?embed=1` : ruta;
  window.history.pushState({}, "", url);

  // RutaProtegida calcula EMBEBIDO desde window.location.search al cargar el
  // módulo — con vi.resetModules() se fuerza una re-evaluación fresca de esa
  // constante en cada prueba, en vez de quedar pegada al primer valor leído.
  const { default: RutaProtegida } = await import("./RutaProtegida");

  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route element={<RutaProtegida />}>
          <Route path={ruta} element={<div data-testid="contenido-protegido">Contenido real de la página</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
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
    useAuth.mockReturnValue({ isAuthenticated: true });

    await montarConRuta();

    expect(screen.getByTestId("contenido-protegido")).toBeInTheDocument();
    expect(screen.queryByText("Esta sección requiere sesión")).not.toBeInTheDocument();
  });
});

describe("RutaProtegida — sin sesión, acceso directo (no embebido)", () => {
  it("bloquea el contenido y muestra el aviso, no el Outlet", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false });

    await montarConRuta({ embebido: false });

    expect(screen.queryByTestId("contenido-protegido")).not.toBeInTheDocument();
    expect(screen.getByText("Esta sección requiere sesión")).toBeInTheDocument();
  });

  it("ofrece un botón propio de Iniciar sesión", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false });

    await montarConRuta({ embebido: false });

    expect(screen.getByText("Iniciar sesión")).toBeInTheDocument();
  });

  it("abre el modal de login al hacer clic", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    useAuth.mockReturnValue({ isAuthenticated: false });

    await montarConRuta({ embebido: false });

    expect(screen.queryByTestId("login-modal-abierto")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Iniciar sesión"));
    expect(screen.getByTestId("login-modal-abierto")).toBeInTheDocument();
  });
});

describe("RutaProtegida — sin sesión, modo embebido (dentro del Inventario)", () => {
  it("bloquea el contenido igual, pero SIN botón de Iniciar sesión propio", async () => {
    // Mismo motivo que en Layout.jsx: dentro del Inventario es la misma
    // sesión (JWT único) — un botón de login aparte aquí da a entender que
    // este módulo pide credenciales propias, que fue justo lo que se corrigió.
    useAuth.mockReturnValue({ isAuthenticated: false });

    await montarConRuta({ embebido: true });

    expect(screen.queryByTestId("contenido-protegido")).not.toBeInTheDocument();
    expect(screen.getByText("Esta sección requiere sesión")).toBeInTheDocument();
    expect(screen.queryByText("Iniciar sesión")).not.toBeInTheDocument();
  });

  it("sugiere revisar la sesión desde el Inventario en vez de ofrecer un login propio", async () => {
    useAuth.mockReturnValue({ isAuthenticated: false });

    await montarConRuta({ embebido: true });

    expect(screen.getByText(/todavía no se ha sincronizado/)).toBeInTheDocument();
  });
});

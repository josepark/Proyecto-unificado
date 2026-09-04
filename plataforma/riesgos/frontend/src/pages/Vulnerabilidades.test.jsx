import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Vulnerabilidades from "./Vulnerabilidades";
import endpoints from "../api/endpoints";

vi.mock("../api/endpoints", () => ({
  default: {
    vulnerabilidades: vi.fn(),
    activos: vi.fn(),
    actualizarVulnerabilidad: vi.fn(),
    crearVulnerabilidad: vi.fn(),
    eliminarVulnerabilidad: vi.fn(),
    bulkActualizarVulnerabilidades: vi.fn(),
  },
}));

// guard() real depende de la sesión (useAuth/AuthContext) — se simula acá
// para que estas pruebas se queden enfocadas en la página, no en el flujo de
// autenticación (ya cubierto aparte en AuthContext.test.jsx). Por defecto
// deja pasar todo, como si hubiera sesión.
const guardMock = vi.fn((accion) => accion);
vi.mock("../lib/useAuthGuard", () => ({
  useAuthGuard: () => ({ guard: guardMock, loginOpen: false, setLoginOpen: vi.fn() }),
}));

// EntityForm y GenerarAccionModal ya tienen sus propios archivos de pruebas
// — se simulan acá para no acoplarse a su render interno.
vi.mock("../components/EntityForm", () => ({
  default: ({ initialValues, onSubmit }) => (
    <div data-testid="entity-form-vuln">
      <button onClick={() => onSubmit({ ...initialValues, nombre_vulnerabilidad: "Editado" })}>
        Guardar (doble de prueba)
      </button>
    </div>
  ),
}));
vi.mock("../components/GenerarAccionModal", () => ({
  default: ({ open, origen }) =>
    open ? <div data-testid="generar-accion-modal">Origen: {origen?.objeto?.nombre_vulnerabilidad}</div> : null,
}));
vi.mock("../components/LoginModal", () => ({
  default: ({ open }) => (open ? <div data-testid="login-modal" /> : null),
}));

const VULN_A = {
  id: 1, activo: 10, activo_id_activo: "RED-012", activo_nombre: "Dell EMC PowerEdge R740",
  nombre_vulnerabilidad: "TLS débil", severidad_ov_display: "Critical", probabilidad: 5, impacto: 5, score: 25,
  nivel_riesgo: "CRITICO", estado: "PENDIENTE", estado_display: "Pendiente",
};
const VULN_B = {
  id: 2, activo: 11, activo_id_activo: "RED-013", activo_nombre: "Dell EMC PowerEdge R420",
  nombre_vulnerabilidad: "DNS Cache Snooping", severidad_ov_display: "Medium", probabilidad: 2, impacto: 3, score: 6,
  nivel_riesgo: "MEDIO", estado: "PENDIENTE", estado_display: "Pendiente",
};

function mockDatosBase({ vulnerabilidades = [VULN_A, VULN_B] } = {}) {
  endpoints.vulnerabilidades.mockResolvedValue({ data: { results: vulnerabilidades } });
  endpoints.activos.mockResolvedValue({ data: { results: [] } });
}

function renderizar() {
  return render(
    <MemoryRouter>
      <Vulnerabilidades />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  guardMock.mockImplementation((accion) => accion);
});

describe("Vulnerabilidades — carga y estados", () => {
  it("muestra las vulnerabilidades reales devueltas por la API", async () => {
    mockDatosBase();
    renderizar();

    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());
    expect(screen.getByText("DNS Cache Snooping")).toBeInTheDocument();
    expect(screen.getByText("RED-012")).toBeInTheDocument();
  });

  it("el encabezado muestra el total y el conteo de críticas", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() =>
      expect(screen.getByText(/2 hallazgo\(s\) · 1 crítico\(s\)/)).toBeInTheDocument()
    );
  });

  it("sin resultados, muestra el mensaje de vacío en vez de la tabla", async () => {
    mockDatosBase({ vulnerabilidades: [] });
    renderizar();
    await waitFor(() =>
      expect(screen.getByText("Ninguna vulnerabilidad coincide con los filtros seleccionados.")).toBeInTheDocument()
    );
  });
});

describe("Vulnerabilidades — filtros", () => {
  it("escribir en el buscador manda el parámetro 'search' a la API", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/Buscar por nombre, CVE/), "TLS");

    await waitFor(() =>
      expect(endpoints.vulnerabilidades).toHaveBeenLastCalledWith(expect.objectContaining({ search: "TLS" }))
    );
  });

  it("elegir un nivel manda 'nivel_riesgo' a la API", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.selectOptions(screen.getByDisplayValue("Todos los niveles"), "CRITICO");

    await waitFor(() =>
      expect(endpoints.vulnerabilidades).toHaveBeenLastCalledWith(expect.objectContaining({ nivel_riesgo: "CRITICO" }))
    );
  });

  it("cambiar un filtro limpia cualquier selección previa", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    const filas = screen.getAllByRole("checkbox");
    await userEvent.click(filas[1]); // primera fila (filas[0] es "seleccionar todos")
    expect(screen.getByText("1 seleccionada")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByDisplayValue("Todos los niveles"), "ALTO");

    await waitFor(() => expect(screen.queryByText("1 seleccionada")).not.toBeInTheDocument());
  });
});

describe("Vulnerabilidades — selección", () => {
  it("marcar una fila muestra la barra de acción en lote con el conteo", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[1]);

    expect(screen.getByText("1 seleccionada")).toBeInTheDocument();
  });

  it("marcar dos filas dice 'seleccionadas' (plural)", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[1]);
    await userEvent.click(checkboxes[2]);

    expect(screen.getByText("2 seleccionadas")).toBeInTheDocument();
  });

  it("'seleccionar todos' marca las filas visibles, y vuelve a marcarlo las desmarca todas", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[0]); // encabezado "seleccionar todos"
    expect(screen.getByText("2 seleccionadas")).toBeInTheDocument();
    expect(checkboxes[1]).toBeChecked();
    expect(checkboxes[2]).toBeChecked();

    await userEvent.click(checkboxes[0]);
    expect(screen.queryByText(/seleccionada/)).not.toBeInTheDocument();
  });

  it("'Quitar selección' limpia todo sin llamar a ninguna API", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByRole("checkbox")[1]);
    await userEvent.click(screen.getByText("Quitar selección"));

    expect(screen.queryByText(/seleccionada/)).not.toBeInTheDocument();
    expect(endpoints.bulkActualizarVulnerabilidades).not.toHaveBeenCalled();
  });
});

describe("Vulnerabilidades — operaciones en lote", () => {
  it("cambiar el estado en lote llama a la API con los ids seleccionados y el campo correcto", async () => {
    mockDatosBase();
    endpoints.bulkActualizarVulnerabilidades.mockResolvedValue({ data: { actualizados: 2 } });
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[1]);
    await userEvent.click(checkboxes[2]);

    // Hay dos selects "elegir…" (estado y tratamiento) — se identifica el de
    // estado por su texto hermano "Cambiar estado a:".
    const bloqueEstado = screen.getByText("Cambiar estado a:").closest("div");
    await userEvent.selectOptions(within(bloqueEstado).getByRole("combobox"), "CERRADO");

    await waitFor(() =>
      expect(endpoints.bulkActualizarVulnerabilidades).toHaveBeenCalledWith([1, 2], { estado: "CERRADO" })
    );
  });

  it("cambiar el tratamiento en lote llama a la API con 'tratamiento', no 'estado'", async () => {
    mockDatosBase();
    endpoints.bulkActualizarVulnerabilidades.mockResolvedValue({ data: { actualizados: 1 } });
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByRole("checkbox")[1]);

    const bloqueTratamiento = screen.getByText("Cambiar tratamiento a:").closest("div");
    await userEvent.selectOptions(within(bloqueTratamiento).getByRole("combobox"), "MITIGAR_INMEDIATO");

    await waitFor(() =>
      expect(endpoints.bulkActualizarVulnerabilidades).toHaveBeenCalledWith([1], { tratamiento: "MITIGAR_INMEDIATO" })
    );
  });

  it("tras aplicar en lote, la selección se limpia y se vuelve a pedir la lista", async () => {
    mockDatosBase();
    endpoints.bulkActualizarVulnerabilidades.mockResolvedValue({ data: { actualizados: 1 } });
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByRole("checkbox")[1]);
    const llamadasAntes = endpoints.vulnerabilidades.mock.calls.length;

    const bloqueEstado = screen.getByText("Cambiar estado a:").closest("div");
    await userEvent.selectOptions(within(bloqueEstado).getByRole("combobox"), "ACEPTADO");

    await waitFor(() => expect(screen.queryByText(/seleccionada/)).not.toBeInTheDocument());
    await waitFor(() =>
      expect(endpoints.vulnerabilidades.mock.calls.length).toBeGreaterThan(llamadasAntes)
    );
  });
});

describe("Vulnerabilidades — flujo CRUD", () => {
  it("'Nueva vulnerabilidad' abre el formulario de creación", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Nueva vulnerabilidad"));

    expect(screen.getByTestId("entity-form-vuln")).toBeInTheDocument();
  });

  it("guardar en el formulario de creación llama a crearVulnerabilidad, no a actualizar", async () => {
    mockDatosBase();
    endpoints.crearVulnerabilidad.mockResolvedValue({ data: {} });
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Nueva vulnerabilidad"));

    await userEvent.click(screen.getByText("Guardar (doble de prueba)"));

    await waitFor(() => expect(endpoints.crearVulnerabilidad).toHaveBeenCalledTimes(1));
    expect(endpoints.actualizarVulnerabilidad).not.toHaveBeenCalled();
  });

  it("editar una fila abre el formulario y guarda con actualizarVulnerabilidad, con el id correcto", async () => {
    mockDatosBase();
    endpoints.actualizarVulnerabilidad.mockResolvedValue({ data: {} });
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByTitle("Editar")[0]);
    await userEvent.click(screen.getByText("Guardar (doble de prueba)"));

    await waitFor(() =>
      expect(endpoints.actualizarVulnerabilidad).toHaveBeenCalledWith(1, expect.objectContaining({ nombre_vulnerabilidad: "Editado" }))
    );
  });

  it("eliminar pide confirmación antes de llamar a la API", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByTitle("Eliminar")[0]);

    expect(screen.getByText("¿Eliminar esta vulnerabilidad?")).toBeInTheDocument();
    expect(endpoints.eliminarVulnerabilidad).not.toHaveBeenCalled();
  });

  it("confirmar la eliminación llama a la API con el id correcto y recarga", async () => {
    mockDatosBase();
    endpoints.eliminarVulnerabilidad.mockResolvedValue({});
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByTitle("Eliminar")[0]);
    await userEvent.click(screen.getByText("Eliminar", { selector: "button" }));

    await waitFor(() => expect(endpoints.eliminarVulnerabilidad).toHaveBeenCalledWith(1));
  });

  it("'Generar acción' abre el modal con el origen correcto", async () => {
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getAllByTitle("Generar acción de tratamiento")[0]);

    expect(screen.getByTestId("generar-accion-modal")).toHaveTextContent("Origen: TLS débil");
  });
});

describe("Vulnerabilidades — sin sesión (guard)", () => {
  it("si el guard bloquea la acción, no se abre el formulario de creación", async () => {
    guardMock.mockImplementation(() => () => {}); // simula: sin sesión, no ejecuta la acción real
    mockDatosBase();
    renderizar();
    await waitFor(() => expect(screen.getByText("TLS débil")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Nueva vulnerabilidad"));

    expect(screen.queryByTestId("entity-form-vuln")).not.toBeInTheDocument();
  });
});

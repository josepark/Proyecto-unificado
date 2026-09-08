import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import GenerarAccionModal from "../components/GenerarAccionModal";

vi.mock("../api/endpoints", () => ({
  default: {
    planesTratamiento: vi.fn(),
    controlesIso: vi.fn(),
    crearAccion: vi.fn(),
  },
}));

vi.mock("../components/EntityForm", () => ({
  default: ({ initialValues, onSubmit }) => (
    <div>
      <span data-testid="plan-inicial">{initialValues.plan}</span>
      <button type="button" onClick={() => onSubmit({ ...initialValues, plan: initialValues.plan, id_riesgo: "R-E2E", descripcion_riesgo: "x", probabilidad: 3, impacto: 3, acciones_tratamiento: "y" })}>
        Crear acción E2E
      </button>
    </div>
  ),
}));

import endpoints from "../api/endpoints";

const ORIGEN_VULN = {
  tipo: "vulnerabilidad",
  objeto: {
    id: 9,
    nombre_vulnerabilidad: "SQLi",
    probabilidad: 4,
    impacto: 4,
    solucion_recomendada: "Parchear",
  },
};

describe("Flujo PTR E2E (componente)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    endpoints.planesTratamiento.mockResolvedValue({
      data: { results: [{ id: 42, referencia: "PTR-001" }, { id: 7, referencia: "PTR-002" }] },
    });
    endpoints.controlesIso.mockResolvedValue({ data: { results: [] } });
    endpoints.crearAccion.mockResolvedValue({ data: { id: 100 } });
  });

  it("precarga el plan cuando hay varios PTR y crea acción enlazada al origen", async () => {
    const onCreated = vi.fn();
    const onClose = vi.fn();

    render(
      <MemoryRouter>
        <GenerarAccionModal open origen={ORIGEN_VULN} onClose={onClose} onCreated={onCreated} />
      </MemoryRouter>
    );

    await waitFor(() => expect(endpoints.planesTratamiento).toHaveBeenCalled());
    expect(screen.getByTestId("plan-inicial")).toHaveTextContent("42");

    await userEvent.click(screen.getByRole("button", { name: /Crear acción E2E/i }));

    await waitFor(() => expect(endpoints.crearAccion).toHaveBeenCalledWith(
      expect.objectContaining({
        plan: 42,
        origen_vulnerabilidad: 9,
        origen_riesgo_activo: null,
        origen_riesgo_contextual: null,
      })
    ));
    expect(onCreated).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});

import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PlanTratamiento from "./PlanTratamiento";

vi.mock("../api/endpoints", () => ({
  default: {
    planesTratamiento: vi.fn(),
    planTratamiento: vi.fn(),
    campanasRedTeam: vi.fn(),
    controlesIso: vi.fn(),
    historial: vi.fn(() => Promise.resolve({ data: [] })),
  },
}));

vi.mock("../lib/useAuthGuard", () => ({
  useAuthGuard: () => ({ guard: (fn) => fn, loginOpen: false, setLoginOpen: vi.fn() }),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ puedeEditar: true, roles: ["Administrador"], isAuthenticated: true }),
}));

vi.mock("../components/LoginModal", () => ({
  default: () => null,
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

import endpoints from "../api/endpoints";

describe("PlanTratamiento", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    endpoints.campanasRedTeam.mockResolvedValue({ data: { results: [] } });
    endpoints.controlesIso.mockResolvedValue({ data: { results: [] } });
    endpoints.planTratamiento.mockResolvedValue({
      data: { id: 7, referencia: "PTR-001", titulo: "Plan demo", acciones: [] },
    });
  });

  it("no llama planTratamiento(undefined) mientras carga la lista de planes", async () => {
    let resolverLista;
    endpoints.planesTratamiento.mockReturnValue(
      new Promise((resolve) => {
        resolverLista = resolve;
      })
    );

    render(
      <MemoryRouter>
        <PlanTratamiento />
      </MemoryRouter>
    );

    await waitFor(() => expect(endpoints.planesTratamiento).toHaveBeenCalled());
    expect(endpoints.planTratamiento).not.toHaveBeenCalled();

    resolverLista({ data: { results: [{ id: 7, referencia: "PTR-001" }] } });

    await waitFor(() => expect(endpoints.planTratamiento).toHaveBeenCalledWith(7));
  });
});

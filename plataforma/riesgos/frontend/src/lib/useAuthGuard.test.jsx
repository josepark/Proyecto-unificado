import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useAuthGuard } from "./useAuthGuard";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../context/AuthContext";

function Probe({ onRun }) {
  const { guard, puedeEditar } = useAuthGuard();
  return (
    <button type="button" onClick={guard(onRun)}>
      {puedeEditar ? "editar" : "solo-lectura"}
    </button>
  );
}

describe("useAuthGuard", () => {
  it("bloquea acciones de escritura para Consultor autenticado", async () => {
    const onRun = vi.fn();
    useAuth.mockReturnValue({
      isAuthenticated: true,
      puedeEditar: false,
    });

    render(<Probe onRun={onRun} />);
    expect(screen.getByRole("button")).toHaveTextContent("solo-lectura");

    await userEvent.click(screen.getByRole("button"));
    expect(onRun).not.toHaveBeenCalled();
  });

  it("permite acciones de escritura para Dinamizador autenticado", async () => {
    const onRun = vi.fn();
    useAuth.mockReturnValue({
      isAuthenticated: true,
      puedeEditar: true,
    });

    render(<Probe onRun={onRun} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onRun).toHaveBeenCalledOnce();
  });
});

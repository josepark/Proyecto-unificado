import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useState } from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MitreMultiSelect from "./MitreMultiSelect";
import endpoints from "../api/endpoints";

vi.mock("../api/endpoints", () => ({
  default: { tecnicasMitre: vi.fn() },
}));

function Controlado(props) {
  const [value, setValue] = useState(props.initialValue ?? "");
  return <MitreMultiSelect {...props} value={value} onChange={setValue} />;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  endpoints.tecnicasMitre.mockResolvedValue({
    data: { results: [{ id: 1, codigo: "T1040", nombre: "Network Sniffing", tipo_display: "Técnica" }] },
  });
});

afterEach(() => {
  vi.useRealTimers();
});

async function escribirEnBuscador(usuario, texto) {
  const campo = screen.getByPlaceholderText(/Buscar por código o nombre/);
  await usuario.type(campo, texto);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(200); // el debounce real es de 200ms
  });
  return campo;
}

describe("MitreMultiSelect — fichas a partir del valor guardado", () => {
  it("sin valor, no muestra ninguna ficha", () => {
    render(<Controlado />);
    expect(screen.queryByText("T1190")).not.toBeInTheDocument();
  });

  it("un valor 'T1190/T1498' se muestra como dos fichas separadas", () => {
    render(<Controlado initialValue="T1190/T1498" />);
    expect(screen.getByText("T1190")).toBeInTheDocument();
    expect(screen.getByText("T1498")).toBeInTheDocument();
  });

  it("respeta un separador distinto (ej. ' · ' para tecnica_mitre_cwe)", () => {
    render(<Controlado initialValue="T1041 · CWE-306" separador=" · " />);
    expect(screen.getByText("T1041")).toBeInTheDocument();
    expect(screen.getByText("CWE-306")).toBeInTheDocument();
  });

  it("quitar una ficha la elimina del valor, conservando las demás", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Controlado initialValue="T1190/T1498/T1078" />);

    const fichaT1498 = screen.getByText("T1498").closest("span");
    await usuario.click(fichaT1498.querySelector("button"));

    expect(screen.getByText("T1190")).toBeInTheDocument();
    expect(screen.queryByText("T1498")).not.toBeInTheDocument();
    expect(screen.getByText("T1078")).toBeInTheDocument();
  });
});

describe("MitreMultiSelect — búsqueda con debounce", () => {
  it("no busca nada mientras el campo está vacío", async () => {
    render(<Controlado />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(endpoints.tecnicasMitre).not.toHaveBeenCalled();
  });

  it("busca 200ms después de dejar de escribir, no en cada tecla", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Controlado />);
    const campo = screen.getByPlaceholderText(/Buscar por código o nombre/);

    await usuario.type(campo, "sniff");
    // Antes de que pasen los 200ms desde la última tecla, no debe haber buscado
    expect(endpoints.tecnicasMitre).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(endpoints.tecnicasMitre).toHaveBeenCalledWith("sniff");
    expect(endpoints.tecnicasMitre).toHaveBeenCalledTimes(1);
  });

  it("muestra los resultados de la búsqueda en el desplegable", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Controlado />);
    await escribirEnBuscador(usuario, "sniff");

    await waitFor(() => expect(screen.getByText("Network Sniffing")).toBeInTheDocument());
    expect(screen.getByText("T1040")).toBeInTheDocument();
  });
});

describe("MitreMultiSelect — agregar códigos", () => {
  it("elegir un resultado de la búsqueda lo agrega como ficha y limpia el buscador", async () => {
    const onChange = vi.fn();
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<MitreMultiSelect value="" onChange={onChange} />);
    const campo = await escribirEnBuscador(usuario, "sniff");
    await waitFor(() => expect(screen.getByText("T1040")).toBeInTheDocument());

    await usuario.click(screen.getByText("T1040"));

    expect(onChange).toHaveBeenCalledWith("T1040");
  });

  it("agregar un segundo código lo une al primero con el separador", async () => {
    const onChange = vi.fn();
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<MitreMultiSelect value="T1190" onChange={onChange} />);
    await escribirEnBuscador(usuario, "sniff");
    await waitFor(() => expect(screen.getByText("T1040")).toBeInTheDocument());

    await usuario.click(screen.getByText("T1040"));

    expect(onChange).toHaveBeenCalledWith("T1190/T1040");
  });

  it("no agrega un código que ya está entre las fichas (sin duplicar)", async () => {
    const onChange = vi.fn();
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<MitreMultiSelect value="T1040" onChange={onChange} />);
    await escribirEnBuscador(usuario, "sniff");

    // "T1040" aparece dos veces en pantalla acá (la ficha ya puesta, y el
    // resultado de la búsqueda) — se apunta puntualmente al botón del
    // desplegable, no a la ficha, para no ambigüar la consulta.
    const resultadoEnDesplegable = await screen.findByText("Network Sniffing");
    await usuario.click(resultadoEnDesplegable);

    expect(onChange).not.toHaveBeenCalled();
  });

  it("presionar Enter agrega el texto escrito tal cual, aunque no esté en el catálogo (ej. un CWE)", async () => {
    endpoints.tecnicasMitre.mockResolvedValue({ data: { results: [] } });
    const onChange = vi.fn();
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<MitreMultiSelect value="" onChange={onChange} />);
    const campo = await escribirEnBuscador(usuario, "CWE-306");

    await usuario.type(campo, "{Enter}");

    expect(onChange).toHaveBeenCalledWith("CWE-306");
  });

  it("el botón '+ Agregar tal cual' aparece siempre que haya texto escrito, aunque haya resultados", async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Controlado />);
    await escribirEnBuscador(usuario, "sniff");

    await waitFor(() => expect(screen.getByText("Network Sniffing")).toBeInTheDocument());
    expect(screen.getByText(/Agregar "sniff" tal cual/)).toBeInTheDocument();
  });
});

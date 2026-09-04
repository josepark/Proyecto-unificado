import { describe, it, expect, vi, beforeEach } from "vitest";
import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CatalogoCombobox from "./CatalogoCombobox";
import endpoints from "../api/endpoints";

vi.mock("../api/endpoints", () => ({
  default: {
    catalogo: vi.fn(),
    catalogoObtenerOCrear: vi.fn(),
  },
}));

function Controlado(props) {
  // Reproduce cómo lo usa EntityForm de verdad: value/onChange controlados
  // desde afuera, no estado propio del combo.
  const [value, setValue] = useState(props.initialValue ?? "");
  return <CatalogoCombobox {...props} value={value} onChange={setValue} />;
}

beforeEach(() => {
  vi.clearAllMocks();
  endpoints.catalogo.mockResolvedValue({
    data: {
      results: [
        { id: 1, valor: "Servidor / Virtualización" },
        { id: 2, valor: "Switch gestionado" },
        { id: 3, valor: "Firewall" },
      ],
    },
  });
});

describe("CatalogoCombobox — carga inicial", () => {
  it("pide las opciones de la categoría al montar", async () => {
    render(<Controlado categoria="TIPO_ACTIVO" onChange={vi.fn()} value="" />);
    await waitFor(() => expect(endpoints.catalogo).toHaveBeenCalledWith("TIPO_ACTIVO"));
  });

  it("muestra 'Cargando…' mientras la petición está en vuelo", async () => {
    let resolver;
    endpoints.catalogo.mockReturnValue(new Promise((r) => { resolver = r; }));
    render(<Controlado categoria="TIPO_ACTIVO" onChange={vi.fn()} value="" />);

    await userEvent.click(screen.getByRole("textbox"));
    expect(screen.getByText("Cargando…")).toBeInTheDocument();

    resolver({ data: { results: [] } });
    await waitFor(() => expect(screen.queryByText("Cargando…")).not.toBeInTheDocument());
  });
});

describe("CatalogoCombobox — sugerencias y filtrado", () => {
  it("al enfocar el campo, muestra las opciones ya cargadas", async () => {
    render(<Controlado categoria="TIPO_ACTIVO" />);
    await userEvent.click(screen.getByRole("textbox"));

    await waitFor(() => expect(screen.getByText("Servidor / Virtualización")).toBeInTheDocument());
    expect(screen.getByText("Switch gestionado")).toBeInTheDocument();
    expect(screen.getByText("Firewall")).toBeInTheDocument();
  });

  it("escribir filtra las opciones por coincidencia parcial, sin distinguir mayúsculas", async () => {
    render(<Controlado categoria="TIPO_ACTIVO" />);
    const input = screen.getByRole("textbox");
    await userEvent.click(input);
    await waitFor(() => expect(screen.getByText("Firewall")).toBeInTheDocument());

    await userEvent.type(input, "switch");

    expect(screen.getByText("Switch gestionado")).toBeInTheDocument();
    expect(screen.queryByText("Firewall")).not.toBeInTheDocument();
    expect(screen.queryByText("Servidor / Virtualización")).not.toBeInTheDocument();
  });

  it("elegir una sugerencia la pone como valor del campo", async () => {
    render(<Controlado categoria="TIPO_ACTIVO" />);
    const input = screen.getByRole("textbox");
    await userEvent.click(input);
    await waitFor(() => expect(screen.getByText("Firewall")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Firewall"));

    expect(input).toHaveValue("Firewall");
  });

  it("sin coincidencias, avisa que se guardará como valor nuevo", async () => {
    render(<Controlado categoria="TIPO_ACTIVO" />);
    const input = screen.getByRole("textbox");
    await userEvent.click(input);
    await waitFor(() => expect(screen.getByText("Firewall")).toBeInTheDocument());

    await userEvent.type(input, "algo que no existe todavía");

    expect(screen.getByText(/se guardará como valor nuevo/)).toBeInTheDocument();
  });
});

describe("CatalogoCombobox — registrar un valor nuevo al salir del campo", () => {
  it("un valor que no coincide con nada existente se registra en el catálogo al perder el foco", async () => {
    endpoints.catalogoObtenerOCrear.mockResolvedValue({ data: { id: 9, valor: "Router doméstico" } });
    render(
      <div>
        <Controlado categoria="TIPO_ACTIVO" />
        <button>otro elemento para robar el foco</button>
      </div>
    );
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Router doméstico");
    await userEvent.click(screen.getByText("otro elemento para robar el foco"));

    await waitFor(() =>
      expect(endpoints.catalogoObtenerOCrear).toHaveBeenCalledWith("TIPO_ACTIVO", "Router doméstico")
    );
  });

  it("un valor que YA coincide exactamente con uno existente NO se vuelve a registrar", async () => {
    render(
      <div>
        <Controlado categoria="TIPO_ACTIVO" />
        <button>otro elemento</button>
      </div>
    );
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Firewall");
    await userEvent.click(screen.getByText("otro elemento"));

    await waitFor(() => expect(input).toHaveValue("Firewall"));
    expect(endpoints.catalogoObtenerOCrear).not.toHaveBeenCalled();
  });

  it("la coincidencia para no re-registrar ignora mayúsculas/minúsculas", async () => {
    render(
      <div>
        <Controlado categoria="TIPO_ACTIVO" />
        <button>otro elemento</button>
      </div>
    );
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "FIREWALL");
    await userEvent.click(screen.getByText("otro elemento"));

    await waitFor(() => expect(input).toHaveValue("FIREWALL"));
    expect(endpoints.catalogoObtenerOCrear).not.toHaveBeenCalled();
  });

  it("un campo vacío no intenta registrar nada al perder el foco", async () => {
    render(
      <div>
        <Controlado categoria="TIPO_ACTIVO" />
        <button>otro elemento</button>
      </div>
    );
    await userEvent.click(screen.getByRole("textbox"));
    await userEvent.click(screen.getByText("otro elemento"));

    expect(endpoints.catalogoObtenerOCrear).not.toHaveBeenCalled();
  });

  it("si el registro falla (ej. sin sesión), no rompe nada — el valor sigue en el campo", async () => {
    endpoints.catalogoObtenerOCrear.mockRejectedValue(new Error("401"));
    render(
      <div>
        <Controlado categoria="TIPO_ACTIVO" />
        <button>otro elemento</button>
      </div>
    );
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Valor nuevo sin sesión");
    await userEvent.click(screen.getByText("otro elemento"));

    await waitFor(() => expect(endpoints.catalogoObtenerOCrear).toHaveBeenCalled());
    expect(input).toHaveValue("Valor nuevo sin sesión"); // no se borra pese al error
  });
});

describe("CatalogoCombobox — modo multiline (ej. 'Solución recomendada')", () => {
  it("con multiline, renderiza un textarea en vez de un input de una línea", async () => {
    render(<Controlado categoria="SOLUCION_VULN" multiline />);
    await waitFor(() => expect(endpoints.catalogo).toHaveBeenCalled());
    const campo = screen.getByRole("textbox");
    expect(campo.tagName).toBe("TEXTAREA");
  });

  it("las sugerencias largas se recortan a 140 caracteres en la lista", async () => {
    const textoLargo = "Deshabilitar TLSv1.0 y TLSv1.1 en el servidor web, habilitar solo TLSv1.2 o superior, y verificar que ningún cliente heredado dependa de las versiones antiguas del protocolo antes del cambio en producción";
    endpoints.catalogo.mockResolvedValue({ data: { results: [{ id: 1, valor: textoLargo }] } });

    render(<Controlado categoria="SOLUCION_VULN" multiline />);
    await userEvent.click(screen.getByRole("textbox"));

    await waitFor(() => expect(screen.getByText(/Deshabilitar TLSv1\.0/)).toBeInTheDocument());
    const sugerencia = screen.getByText(/Deshabilitar TLSv1\.0/);
    expect(sugerencia.textContent.length).toBeLessThan(textoLargo.length);
    expect(sugerencia.textContent.endsWith("…")).toBe(true);
  });
});

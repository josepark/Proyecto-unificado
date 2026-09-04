import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EntityForm from "./EntityForm";

// CatalogoCombobox y MitreMultiSelect hacen sus propias llamadas a la API y
// tienen su propia lógica de búsqueda — se simulan acá para que estas
// pruebas se queden enfocadas en lo que le corresponde a EntityForm: elegir
// qué widget renderizar según field.type, y sanear el valor antes de enviar.
// Merecen su propio archivo de pruebas aparte.
vi.mock("./CatalogoCombobox", () => ({
  default: ({ value, onChange }) => (
    <input data-testid="catalogo-combobox-falso" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
  ),
}));
vi.mock("./MitreMultiSelect", () => ({
  default: ({ value, onChange }) => (
    <input data-testid="mitre-multiselect-falso" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EntityForm — un tipo de campo por widget", () => {
  it("type 'text' (o sin type) renderiza un input de texto", () => {
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const input = screen.getByLabelText("Nombre");
    expect(input.tagName).toBe("INPUT");
    expect(input.type).toBe("text");
  });

  it("type 'textarea' renderiza un textarea", () => {
    render(<EntityForm fields={[{ name: "obs", label: "Observaciones", type: "textarea" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Observaciones").tagName).toBe("TEXTAREA");
  });

  it("type 'select' renderiza un select con las opciones dadas más un '—' inicial", () => {
    render(
      <EntityForm
        fields={[{ name: "estado", label: "Estado", type: "select", options: [{ value: "A", label: "Activo" }, { value: "B", label: "Bajo" }] }]}
        onSubmit={vi.fn()} onCancel={vi.fn()}
      />
    );
    const select = screen.getByLabelText("Estado");
    expect(select.tagName).toBe("SELECT");
    const opciones = Array.from(select.querySelectorAll("option")).map((o) => o.textContent);
    expect(opciones).toEqual(["—", "Activo", "Bajo"]);
  });

  it("type 'checkbox' renderiza un checkbox y lo asocia a la etiqueta", () => {
    render(<EntityForm fields={[{ name: "activo", label: "¿Activo?", type: "checkbox" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("¿Activo?").type).toBe("checkbox");
  });

  it("type 'number' renderiza un input numérico", () => {
    render(<EntityForm fields={[{ name: "score", label: "Score", type: "number" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Score").type).toBe("number");
  });

  it("type 'date' renderiza un input de fecha", () => {
    render(<EntityForm fields={[{ name: "vence", label: "Vence", type: "date" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Vence").type).toBe("date");
  });

  it("type 'multiselect' renderiza un select múltiple", () => {
    render(
      <EntityForm
        fields={[{ name: "controles", label: "Controles", type: "multiselect", options: [{ value: 1, label: "5.1" }] }]}
        onSubmit={vi.fn()} onCancel={vi.fn()}
      />
    );
    expect(screen.getByLabelText("Controles")).toHaveAttribute("multiple");
  });

  it("type 'mitre' renderiza el selector MITRE", () => {
    render(<EntityForm fields={[{ name: "tecnica", label: "Técnica", type: "mitre" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByTestId("mitre-multiselect-falso")).toBeInTheDocument();
  });

  it("type 'catalogo' renderiza el combo de catálogo", () => {
    render(<EntityForm fields={[{ name: "tipo", label: "Tipo", type: "catalogo", categoria: "TIPO_ACTIVO" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByTestId("catalogo-combobox-falso")).toBeInTheDocument();
  });

  it("un campo requerido muestra el asterisco", () => {
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre", required: true }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("*")).toBeInTheDocument();
  });
});

describe("EntityForm — valores iniciales y por defecto", () => {
  it("sin initialValues, arranca con los defaults según el tipo (checkbox=false, multiselect=[], resto='')", () => {
    render(
      <EntityForm
        fields={[
          { name: "nombre", label: "Nombre" },
          { name: "activo", label: "Activo", type: "checkbox" },
        ]}
        onSubmit={vi.fn()} onCancel={vi.fn()}
      />
    );
    expect(screen.getByLabelText("Nombre")).toHaveValue("");
    expect(screen.getByLabelText("Activo")).not.toBeChecked();
  });

  it("initialValues sobrescribe los defaults", () => {
    render(
      <EntityForm
        fields={[{ name: "nombre", label: "Nombre" }, { name: "activo", label: "Activo", type: "checkbox" }]}
        initialValues={{ nombre: "Ya cargado", activo: true }}
        onSubmit={vi.fn()} onCancel={vi.fn()}
      />
    );
    expect(screen.getByLabelText("Nombre")).toHaveValue("Ya cargado");
    expect(screen.getByLabelText("Activo")).toBeChecked();
  });
});

describe("EntityForm — interacción", () => {
  it("escribir en un campo de texto y enviar, manda ese valor tal cual", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Nombre"), "RED-099");
    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ nombre: "RED-099" })));
  });

  it("un campo number convierte lo escrito a Number, no lo deja como string", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "valor", label: "Valor", type: "number" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Valor"), "12");
    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    const enviado = onSubmit.mock.calls[0][0];
    expect(enviado.valor).toBe(12);
    expect(typeof enviado.valor).toBe("number");
  });

  it("cancelar llama a onCancel sin llamar a onSubmit", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={onCancel} />);

    await userEvent.click(screen.getByText("Cancelar"));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mientras guarda, el botón muestra 'Guardando…' y queda deshabilitado", async () => {
    let resolver;
    const onSubmit = vi.fn(() => new Promise((r) => { resolver = r; }));
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    const boton = await screen.findByText("Guardando…");
    expect(boton).toBeDisabled();

    resolver();
    await waitFor(() => expect(screen.getByText("Guardar")).toBeInTheDocument());
  });

  it("submitLabel personalizado se usa en el botón", () => {
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={vi.fn()} onCancel={vi.fn()} submitLabel="Crear acción de tratamiento" />);
    expect(screen.getByText("Crear acción de tratamiento")).toBeInTheDocument();
  });
});

describe("EntityForm — saneo de valores antes de enviar (sanitize)", () => {
  it("un campo date vacío se manda como null, no como ''", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "vence", label: "Vence", type: "date" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar")); // sin tocar el campo, queda vacío

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].vence).toBeNull();
  });

  it("un campo number vacío se manda como null, no como ''", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "porcentaje", label: "Porcentaje", type: "number" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].porcentaje).toBeNull();
  });

  it("un campo marcado fkId vacío se manda como null aunque sea de texto", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "plan", label: "Plan", fkId: true }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].plan).toBeNull();
  });

  it("un campo de texto vacío sin fkId se manda tal cual ('', no null)", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(<EntityForm fields={[{ name: "notas", label: "Notas" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].notas).toBe("");
  });

  it("multiselect convierte sus valores a números al enviar", async () => {
    const onSubmit = vi.fn().mockResolvedValue();
    render(
      <EntityForm
        fields={[{ name: "controles", label: "Controles", type: "multiselect", options: [{ value: 1, label: "5.1" }, { value: 2, label: "5.2" }] }]}
        initialValues={{ controles: ["1", "2"] }}
        onSubmit={onSubmit} onCancel={vi.fn()}
      />
    );

    await userEvent.click(screen.getByText("Guardar"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].controles).toEqual([1, 2]);
  });
});

describe("EntityForm — secciones", () => {
  it("agrupa campos con el mismo section bajo un mismo encabezado", () => {
    render(
      <EntityForm
        fields={[
          { name: "a", label: "Campo A", section: "Identificación" },
          { name: "b", label: "Campo B", section: "Identificación" },
          { name: "c", label: "Campo C", section: "Riesgo" },
        ]}
        onSubmit={vi.fn()} onCancel={vi.fn()}
      />
    );
    expect(screen.getByText("Identificación")).toBeInTheDocument();
    expect(screen.getByText("Riesgo")).toBeInTheDocument();
  });

  it("campos sin section no muestran ningún encabezado", () => {
    render(<EntityForm fields={[{ name: "a", label: "Campo A" }]} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    // "_default" es una clave interna, nunca debe llegar a verse en pantalla
    expect(screen.queryByText("_default")).not.toBeInTheDocument();
  });
});

describe("EntityForm — manejo de errores al guardar", () => {
  it("un error con { detail } lo muestra tal cual", async () => {
    const onSubmit = vi.fn().mockRejectedValue({ response: { data: { detail: "No tiene permiso para esto." } } });
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    expect(await screen.findByText("No tiene permiso para esto.")).toBeInTheDocument();
  });

  it("un error de validación DRF { campo: [mensajes] } arma un resumen legible", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      response: { data: { id_riesgo: ["Ya existe un registro con este plan e id_riesgo."] } },
    });
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    expect(await screen.findByText(/id_riesgo: Ya existe un registro/)).toBeInTheDocument();
  });

  it("un error sin cuerpo de respuesta (ej. sin conexión) muestra un mensaje genérico", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("Network Error"));
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    expect(await screen.findByText(/No fue posible guardar/)).toBeInTheDocument();
  });

  it("un error de string plano se muestra tal cual", async () => {
    const onSubmit = vi.fn().mockRejectedValue({ response: { data: "Error interno del servidor" } });
    render(<EntityForm fields={[{ name: "nombre", label: "Nombre" }]} onSubmit={onSubmit} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByText("Guardar"));

    expect(await screen.findByText("Error interno del servidor")).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GenerarAccionModal from "./GenerarAccionModal";
import endpoints from "../api/endpoints";

vi.mock("../api/endpoints", () => ({
  default: {
    planesTratamiento: vi.fn(),
    controlesIso: vi.fn(),
    crearAccion: vi.fn(),
  },
}));

// EntityForm es un componente genérico y reusado por casi toda la app — su
// propio comportamiento (validación, tipos de campo, catálogos) merece su
// archivo de pruebas aparte. Acá se simula con un doble mínimo que expone
// justo lo que GenerarAccionModal le entrega, para verificar ESO sin
// reimplementar EntityForm ni acoplarse a su render interno.
vi.mock("./EntityForm", () => ({
  default: ({ fields, initialValues, onSubmit }) => (
    <div data-testid="entity-form">
      <pre data-testid="valores-iniciales">{JSON.stringify(initialValues)}</pre>
      <pre data-testid="nombres-de-campos">{JSON.stringify(fields.map((f) => f.name))}</pre>
      <button onClick={() => onSubmit(initialValues)}>Guardar (con los valores iniciales tal cual)</button>
      {/* Un <select> real entrega el value del plan como string ("7"), no
          number — este botón lo simula para poder probar la conversión
          Number() que hace guardar() antes de mandar el payload. */}
      <button onClick={() => onSubmit({ ...initialValues, plan: "7" })}>
        Guardar (con plan elegido como string, como lo entregaría un select real)
      </button>
    </div>
  ),
}));

const UN_PLAN = { id: 7, referencia: "SUIIN-SGSI-PTR-001 v1.0" };

function mockPlanesYControles({ planes = [UN_PLAN] } = {}) {
  endpoints.planesTratamiento.mockResolvedValue({ data: { results: planes } });
  endpoints.controlesIso.mockResolvedValue({ data: { results: [] } });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("GenerarAccionModal — no se muestra nada sin abrir o sin origen", () => {
  it("no renderiza si open es false", async () => {
    mockPlanesYControles();
    const { container } = render(
      <GenerarAccionModal open={false} onClose={vi.fn()} origen={null} onCreated={vi.fn()} />
    );
    // useApiData sigue disparando su efecto aunque open sea false (el
    // fetcher pasa a resolver null) — se espera a que esa actualización de
    // estado interna termine antes de afirmar sobre el render.
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

describe("GenerarAccionModal — sin ningún PTR creado todavía", () => {
  it("muestra el aviso de crear un PTR primero, no el formulario", async () => {
    mockPlanesYControles({ planes: [] });
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "vulnerabilidad", objeto: { id: 1, nombre_vulnerabilidad: "x", probabilidad: 3, impacto: 3 } }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByText(/Aún no hay ningún Plan de Tratamiento/)).toBeInTheDocument());
    expect(screen.queryByTestId("entity-form")).not.toBeInTheDocument();
  });
});

describe("GenerarAccionModal — precarga de campos según el origen", () => {
  it("origen vulnerabilidad: usa el nombre del hallazgo y la solución recomendada", async () => {
    mockPlanesYControles();
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{
          tipo: "vulnerabilidad",
          objeto: {
            id: 42, nombre_vulnerabilidad: "TLS débil", probabilidad: 5, impacto: 4,
            solucion_recomendada: "Deshabilitar TLSv1.0/1.1",
          },
        }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    const valores = JSON.parse(screen.getByTestId("valores-iniciales").textContent);
    expect(valores.descripcion_riesgo).toBe("TLS débil");
    expect(valores.acciones_tratamiento).toBe("Deshabilitar TLSv1.0/1.1");
    expect(valores.probabilidad).toBe(5);
    expect(valores.impacto).toBe(4);
    expect(valores.responsable).toBe(""); // vulnerabilidad no trae responsable propio
    expect(screen.getByText(/Origen: TLS débil/)).toBeInTheDocument();
  });

  it("origen riesgo_activo: usa la justificación, controles_accion y responsable_sugerido", async () => {
    mockPlanesYControles();
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{
          tipo: "riesgo_activo",
          objeto: {
            id: 9, id_riesgo: "R-05", justificacion: "Switch sin gestión expuesto", probabilidad: 4, impacto: 4,
            controles_accion: "Segmentar VLAN", responsable_sugerido: "Coordinación técnica",
          },
        }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    const valores = JSON.parse(screen.getByTestId("valores-iniciales").textContent);
    expect(valores.descripcion_riesgo).toBe("Switch sin gestión expuesto");
    expect(valores.acciones_tratamiento).toBe("Segmentar VLAN");
    expect(valores.responsable).toBe("Coordinación técnica");
    expect(screen.getByText(/Origen: R-05/)).toBeInTheDocument();
  });

  it("origen riesgo_activo sin justificación: arma una descripción con el id_riesgo", async () => {
    mockPlanesYControles();
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "riesgo_activo", objeto: { id: 9, id_riesgo: "R-06", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    const valores = JSON.parse(screen.getByTestId("valores-iniciales").textContent);
    expect(valores.descripcion_riesgo).toBe("Riesgo agregado R-06");
  });

  it("origen riesgo_contextual: usa escenario_amenaza, accion_mitigacion y responsable", async () => {
    mockPlanesYControles();
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{
          tipo: "riesgo_contextual",
          objeto: {
            id: 3, id_riesgo_contextual: "RC-03", escenario_amenaza: "Ingeniería social", probabilidad: 5, impacto: 5,
            accion_mitigacion: "Capacitar al personal", responsable: "Coordinación UAIIN",
          },
        }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    const valores = JSON.parse(screen.getByTestId("valores-iniciales").textContent);
    expect(valores.descripcion_riesgo).toBe("Ingeniería social");
    expect(valores.acciones_tratamiento).toBe("Capacitar al personal");
    expect(valores.responsable).toBe("Coordinación UAIIN");
    expect(screen.getByText(/Origen: RC-03/)).toBeInTheDocument();
  });
});

describe("GenerarAccionModal — valores por defecto (regresión del bug real)", () => {
  it.each(["vulnerabilidad", "riesgo_activo", "riesgo_contextual"])(
    "origen %s: precarga opcion_tratamiento, fase, estado y porcentaje_avance",
    async (tipo) => {
      // Bug real: el formulario no traía valor por defecto para estos cuatro
      // campos, aunque el modelo (AccionTratamiento en models.py) sí los
      // tiene — el guardado fallaba con "no es una elección válida" para los
      // tres orígenes por igual hasta que alguien los llenaba a mano. Se
      // descubrió recién al probar el flujo de riesgo_contextual de punta a
      // punta, pero afectaba a los tres desde siempre.
      mockPlanesYControles();
      render(
        <GenerarAccionModal
          open
          onClose={vi.fn()}
          origen={{ tipo, objeto: { id: 1, id_riesgo: "R-01", id_riesgo_contextual: "RC-01", probabilidad: 1, impacto: 1 } }}
          onCreated={vi.fn()}
        />
      );

      await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
      const valores = JSON.parse(screen.getByTestId("valores-iniciales").textContent);
      expect(valores.opcion_tratamiento).toBe("MITIGAR");
      expect(valores.fase).toBe("FASE_1");
      expect(valores.estado).toBe("PENDIENTE");
      expect(valores.porcentaje_avance).toBe(0);
    }
  );
});

describe("GenerarAccionModal — guardar() arma el payload con el origen correcto", () => {
  it("origen vulnerabilidad: solo origen_vulnerabilidad va con el id, los otros dos van null", async () => {
    mockPlanesYControles();
    endpoints.crearAccion.mockResolvedValue({ data: {} });
    const onCreated = vi.fn();
    const onClose = vi.fn();

    render(
      <GenerarAccionModal
        open
        onClose={onClose}
        origen={{ tipo: "vulnerabilidad", objeto: { id: 55, nombre_vulnerabilidad: "x", probabilidad: 1, impacto: 1 } }}
        onCreated={onCreated}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Guardar (con los valores iniciales tal cual)"));

    await waitFor(() => expect(endpoints.crearAccion).toHaveBeenCalledTimes(1));
    const payload = endpoints.crearAccion.mock.calls[0][0];
    expect(payload.origen_vulnerabilidad).toBe(55);
    expect(payload.origen_riesgo_activo).toBeNull();
    expect(payload.origen_riesgo_contextual).toBeNull();
    expect(onCreated).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("origen riesgo_activo: solo origen_riesgo_activo va con el id", async () => {
    mockPlanesYControles();
    endpoints.crearAccion.mockResolvedValue({ data: {} });

    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "riesgo_activo", objeto: { id: 77, id_riesgo: "R-01", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Guardar (con los valores iniciales tal cual)"));

    await waitFor(() => expect(endpoints.crearAccion).toHaveBeenCalledTimes(1));
    const payload = endpoints.crearAccion.mock.calls[0][0];
    expect(payload.origen_riesgo_activo).toBe(77);
    expect(payload.origen_vulnerabilidad).toBeNull();
    expect(payload.origen_riesgo_contextual).toBeNull();
  });

  it("origen riesgo_contextual: solo origen_riesgo_contextual va con el id", async () => {
    mockPlanesYControles();
    endpoints.crearAccion.mockResolvedValue({ data: {} });

    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "riesgo_contextual", objeto: { id: 3, id_riesgo_contextual: "RC-03", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Guardar (con los valores iniciales tal cual)"));

    await waitFor(() => expect(endpoints.crearAccion).toHaveBeenCalledTimes(1));
    const payload = endpoints.crearAccion.mock.calls[0][0];
    expect(payload.origen_riesgo_contextual).toBe(3);
    expect(payload.origen_vulnerabilidad).toBeNull();
    expect(payload.origen_riesgo_activo).toBeNull();
  });

  it("convierte a número el plan elegido (un <select> real entrega el value como string)", async () => {
    mockPlanesYControles();
    endpoints.crearAccion.mockResolvedValue({ data: {} });

    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "vulnerabilidad", objeto: { id: 1, nombre_vulnerabilidad: "x", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );
    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());

    await userEvent.click(
      screen.getByText("Guardar (con plan elegido como string, como lo entregaría un select real)")
    );

    await waitFor(() => expect(endpoints.crearAccion).toHaveBeenCalledTimes(1));
    const payload = endpoints.crearAccion.mock.calls[0][0];
    expect(payload.plan).toBe(7);
    expect(typeof payload.plan).toBe("number");
  });

  it("el formulario expuesto incluye el campo 'plan'", async () => {
    mockPlanesYControles();
    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "vulnerabilidad", objeto: { id: 1, nombre_vulnerabilidad: "x", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );
    await waitFor(() => expect(screen.getByTestId("entity-form")).toBeInTheDocument());
    const nombresDeCampos = JSON.parse(screen.getByTestId("nombres-de-campos").textContent);
    expect(nombresDeCampos).toContain("plan");
  });
});

describe("GenerarAccionModal — plan y controles ISO llegan como opciones al formulario", () => {
  it("expone el plan real como opción seleccionable", async () => {
    mockPlanesYControles({ planes: [UN_PLAN, { id: 8, referencia: "SUIIN-SGSI-PTR-002" }] });

    render(
      <GenerarAccionModal
        open
        onClose={vi.fn()}
        origen={{ tipo: "vulnerabilidad", objeto: { id: 1, nombre_vulnerabilidad: "x", probabilidad: 1, impacto: 1 } }}
        onCreated={vi.fn()}
      />
    );

    await waitFor(() => expect(endpoints.planesTratamiento).toHaveBeenCalled());
    // El propio EntityForm (real) es quien decide cómo pintar el <select> de
    // "plan" con esas opciones — acá solo se confirma que la llamada a la API
    // que las provee ocurrió con los parámetros esperados.
    expect(endpoints.planesTratamiento).toHaveBeenCalledWith({ page_size: 100 });
  });
});

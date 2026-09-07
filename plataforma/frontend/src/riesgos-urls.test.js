import { describe, it, expect, afterEach } from "vitest";
import { enPlataformaUnificada, resolverBaseRiesgos, resolverBaseInventario } from "@riesgos/api/urls";

describe("urls — plataforma unificada", () => {
  const pathnameOriginal = window.location.pathname;

  afterEach(() => {
    window.history.replaceState({}, "", pathnameOriginal || "/");
  });

  it("detecta modo unificado por ruta /gestion-riesgos", () => {
    window.history.replaceState({}, "", "/gestion-riesgos");
    expect(enPlataformaUnificada()).toBe(true);
    expect(resolverBaseRiesgos()).toBe("/riesgos/api");
    expect(resolverBaseInventario()).toBe("/api");
  });
});

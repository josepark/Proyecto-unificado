import { useState } from "react";
import CatalogoCombobox from "./CatalogoCombobox";
import MitreMultiSelect from "./MitreMultiSelect";

/**
 * Renderiza un formulario a partir de un esquema declarativo de campos.
 * field: { name, label, type, required?, options?, help?, min?, max?, full?, section? }
 * type ∈ 'text' | 'textarea' | 'number' | 'select' | 'checkbox' | 'date' | 'multiselect'
 */
export default function EntityForm({ fields, initialValues = {}, onSubmit, onCancel, submitLabel = "Guardar" }) {
  const [values, setValues] = useState(() => ({ ...defaultsFor(fields), ...initialValues }));
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  function setField(name, value) {
    setValues((v) => ({ ...v, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit(sanitize(values, fields));
    } catch (err) {
      setError(readError(err));
    } finally {
      setSaving(false);
    }
  }

  const sections = groupBySection(fields);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {sections.map(([section, sectionFields]) => (
        <div key={section}>
          {section !== "_default" && (
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-cric-gold-400">
              {section}
            </p>
          )}
          <div className="grid grid-cols-2 gap-x-4 gap-y-4">
            {sectionFields.map((f) => (
              <FieldInput key={f.name} field={f} value={values[f.name]} onChange={(v) => setField(f.name, v)} />
            ))}
          </div>
        </div>
      ))}

      {error && (
        <p className="rounded-lg border border-[#e0475a]/40 bg-[#e0475a]/10 px-3 py-2 text-[12px] text-[#e0475a]">
          {error}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 border-t border-base-700/60 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-4 py-2 text-sm font-medium text-base-300 hover:text-base-100"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-cric-green-600 px-4 py-2 text-sm font-medium text-base-100 transition-colors hover:bg-cric-green-500 disabled:opacity-60"
        >
          {saving ? "Guardando…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

function FieldInput({ field, value, onChange }) {
  const span = field.full || ["textarea", "multiselect"].includes(field.type) ? "col-span-2" : "col-span-1";
  const baseInput =
    "w-full rounded-lg border border-base-700/60 bg-base-850/60 px-3 py-2 text-sm text-base-100 outline-none focus:border-cric-green-500";
  // Asocia la etiqueta con su control por id — sin esto, un lector de
  // pantalla no anuncia el campo correctamente, hacer clic en la etiqueta no
  // enfoca el control, y las pruebas por getByLabelText no encuentran nada
  // (hallazgo real al escribir la primera prueba de este componente).
  const id = `campo-${field.name}`;

  if (field.type === "checkbox") {
    return (
      <label htmlFor={id} className={`${span} flex items-center gap-2.5 pt-1 text-sm text-base-100`}>
        <input
          id={id}
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-base-600 bg-base-850 accent-cric-green-500"
        />
        {field.label}
      </label>
    );
  }

  return (
    <div className={span}>
      <label htmlFor={id} className="mb-1 flex items-center justify-between text-[12px] font-medium text-base-300">
        <span>
          {field.label}
          {field.required && <span className="ml-0.5 text-[#e0475a]">*</span>}
        </span>
        {field.help && <span className="text-[10px] font-normal text-base-300/60">{field.help}</span>}
      </label>

      {field.type === "textarea" && (
        <textarea
          id={id}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          rows={field.rows || 3}
          className={`${baseInput} resize-y`}
        />
      )}

      {field.type === "select" && (
        <select
          id={id}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          className={baseInput}
        >
          <option value="">—</option>
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )}

      {field.type === "multiselect" && (
        <select
          id={id}
          multiple
          value={(value ?? []).map(String)}
          onChange={(e) => onChange(Array.from(e.target.selectedOptions, (o) => o.value))}
          className={`${baseInput} h-28`}
        >
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )}

      {field.type === "number" && (
        <input
          id={id}
          type="number"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          required={field.required}
          min={field.min}
          max={field.max}
          step={field.step || 1}
          className={`${baseInput} font-mono-data`}
        />
      )}

      {field.type === "date" && (
        <input
          id={id}
          type="date"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          className={`${baseInput} font-mono-data`}
        />
      )}

      {field.type === "mitre" && (
        <MitreMultiSelect
          value={value}
          onChange={onChange}
          separador={field.separador || "/"}
          placeholder={field.placeholder}
        />
      )}

      {field.type === "catalogo" && (
        <CatalogoCombobox
          categoria={field.categoria}
          value={value}
          onChange={onChange}
          placeholder={field.placeholder}
          multiline={field.multiline}
        />
      )}

      {(!field.type || field.type === "text") && (
        <input
          id={id}
          type="text"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          placeholder={field.placeholder}
          className={baseInput}
        />
      )}
    </div>
  );
}

function defaultsFor(fields) {
  const d = {};
  for (const f of fields) {
    d[f.name] = f.type === "checkbox" ? false : f.type === "multiselect" ? [] : "";
  }
  return d;
}

/**
 * Convierte cadenas vacías a null para campos donde el backend espera un valor
 * ausente real (fechas, números, selects que representan una FK numérica) — un
 * <select> o <input> vacío en HTML siempre produce "", nunca null.
 */
function sanitize(values, fields) {
  const out = { ...values };
  for (const f of fields) {
    const v = out[f.name];
    if (v === "" && (f.type === "date" || f.type === "number" || f.fkId)) {
      out[f.name] = null;
    }
    if (f.type === "number" && typeof v === "string" && v !== "") {
      out[f.name] = Number(v);
    }
    if (f.type === "multiselect" && Array.isArray(v)) {
      out[f.name] = v.map(Number);
    }
  }
  return out;
}

function groupBySection(fields) {
  const map = new Map();
  for (const f of fields) {
    const key = f.section || "_default";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(f);
  }
  return Array.from(map.entries());
}

function readError(err) {
  const data = err?.response?.data;
  if (!data) return "No fue posible guardar. Verifique su conexión con el backend.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  // DRF ValidationError: { campo: ["mensaje"] }
  const primeros = Object.entries(data)
    .slice(0, 3)
    .map(([campo, msgs]) => `${campo}: ${Array.isArray(msgs) ? msgs[0] : msgs}`);
  return primeros.join(" · ") || "Error de validación.";
}

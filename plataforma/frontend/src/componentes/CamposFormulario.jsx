/** Componentes de campo compartidos por todos los formularios de escritura
 * (ActivoForm, RolForm, UsuarioForm, SistemaForm, DatacenterForm) — mismo
 * estilo visual, una sola vez.
 *
 * useId() vincula cada <label> con su control (htmlFor/id): antes no
 * había asociación programática entre ambos — invisible a simple vista,
 * pero un lector de pantalla no podía anunciar la etiqueta al enfocar el
 * campo, y las pruebas con Testing Library no podían ubicar los campos
 * por su etiqueta (getByLabelText), que es la forma recomendada de
 * probar formularios. Lo detectó la propia suite de pruebas al escribirla. */
import { useId } from 'react';

export function Campo({ label, id: idProp, style, ...props }) {
  const idGenerado = useId();
  const id = idProp || idGenerado;
  return (
    <div>
      <label htmlFor={id} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
        {label}
      </label>
      <input id={id} style={{ width: '100%', ...style }} {...props} />
    </div>
  );
}

export function CampoSelect({ label, opciones, id: idProp, style, ...props }) {
  const idGenerado = useId();
  const id = idProp || idGenerado;
  return (
    <div>
      <label htmlFor={id} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
        {label}
      </label>
      <select id={id} style={{ width: '100%', ...style }} {...props}>
        {opciones.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}

export function CampoTextarea({ label, id: idProp, style, ...props }) {
  const idGenerado = useId();
  const id = idProp || idGenerado;
  return (
    <div>
      <label htmlFor={id} style={{ display: 'block', fontSize: 12, color: 'var(--texto-suave)', marginBottom: 3 }}>
        {label}
      </label>
      <textarea id={id} style={{ width: '100%', ...style }} {...props} />
    </div>
  );
}

export function Fila({ children, columnas = 2 }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${columnas}, 1fr)`, gap: 12, marginBottom: 12 }}>
      {children}
    </div>
  );
}

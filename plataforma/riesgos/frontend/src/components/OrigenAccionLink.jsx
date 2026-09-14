import { Link } from "react-router-dom";
import { Link2 } from "lucide-react";
import { usePlataforma } from "../context/PlataformaContext";
import { etiquetaOrigenAccion, rutaOrigenAccion } from "../lib/rutasOrigen";

export default function OrigenAccionLink({ accion }) {
  const plataforma = usePlataforma();
  const etiqueta = etiquetaOrigenAccion(accion);
  const ruta = rutaOrigenAccion(plataforma.anidado, plataforma.prefijo, accion);
  if (!etiqueta) return null;

  if (!ruta) {
    return (
      <p className="mt-1.5 flex items-center gap-1 text-[11px] text-cric-gold-400/90">
        <Link2 className="h-3 w-3" /> Generada desde: {etiqueta}
      </p>
    );
  }

  return (
    <p className="mt-1.5 flex items-center gap-1 text-[11px] text-cric-gold-400/90">
      <Link2 className="h-3 w-3" />
      Generada desde:{" "}
      <Link to={ruta} className="font-medium text-cric-gold-400 hover:underline">
        {etiqueta}
      </Link>
    </p>
  );
}

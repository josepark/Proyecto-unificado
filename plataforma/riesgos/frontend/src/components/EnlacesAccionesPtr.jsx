import { Link } from "react-router-dom";
import { ClipboardList } from "lucide-react";
import { usePlataforma } from "../context/PlataformaContext";
import { rutaPlanTratamiento } from "../lib/rutasOrigen";

export default function EnlacesAccionesPtr({ acciones = [] }) {
  const plataforma = usePlataforma();
  if (!acciones.length) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {acciones.map((a) => (
        <Link
          key={a.id}
          to={rutaPlanTratamiento(plataforma.anidado, plataforma.prefijo, { planId: a.plan_id, accionId: a.id })}
          className="inline-flex items-center gap-1 rounded-md bg-base-800/80 px-2 py-0.5 font-mono-data text-[11px] text-cric-gold-400 hover:underline"
        >
          <ClipboardList className="h-3 w-3" />
          {a.id_riesgo} · {a.plan_referencia}
        </Link>
      ))}
    </div>
  );
}

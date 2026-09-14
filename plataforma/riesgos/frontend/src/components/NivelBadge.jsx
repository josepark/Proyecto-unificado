import { nivelInfo } from "../lib/risk";

export default function NivelBadge({ nivel, size = "md" }) {
  const info = nivelInfo(nivel);
  const sizeClasses = size === "sm" ? "text-[11px] px-2 py-0.5" : "text-xs px-2.5 py-1";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-mono-data font-medium uppercase tracking-wide ${info.text} ${info.bg} ${info.border} ${sizeClasses}`}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: info.color }}
      />
      {info.label}
    </span>
  );
}

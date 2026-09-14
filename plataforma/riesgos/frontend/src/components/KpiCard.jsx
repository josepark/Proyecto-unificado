export default function KpiCard({ label, value, sub, accent = "green", icon: Icon }) {
  const accentColor = {
    green: "text-cric-green-400",
    gold: "text-cric-gold-400",
    critico: "text-[#e0475a]",
    alto: "text-[#e0812f]",
  }[accent];

  return (
    <div className="rounded-2xl border border-base-700/60 bg-base-900/60 p-5 backdrop-blur-sm">
      <div className="flex items-start justify-between">
        <p className="text-[13px] font-medium text-base-300">{label}</p>
        {Icon && <Icon className={`h-4 w-4 ${accentColor}`} strokeWidth={2} />}
      </div>
      <p className={`mt-2 font-display text-3xl font-semibold ${accentColor}`}>
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-base-300/80">{sub}</p>}
    </div>
  );
}

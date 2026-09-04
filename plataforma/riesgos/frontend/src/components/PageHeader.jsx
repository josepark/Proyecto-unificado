export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-cric-gold-400">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-2xl font-semibold text-base-100">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-base-300">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

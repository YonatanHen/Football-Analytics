interface Option<T extends string> { value: T; label: string }

export default function Segmented<T extends string>({
  options, value, onChange, size = 'md', mono = false,
}: {
  options: Option<T>[]; value: T | null; onChange: (v: T) => void
  size?: 'sm' | 'md'; mono?: boolean
}) {
  const h = size === 'sm' ? 'h-8 text-xs' : 'h-9 text-sm'
  return (
    <div className="inline-flex rounded-md border border-line bg-surface p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`${h} ${mono ? 'font-mono' : ''} rounded px-3.5 transition-colors ${
            value === o.value ? 'bg-accent-deep text-white' : 'text-muted hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

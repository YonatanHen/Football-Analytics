import { X } from 'lucide-react'

export default function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex h-8 items-center gap-2 rounded-md border border-accent-deep/70 bg-accent-soft pl-2.5 pr-1.5 font-mono text-xs text-accent">
      {label}
      <button onClick={onRemove} aria-label={`Remove ${label}`} className="rounded p-0.5 hover:bg-accent-deep/40">
        <X size={12} />
      </button>
    </span>
  )
}

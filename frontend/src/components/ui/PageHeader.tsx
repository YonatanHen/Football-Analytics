import type { ReactNode } from 'react'

export default function PageHeader({
  title, subtitle, right,
}: { title: string; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1.5 font-mono text-[11px] text-muted">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0 text-right">{right}</div>}
    </div>
  )
}

export const Dot = () => <span className="mx-3 text-dim">·</span>

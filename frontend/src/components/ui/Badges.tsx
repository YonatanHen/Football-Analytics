import type { ReactNode } from 'react'
import { Star } from 'lucide-react'
import type { Flag } from '../../api/players'

const FLAG_LABEL: Record<Flag, string> = {
  HIGH_VALUE: 'Due to score',
  OVERPERFORMING: 'Overperforming',
}

const POS_TONE: Record<string, string> = { GK: 'text-warn', DF: 'text-info', MF: 'text-muted' }

export function PosBadge({ pos }: { pos: string }) {
  return (
    <span
      className={`inline-flex h-5 min-w-[26px] items-center justify-center rounded bg-surface-2 px-1 font-mono text-[10px] ${POS_TONE[pos] ?? 'text-accent'}`}
    >
      {pos || '—'}
    </span>
  )
}

export function FlagBadge({ flag }: { flag: Flag }) {
  const tone = flag === 'HIGH_VALUE' ? 'bg-warn-soft text-warn' : 'bg-accent-soft text-accent'
  return (
    <span className={`inline-flex h-6 items-center whitespace-nowrap rounded px-2 font-mono text-[10px] uppercase tracking-[0.12em] ${tone}`}>
      {FLAG_LABEL[flag]}
    </span>
  )
}

export function TotwBadge({ count }: { count: number }) {
  return (
    <span className="inline-flex h-6 items-center gap-1 whitespace-nowrap rounded bg-info-soft px-2 font-mono text-[10px] uppercase tracking-[0.08em] text-info">
      <Star size={11} /> TOTW ×{count}
    </span>
  )
}

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-7 items-center rounded bg-surface-2 px-2.5 font-mono text-[11px] text-ink">
      {children}
    </span>
  )
}

export function CompTag({ national }: { national: boolean }) {
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] tracking-[0.1em] ${national ? 'bg-info-soft text-info' : 'bg-surface-2 text-dim'}`}>
      {national ? 'NT' : 'CLUB'}
    </span>
  )
}

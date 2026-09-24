import type { ReactNode } from 'react'

export default function StatRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-line py-2 text-[13px]">
      <span className="text-ink/90">{label}</span>
      <span className="font-mono text-ink">{value}</span>
    </div>
  )
}

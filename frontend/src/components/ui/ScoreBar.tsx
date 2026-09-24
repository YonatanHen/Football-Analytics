// Value above a thin progress track, as in the ranking tables.
export default function ScoreBar({
  label, fraction, tone = 'accent',
}: { label: string; fraction: number; tone?: 'accent' | 'warn' }) {
  const text = tone === 'warn' ? 'text-warn' : 'text-accent'
  const fill = tone === 'warn' ? 'bg-warn' : 'bg-accent'
  const pct = Math.max(0, Math.min(1, fraction)) * 100
  return (
    <div className="w-32">
      <div className={`font-mono text-sm ${text}`}>{label}</div>
      <div className="mt-1 h-[3px] w-full rounded bg-line-strong">
        <div className={`h-full rounded ${fill}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

interface Segment { label: string; value: number; color: string }

export default function StackedBar({
  title, total, segments,
}: { title: string; total: number; segments: Segment[] }) {
  const sum = segments.reduce((n, s) => n + s.value, 0) || 1
  return (
    <div>
      <div className="label-caps mb-3">
        {title} <span className="mx-2">·</span> {total} total
      </div>
      <div className="flex h-2 w-full gap-[2px] overflow-hidden rounded-sm">
        {segments.filter((s) => s.value > 0).map((s) => (
          <div key={s.label} style={{ width: `${(s.value / sum) * 100}%`, background: s.color }} />
        ))}
      </div>
      <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {segments.map((s) => (
          <span key={s.label} className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
            {s.label} <span className="font-mono text-ink">{s.value}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

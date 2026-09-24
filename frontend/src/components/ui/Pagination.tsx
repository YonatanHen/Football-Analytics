import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({
  page, pageSize, total, shown, onPage,
}: { page: number; pageSize: number; total: number; shown: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.max(from, from + shown - 1)
  return (
    <div className="mt-6 flex items-center justify-between">
      <span className="font-mono text-xs text-muted">
        Showing {from}–{to} of {total.toLocaleString('en-US')}
      </span>
      <div className="flex items-center gap-4">
        <button
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink disabled:cursor-not-allowed disabled:text-dim"
        >
          <ChevronLeft size={14} /> Prev
        </button>
        <span className="font-mono text-sm text-ink">
          {page} <span className="text-muted">/</span> {pages}
        </span>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="btn-ghost">
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}

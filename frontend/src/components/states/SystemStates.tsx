import { useState } from 'react'
import { ArrowUpRight, Copy, Database, RefreshCw, SearchX, WifiOff } from 'lucide-react'
import { API_DOCS_URL } from '../../api/meta'

const CLI_STEPS = [
  { cmd: 'python -m fetch_cli.cli refresh', note: 'pull the competition / season catalog' },
  { cmd: 'python -m fetch_cli.cli browse', note: 'see what is available' },
  { cmd: 'python -m fetch_cli.cli fetch', note: 'pick a league + season, load it' },
]

export function EmptyDatabase({ onRetry }: { onRetry: () => void }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(CLI_STEPS.map((s) => s.cmd).join('\n')).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-line-strong bg-surface">
        <Database size={22} className="text-muted" />
      </div>
      <h2 className="mt-6 text-2xl font-semibold tracking-tight">No data loaded yet</h2>
      <p className="mt-4 max-w-lg text-center text-sm leading-relaxed text-muted">
        The database is empty. Loading is developer-driven — run the fetch CLI against the running
        backend to pull a competition and season into MongoDB.
      </p>
      <div className="mt-6 w-full max-w-3xl overflow-hidden rounded-lg border border-line-strong bg-surface">
        <div className="flex items-center justify-between border-b border-line bg-surface-2 px-4 py-2.5">
          <span className="font-mono text-[11px] text-dim">tools/</span>
          <button onClick={copy} className="inline-flex items-center gap-1 text-xs text-muted hover:text-ink">
            <Copy size={12} /> {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <div className="space-y-2 px-4 py-4 font-mono text-[13px]">
          {CLI_STEPS.map((s) => (
            <div key={s.cmd} className="flex items-center justify-between gap-6">
              <span><span className="mr-3 text-accent-deep">$</span>{s.cmd}</span>
              <span className="hidden text-[11px] text-dim md:inline"># {s.note}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-6 flex gap-3">
        <a href={API_DOCS_URL} target="_blank" rel="noreferrer" className="btn-solid h-10 px-5">
          Open API docs <ArrowUpRight size={15} />
        </a>
        <button onClick={onRetry} className="btn-ghost h-10 px-5 text-muted">
          <RefreshCw size={14} /> Check again
        </button>
      </div>
    </div>
  )
}

export function BackendUnreachable({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center text-center">
      <WifiOff size={26} className="text-danger" />
      <h2 className="mt-4 text-xl font-semibold text-danger">Backend unreachable</h2>
      <p className="mt-3 max-w-md text-sm text-muted">
        Cannot reach the API. Make sure the backend is running.
      </p>
      <p className="mt-2 font-mono text-[11px] text-dim">retrying every 10s</p>
      <button onClick={onRetry} className="btn-ghost mt-5 h-10 px-5">
        <RefreshCw size={14} /> Retry now
      </button>
    </div>
  )
}

export function NoResults({
  active, onClearAll, onRemoveLast,
}: { active: string[]; onClearAll: () => void; onRemoveLast?: () => void }) {
  return (
    <div className="flex flex-col items-center py-20 text-center">
      <SearchX size={24} className="text-warn" />
      <h3 className="mt-3 text-base font-semibold text-warn">No results</h3>
      <p className="mt-2 text-sm text-muted">No players match this search.</p>
      {active.length > 0 && (
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {active.map((a) => (
            <span key={a} className="rounded bg-surface-2 px-2 py-1 font-mono text-[11px] text-ink">{a}</span>
          ))}
        </div>
      )}
      <div className="mt-5 flex gap-4 font-mono text-[11px]">
        <button onClick={onClearAll} className="text-accent hover:underline">clear all filters</button>
        {onRemoveLast && (
          <button onClick={onRemoveLast} className="text-muted hover:text-ink hover:underline">remove last clause</button>
        )}
      </div>
    </div>
  )
}

export function TableSkeleton({ rows = 10 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg">
      <div className="h-11 bg-surface" />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-[46px] items-center gap-6 border-b border-line px-4">
          <div className="h-2.5 w-5 animate-pulse rounded bg-surface-2" />
          <div className="h-7 w-7 animate-pulse rounded-full bg-surface-2" />
          <div className="h-2.5 w-40 animate-pulse rounded bg-surface-2" />
          <div className="h-2.5 flex-1 animate-pulse rounded bg-surface-2" />
        </div>
      ))}
    </div>
  )
}

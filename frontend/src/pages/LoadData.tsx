import { useState, useEffect, useRef } from 'react'
import {
  triggerFetch, getFetchStatus, getCompetitions,
  type FetchJobStatus, type FetchTask,
} from '../api/fetch'

const SEASONS = ['2025-2026', '2024-2025', '2023-2024']
const POLL_MS = 3000

function TaskIcon({ status }: { status: FetchTask['status'] }) {
  if (status === 'done') return <span className="text-green-400 w-4 shrink-0">✓</span>
  if (status === 'failed') return <span className="text-red-400 w-4 shrink-0">✗</span>
  if (status === 'running') return <span className="text-indigo-400 w-4 shrink-0 animate-spin inline-block">⟳</span>
  return <span className="text-gray-600 w-4 shrink-0">·</span>
}

type PageStatus = 'idle' | 'running' | 'done' | 'partial' | 'error'

export default function LoadData({ onDone }: { onDone?: () => void } = {}) {
  const [competitions, setCompetitions] = useState<string[]>([])
  const [compsLoading, setCompsLoading] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [season, setSeason] = useState(SEASONS[0])

  const [pageStatus, setPageStatus] = useState<PageStatus>('idle')
  const [jobStatus, setJobStatus] = useState<FetchJobStatus | null>(null)
  const [resultMsg, setResultMsg] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    getCompetitions()
      .then(list => { setCompetitions(list); setSelected(list[0] ?? '') })
      .catch(() => setCompetitions([]))
      .finally(() => setCompsLoading(false))
  }, [])

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleFetch = async () => {
    if (!selected) return
    setPageStatus('running')
    setJobStatus(null)
    setResultMsg('')

    try {
      const { job_id } = await triggerFetch({ mode: 'fantasy', season, competitions: [selected] })
      pollRef.current = setInterval(async () => {
        try {
          const status = await getFetchStatus(job_id)
          setJobStatus(status)
          if (status.status !== 'running') {
            clearInterval(pollRef.current!)
            pollRef.current = null
            setPageStatus(status.status as PageStatus)
            if (status.status === 'done') {
              setResultMsg(`Done — ${status.players_upserted.toLocaleString()} players loaded for ${selected}.`)
              onDone?.()
            } else if (status.status === 'partial') {
              setResultMsg(`${status.players_upserted.toLocaleString()} players loaded, but some data failed — see server logs.`)
            } else {
              setResultMsg('No data loaded — the fetch failed. You can try again.')
            }
          }
        } catch {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setPageStatus('error')
          setResultMsg('Lost connection to server.')
        }
      }, POLL_MS)
    } catch (e) {
      setPageStatus('error')
      setResultMsg(e instanceof Error ? e.message : 'Failed to start fetch. Check server logs.')
    }
  }

  const running = pageStatus === 'running'
  const total = jobStatus?.total ?? 1
  const done = jobStatus?.completed ?? 0
  const failed = jobStatus?.competitions_failed ?? 0
  const current = jobStatus?.current ?? ''
  const progress = total > 0 ? Math.round((done / total) * 100) : 0

  const msgColor =
    pageStatus === 'done' ? 'text-green-400' :
    pageStatus === 'partial' ? 'text-amber-400' :
    'text-red-400'

  return (
    <div className="max-w-md">
      <h1 className="text-xl font-bold mb-2">Load Data</h1>

      <p className="text-sm text-gray-400 mb-3">
        Load player data for a league. This takes a few minutes.
      </p>

      <p className="text-sm text-amber-300/80 mb-4">
        ⚠ Avoid running multiple fetches in quick succession for the same league — it may trigger rate-limiting.
      </p>

      <div className="mb-4">
        <label className="block text-xs text-gray-400 mb-1">Season</label>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          disabled={running}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm disabled:opacity-50"
        >
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="mb-5">
        <label className="block text-xs text-gray-400 mb-1">League</label>
        {compsLoading ? (
          <div className="text-sm text-gray-500 py-2">Loading leagues…</div>
        ) : competitions.length === 0 ? (
          <div className="text-sm text-red-400 py-2">Could not load league list.</div>
        ) : (
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={running}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm disabled:opacity-50"
          >
            {competitions.map(comp => <option key={comp} value={comp}>{comp}</option>)}
          </select>
        )}
      </div>

      {running && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span className="truncate max-w-xs">{current || 'Starting…'}</span>
            <span>{done} / {total}</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2 mb-2">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {failed > 0 && (
            <p className="text-xs text-amber-400 mb-2">{failed} failed so far — see server logs.</p>
          )}
          {jobStatus && jobStatus.tasks.length > 0 && (
            <div className="max-h-40 overflow-y-auto bg-gray-900 rounded p-2 space-y-0.5">
              {jobStatus.tasks.map((task: FetchTask, i: number) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <TaskIcon status={task.status} />
                  <span className={task.status === 'failed' ? 'text-red-400' : task.status === 'done' ? 'text-gray-400' : 'text-gray-200'}>
                    {task.label}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={handleFetch}
          disabled={running || !selected}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold"
        >
          {running ? 'Fetching…' : 'Fetch league'}
        </button>
        {resultMsg && !running && (
          <span className={`text-sm ${msgColor}`}>{resultMsg}</span>
        )}
      </div>
    </div>
  )
}

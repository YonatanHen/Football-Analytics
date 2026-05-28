import { useState, useEffect, useRef } from 'react'
import { triggerFetch, getFetchStatus, getCompetitions, type FetchJobStatus } from '../api/fetch'

const SEASONS = ['2025-2026', '2024-2025', '2023-2024']
const POLL_MS = 3000

type PageStatus = 'idle' | 'running' | 'done' | 'partial' | 'error'

export default function LoadData() {
  const [competitions, setCompetitions] = useState<string[]>([])
  const [compsLoading, setCompsLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [season, setSeason] = useState(SEASONS[0])

  const [pageStatus, setPageStatus] = useState<PageStatus>('idle')
  const [jobStatus, setJobStatus] = useState<FetchJobStatus | null>(null)
  const [resultMsg, setResultMsg] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    getCompetitions()
      .then(list => { setCompetitions(list); setSelected(new Set(list)) })
      .catch(() => setCompetitions([]))
      .finally(() => setCompsLoading(false))
  }, [])

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const toggle = (comp: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(comp) ? next.delete(comp) : next.add(comp)
      return next
    })
  }

  const toggleAll = () =>
    setSelected(prev => prev.size === competitions.length ? new Set() : new Set(competitions))

  const handleFetch = async () => {
    if (selected.size === 0) return
    setPageStatus('running')
    setJobStatus(null)
    setResultMsg('')

    try {
      const { job_id } = await triggerFetch({ mode: 'fantasy', season, competitions: [...selected] })
      pollRef.current = setInterval(async () => {
        try {
          const status = await getFetchStatus(job_id)
          setJobStatus(status)
          if (status.status !== 'running') {
            clearInterval(pollRef.current!)
            pollRef.current = null
            setPageStatus(status.status as PageStatus)
            if (status.status === 'done') {
              setResultMsg(`Done — ${status.players_upserted.toLocaleString()} players loaded for ${season}.`)
            } else if (status.status === 'partial') {
              setResultMsg(`${status.players_upserted.toLocaleString()} players loaded. ${status.competitions_failed} competition${status.competitions_failed !== 1 ? 's' : ''} failed — see server logs.`)
            } else {
              setResultMsg('No data loaded. Check server logs for details.')
            }
          }
        } catch {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setPageStatus('error')
          setResultMsg('Lost connection to server.')
        }
      }, POLL_MS)
    } catch {
      setPageStatus('error')
      setResultMsg('Failed to start fetch. Check server logs.')
    }
  }

  const running = pageStatus === 'running'
  const total = jobStatus?.total ?? selected.size
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

      <div className="mb-5">
        <label className="block text-xs text-gray-400 mb-1">Season</label>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          disabled={running}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm disabled:opacity-50"
        >
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <p className="text-sm text-gray-400 mb-4">
        Fetch player data for the selected competitions and store in the database.
        This takes a few minutes per competition.
      </p>

      <div className="bg-gray-900 rounded-lg p-4 mb-4">
        {compsLoading ? (
          <div className="text-sm text-gray-500 py-2">Loading competitions…</div>
        ) : competitions.length === 0 ? (
          <div className="text-sm text-red-400 py-2">Could not load competition list.</div>
        ) : (
          <>
            <label className="flex items-center gap-3 pb-3 mb-3 border-b border-gray-800 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.size === competitions.length}
                onChange={toggleAll}
                disabled={running}
                className="w-4 h-4 accent-indigo-500"
              />
              <span className="text-sm font-medium">All competitions</span>
            </label>
            {competitions.map(comp => (
              <label key={comp} className="flex items-center gap-3 py-1.5 cursor-pointer hover:text-white">
                <input
                  type="checkbox"
                  checked={selected.has(comp)}
                  onChange={() => toggle(comp)}
                  disabled={running}
                  className="w-4 h-4 accent-indigo-500"
                />
                <span className="text-sm text-gray-300">{comp}</span>
              </label>
            ))}
          </>
        )}
      </div>

      {running && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span className="truncate max-w-xs">{current || 'Starting…'}</span>
            <span>{done} / {total}</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {failed > 0 && (
            <p className="text-xs text-amber-400 mt-1">{failed} failed so far — see server logs.</p>
          )}
        </div>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={handleFetch}
          disabled={running || selected.size === 0}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 rounded-lg text-sm font-semibold"
        >
          {running ? 'Fetching…' : `Fetch ${selected.size} competition${selected.size !== 1 ? 's' : ''}`}
        </button>
        {resultMsg && !running && (
          <span className={`text-sm ${msgColor}`}>{resultMsg}</span>
        )}
      </div>
    </div>
  )
}

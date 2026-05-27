import { useState } from 'react'
import { triggerFetch } from '../api/fetch'

const ALL_COMPETITIONS = [
  'England Premier League',
  'UEFA Champions League',
  'Spain La Liga',
  'Germany Bundesliga',
  'Italy Serie A',
  'France Ligue 1',
]

const SEASONS = ['2025-2026', '2024-2025', '2023-2024']

type Status = 'idle' | 'loading' | 'done' | 'error'

export default function LoadData() {
  const [selected, setSelected] = useState<Set<string>>(new Set(ALL_COMPETITIONS))
  const [season, setSeason] = useState(SEASONS[0])
  const [status, setStatus] = useState<Status>('idle')
  const [message, setMessage] = useState('')

  const toggle = (comp: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(comp) ? next.delete(comp) : next.add(comp)
      return next
    })
  }

  const toggleAll = () => {
    setSelected(prev => prev.size === ALL_COMPETITIONS.length ? new Set() : new Set(ALL_COMPETITIONS))
  }

  const handleFetch = async () => {
    if (selected.size === 0) return
    setStatus('loading')
    setMessage('')
    try {
      const r = await triggerFetch({ mode: 'fantasy', season, competitions: [...selected] })
      const errors = (r as Record<string, unknown>).competition_errors as Record<string, string> | undefined
      if (errors && Object.keys(errors).length > 0) {
        const errList = Object.entries(errors).map(([c, e]) => `${c}: ${e}`).join('\n')
        setMessage(`${r.players_upserted ?? 0} players loaded. Errors:\n${errList}`)
        setStatus('error')
      } else {
        setMessage(`Done — ${r.players_upserted ?? 0} players loaded for ${r.season}.`)
        setStatus('done')
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Fetch failed')
      setStatus('error')
    }
  }

  const allChecked = selected.size === ALL_COMPETITIONS.length

  return (
    <div className="max-w-md">
      <h1 className="text-xl font-bold mb-2">Load Data</h1>

      <div className="mb-5">
        <label className="block text-xs text-gray-400 mb-1">Season</label>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
        >
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <p className="text-sm text-gray-400 mb-6">
        Scrape live data from Sofascore + FBref for the selected competitions and store in the database.
        This takes several minutes per competition.
      </p>

      <div className="bg-gray-900 rounded-lg p-4 mb-4">
        <label className="flex items-center gap-3 pb-3 mb-3 border-b border-gray-800 cursor-pointer">
          <input
            type="checkbox"
            checked={allChecked}
            onChange={toggleAll}
            className="w-4 h-4 accent-indigo-500"
          />
          <span className="text-sm font-medium">All competitions</span>
        </label>
        {ALL_COMPETITIONS.map(comp => (
          <label key={comp} className="flex items-center gap-3 py-2 cursor-pointer hover:text-white">
            <input
              type="checkbox"
              checked={selected.has(comp)}
              onChange={() => toggle(comp)}
              className="w-4 h-4 accent-indigo-500"
            />
            <span className="text-sm text-gray-300">{comp}</span>
          </label>
        ))}
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleFetch}
          disabled={status === 'loading' || selected.size === 0}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 rounded-lg text-sm font-semibold"
        >
          {status === 'loading' ? 'Scraping…' : `Fetch ${selected.size} competition${selected.size !== 1 ? 's' : ''}`}
        </button>
        {message && (
          <span className={`text-sm ${status === 'error' ? 'text-red-400' : 'text-green-400'}`}>
            {message}
          </span>
        )}
      </div>

      {status === 'loading' && (
        <p className="text-xs text-gray-500 mt-3">
          Please keep this tab open. Scraping each competition takes 1–3 minutes.
        </p>
      )}
    </div>
  )
}

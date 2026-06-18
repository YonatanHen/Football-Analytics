import { useState } from 'react'
import { getPlayers, getPlayer, type Player } from '../api/players'
import PlayerModal from '../components/PlayerModal'

type SearchState = 'idle' | 'loading' | 'done' | 'error'

export default function PlayerDetail() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Player[]>([])
  const [state, setState] = useState<SearchState>('idle')
  const [error, setError] = useState('')
  const [modalPlayer, setModalPlayer] = useState<Player | null>(null)

  const search = async () => {
    const q = query.trim()
    if (!q) return
    setState('loading')
    setError('')
    try {
      const r = await getPlayers({ name: q, page_size: 20 })
      setResults(r.data)
      setState('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
      setState('error')
    }
  }

  const selectPlayer = async (p: Player) => {
    if (!p.sofascore_player_id) { setModalPlayer(p); return }
    try {
      setModalPlayer(await getPlayer(p.sofascore_player_id))
    } catch {
      setModalPlayer(p)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Player Detail</h1>
      <div className="flex gap-2 mb-6">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Search player name…"
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-64"
        />
        <button
          onClick={search}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm"
        >
          Search
        </button>
      </div>

      {state === 'loading' && <div className="text-gray-400 text-sm">Searching…</div>}
      {state === 'error' && <div className="text-red-400 text-sm">{error}</div>}

      {state === 'done' && results.length === 0 && (
        <div className="text-gray-400 text-sm">No players found for "{query}".</div>
      )}

      {state === 'done' && results.length > 0 && (
        <div className="bg-gray-900 rounded-lg overflow-hidden">
          {results.map((p) => (
            <button
              key={p.sofascore_player_id ?? p.name}
              onClick={() => selectPlayer(p)}
              className="w-full flex items-center gap-4 px-4 py-3 hover:bg-gray-800 border-b border-gray-800 last:border-0 text-left"
            >
              {p.photo_url && (
                <img src={p.photo_url} alt={p.name} className="w-8 h-8 rounded-full object-cover bg-gray-700 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{p.name}</div>
                <div className="text-xs text-gray-400">{p.position_exact} · {p.team} · {p.nationality}</div>
              </div>
              <div className="text-indigo-300 font-mono text-sm flex-shrink-0">
                {p.aggregated_scores.s_final.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
      )}

      <PlayerModal player={modalPlayer} playerId={null} onClose={() => setModalPlayer(null)} />
    </div>
  )
}

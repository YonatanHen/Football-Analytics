import { useState } from 'react'
import { getPlayer, type Player } from '../api/players'
import PlayerCard from '../components/PlayerCard'

export default function PlayerDetail() {
  const [playerId, setPlayerId] = useState('')
  const [player, setPlayer] = useState<Player | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const search = async () => {
    if (!playerId.trim()) return
    setLoading(true)
    setError('')
    try {
      setPlayer(await getPlayer(playerId.trim()))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Not found')
      setPlayer(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Player Detail</h1>
      <div className="flex gap-2 mb-6">
        <input
          value={playerId}
          onChange={(e) => setPlayerId(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Player ID…"
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-60"
        />
        <button
          onClick={search}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm"
        >
          Search
        </button>
      </div>
      {loading && <div className="text-gray-400">Loading…</div>}
      {error && <div className="text-red-400">{error}</div>}
      {player && <PlayerCard player={player} />}
    </div>
  )
}

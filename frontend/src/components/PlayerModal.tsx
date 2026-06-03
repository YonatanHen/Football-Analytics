import { useEffect, useState } from 'react'
import { getPlayer, type Player } from '../api/players'
import PlayerCard from './PlayerCard'

interface PlayerModalProps {
  playerId: string | null
  player?: Player | null
  onClose: () => void
}

export default function PlayerModal({ playerId, player: prefetched, onClose }: PlayerModalProps) {
  const [player, setPlayer] = useState<Player | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (prefetched !== undefined) {
      setPlayer(prefetched)
      return
    }
    if (!playerId) return
    setLoading(true)
    setPlayer(null)
    getPlayer(playerId)
      .then(setPlayer)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [playerId, prefetched])

  const open = playerId != null || prefetched != null
  if (!open) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-4 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-200 text-sm"
        >
          ✕
        </button>
        {loading && <div className="text-gray-400 text-sm py-8 text-center">Loading…</div>}
        {player && <PlayerCard player={player} />}
      </div>
    </div>
  )
}

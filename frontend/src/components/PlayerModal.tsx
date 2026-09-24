import { useEffect, useState } from 'react'
import { getPlayer, refreshBio, type Player } from '../api/players'
import { useApp } from '../context/AppContext'
import PlayerCard from './PlayerCard'

interface PlayerModalProps {
  playerId: string | null
  player?: Player | null
  onClose: () => void
}

export default function PlayerModal({ playerId, player: prefetched, onClose }: PlayerModalProps) {
  const { season, go } = useApp()
  const [player, setPlayer] = useState<Player | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [bioLoading, setBioLoading] = useState(false)

  useEffect(() => {
    if (prefetched !== undefined) {
      setPlayer(prefetched)
      return
    }
    if (!playerId) return
    setLoading(true)
    setFailed(false)
    setPlayer(null)
    getPlayer(playerId, season || undefined)
      .then(setPlayer)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [playerId, prefetched, season])

  // Trigger lazy bio fetch when the modal opens with missing bio fields
  useEffect(() => {
    const id = player?.sofascore_player_id
    if (!id || (player?.nationality && player?.position_exact)) return
    setBioLoading(true)
    refreshBio(id)
      .then((bio) => setPlayer((prev) => prev ? { ...prev, ...bio } : prev))
      .catch(() => {})
      .finally(() => setBioLoading(false))
  }, [player?.sofascore_player_id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const open = playerId != null || prefetched != null
  if (!open) return null

  const compare = player?.sofascore_player_id
    ? () => { onClose(); go('compare', { comparePlayerId: player.sofascore_player_id }) }
    : undefined

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-6" onClick={onClose}>
      <div
        className="max-h-[92vh] w-full max-w-[880px] overflow-y-auto rounded-xl border border-line-strong bg-header p-7 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {loading && <div className="py-16 text-center text-sm text-muted">Loading…</div>}
        {failed && <div className="py-16 text-center text-sm text-danger">Could not load this player.</div>}
        {player && <PlayerCard player={player} bioLoading={bioLoading} onClose={onClose} onCompare={compare} />}
      </div>
    </div>
  )
}

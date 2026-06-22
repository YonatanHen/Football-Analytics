import { useState, useEffect } from 'react'
import { getPlayers, type Player, type PlayerList } from '../api/players'
import PlayerTable from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'

export default function Sleepers() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [flag, setFlag] = useState<'HIGH_VALUE' | 'OVERPERFORMING'>('HIGH_VALUE')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalId, setModalId] = useState<string | null>(null)
  const [modalPlayer, setModalPlayer] = useState<Player | null>(null)

  const openPlayer = (p: Player) =>
    p.sofascore_player_id ? setModalId(p.sofascore_player_id) : setModalPlayer(p)
  const closeModal = () => { setModalId(null); setModalPlayer(null) }

  useEffect(() => {
    setLoading(true)
    getPlayers({ underpredicted_flag: flag, page, page_size: 50 })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [flag, page])

  return (
    <div>
      <h1 className="text-xl font-bold mb-2">Underpredicted Picks</h1>
      <p className="text-sm text-gray-400 mb-4">
        <strong className="text-amber-300">Underpredicted</strong>: xG+xA &gt; 1.2×(G+A) with &gt;450 min — underperforming their underlying numbers.{' '}
        <strong className="text-green-300">Overperforming</strong>: G+A &gt; 1.25×(xG+xA) with &gt;450 min — scoring above expectation, likely to regress.
      </p>
      <div className="flex gap-2 mb-4">
        {(['HIGH_VALUE', 'OVERPERFORMING'] as const).map((f) => (
          <button
            key={f}
            onClick={() => { setFlag(f); setPage(1) }}
            className={`px-4 py-2 rounded text-sm ${
              flag === f ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {f === 'HIGH_VALUE' ? 'Underpredicted' : 'Overperforming'}
          </button>
        ))}
      </div>
      {loading && <div className="text-gray-400 py-8 text-center">Loading…</div>}
      {data && !loading && (
        <>
          <div className="text-xs text-gray-500 mb-2">{data.total} players</div>
          <PlayerTable
            players={data.data}
            total={data.total}
            page={page}
            pageSize={50}
            onPageChange={setPage}
            onPlayerClick={openPlayer}
          />
        </>
      )}
      <PlayerModal playerId={modalId} player={modalPlayer ?? undefined} onClose={closeModal} />
    </div>
  )
}

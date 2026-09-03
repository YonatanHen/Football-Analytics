import { useState, useEffect } from 'react'
import { getScatterData, type ScatterPoint } from '../api/players'
import ScatterPlot from '../components/ScatterPlot'
import PlayerModal from '../components/PlayerModal'

export default function ScatterPage() {
  const [data, setData] = useState<ScatterPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [modalId, setModalId] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getScatterData()
      .then((r) => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handlePointClick = (point: ScatterPoint) => {
    if (point.sofascore_player_id) setModalId(point.sofascore_player_id)
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-2">G+A vs xG+xA</h1>
      <p className="text-gray-400 text-sm mb-4">
        Points <strong className="text-white">above</strong> the diagonal are overperforming their xG+xA. Points{' '}
        <strong className="text-white">below</strong> have higher expected output than actual —
        underpredicted players.
      </p>
      {loading && <div className="text-gray-400 py-8 text-center">Loading…</div>}
      {!loading && (
        <div className="w-screen relative left-1/2 -translate-x-1/2 px-4 md:px-8">
          <ScatterPlot data={data} onPointClick={handlePointClick} />
        </div>
      )}
      <PlayerModal playerId={modalId} onClose={() => setModalId(null)} />
    </div>
  )
}

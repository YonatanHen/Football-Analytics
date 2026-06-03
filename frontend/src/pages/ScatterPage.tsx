import { useState, useEffect } from 'react'
import { getScatterData, type ScatterPoint } from '../api/players'
import ScatterPlot from '../components/ScatterPlot'

export default function ScatterPage() {
  const [data, setData] = useState<ScatterPoint[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getScatterData()
      .then((r) => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1 className="text-xl font-bold mb-2">xG+xA vs G+A</h1>
      <p className="text-gray-400 text-sm mb-4">
        Points <strong className="text-white">above</strong> the diagonal have higher expected output than actual —
        underpredicted players. Points <strong className="text-white">below</strong> are overperforming their xG+xA.
      </p>
      {loading && <div className="text-gray-400 py-8 text-center">Loading…</div>}
      {!loading && <ScatterPlot data={data} />}
    </div>
  )
}

import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import type { ScatterPoint } from '../api/players'

interface ScatterPlotProps { data: ScatterPoint[] }

const POSITION_COLORS: Record<string, string> = {
  GK: '#6366f1', DF: '#22c55e', MF: '#f59e0b', FW: '#ef4444',
}

export default function ScatterPlot({ data }: ScatterPlotProps) {
  const byPosition: Record<string, ScatterPoint[]> = {}
  for (const p of data) {
    const pos = p.position || 'MF'
    byPosition[pos] = byPosition[pos] ?? []
    byPosition[pos].push(p)
  }

  const maxVal = data.reduce((m, p) => Math.max(m, p.g_a, p.xg_xa), 5)

  return (
    <ResponsiveContainer width="100%" height={500}>
      <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="g_a" name="G+A" type="number"
          label={{ value: 'Goals + Assists', position: 'insideBottom', offset: -20, fill: '#9ca3af' }}
          stroke="#6b7280"
        />
        <YAxis
          dataKey="xg_xa" name="xG+xA" type="number"
          label={{ value: 'xG + xA', angle: -90, position: 'insideLeft', offset: 10, fill: '#9ca3af' }}
          stroke="#6b7280"
        />
        {/* diagonal y=x: above = underperformer (potential sleeper) */}
        <ReferenceLine
          segment={[{ x: 0, y: 0 }, { x: maxVal, y: maxVal }]}
          stroke="#4b5563" strokeDasharray="4 4"
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          content={({ payload }) => {
            if (!payload?.length) return null
            const p = payload[0].payload as ScatterPoint
            return (
              <div className="bg-gray-800 border border-gray-700 p-2 rounded text-sm">
                <div className="font-medium">{p.name}</div>
                <div className="text-gray-400">{p.position}</div>
                <div className="text-gray-400">G+A: {p.g_a} · xG+xA: {p.xg_xa.toFixed(2)}</div>
              </div>
            )
          }}
        />
        <Legend />
        {Object.entries(byPosition).map(([pos, points]) => (
          <Scatter
            key={pos}
            name={pos}
            data={points}
            fill={POSITION_COLORS[pos] ?? '#9ca3af'}
            opacity={0.8}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

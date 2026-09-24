import { useEffect, useMemo, useState } from 'react'
import { ArrowUpRight, MousePointerClick } from 'lucide-react'
import { getScatterData, type ScatterPoint } from '../api/players'
import { useApp } from '../context/AppContext'
import PlayerModal from '../components/PlayerModal'
import ScatterPlot, { type PlotPoint } from '../components/ScatterPlot'
import Avatar from '../components/ui/Avatar'
import { FlagBadge } from '../components/ui/Badges'
import { Select } from '../components/ui/Fields'
import PageHeader, { Dot } from '../components/ui/PageHeader'
import Segmented from '../components/ui/Segmented'
import StatRow from '../components/ui/StatRow'

const X_AXES = [
  { value: 'xg_xa', label: 'xG + xA' },
  { value: 'xg', label: 'xG' },
  { value: 'xa', label: 'xA' },
] as const
const Y_AXES = [
  { value: 'g_a', label: 'Goals + Assists' },
  { value: 'goals', label: 'Goals' },
  { value: 'assists', label: 'Assists' },
] as const
const Y_SHORT: Record<string, string> = { g_a: 'G + A', goals: 'Goals', assists: 'Assists' }

type XKey = (typeof X_AXES)[number]['value']
type YKey = (typeof Y_AXES)[number]['value']
type Pos = 'ALL' | 'GK' | 'DF' | 'MF' | 'FW'

const COLORS = { due: '#e9b44c', over: '#34d98c', inline: '#34423b', selected: '#f4f7f5' }
const LABELS_PER_FLAG = 3

export default function ScatterPage() {
  const { season } = useApp()
  const [data, setData] = useState<ScatterPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [xKey, setXKey] = useState<XKey>('xg_xa')
  const [yKey, setYKey] = useState<YKey>('g_a')
  const [pos, setPos] = useState<Pos>('ALL')
  const [minMinutes, setMinMinutes] = useState('900')
  const [highlight, setHighlight] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [modalId, setModalId] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getScatterData(season)
      .then((r) => { setData(r.data); setError(false) })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [season])

  const visible = useMemo(() => {
    const min = Number(minMinutes) || 0
    return data.filter((p) => p.sofascore_player_id && p.minutes >= min && (pos === 'ALL' || p.position === pos))
  }, [data, minMinutes, pos])

  const points = useMemo<PlotPoint[]>(() => {
    // Label the widest gaps of each flag, plus the selected player.
    const gap = (p: ScatterPoint) => Math.abs(p.xg_xa - p.g_a)
    const top = (f: string) =>
      visible.filter((p) => p.flag === f).sort((a, b) => gap(b) - gap(a)).slice(0, LABELS_PER_FLAG)
    const labelled = new Set(highlight ? [...top('HIGH_VALUE'), ...top('OVERPERFORMING')].map((p) => p.sofascore_player_id) : [])
    const lastName = (n: string) => n.split(' ').slice(-1)[0]

    const out = visible.map<PlotPoint>((p) => {
      const selected = p.sofascore_player_id === selectedId
      const flagged = highlight && p.flag
      return {
        id: p.sofascore_player_id!,
        name: p.name,
        x: p[xKey],
        y: p[yKey],
        color: selected ? COLORS.selected : !flagged ? COLORS.inline : p.flag === 'HIGH_VALUE' ? COLORS.due : COLORS.over,
        radius: selected || flagged ? 5 : 3,
        label: selected || labelled.has(p.sofascore_player_id) ? lastName(p.name) : undefined,
        selected,
      }
    })
    // Draw grey points first so flagged and selected ones stay on top.
    const rank = (p: PlotPoint) => (p.selected ? 2 : p.color === COLORS.inline ? 0 : 1)
    return out.sort((a, b) => rank(a) - rank(b))
  }, [visible, xKey, yKey, highlight, selectedId])

  const selected = data.find((p) => p.sofascore_player_id === selectedId) ?? null
  const xLabel = X_AXES.find((a) => a.value === xKey)!.label
  const yShort = Y_SHORT[yKey]

  return (
    <div>
      <PageHeader
        title="Scatter Plot"
        subtitle={<>Expected contribution against actual contribution<Dot />the diagonal is xGI = GI</>}
        right={<span className="font-mono text-[11px] text-muted">{visible.length.toLocaleString('en-US')} players plotted</span>}
      />

      <div className="mb-6 flex flex-wrap items-center gap-2.5">
        <Select value={xKey} onChange={(v) => setXKey(v as XKey)} prefix="X" className="w-[205px]">
          {X_AXES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </Select>
        <Select value={yKey} onChange={(v) => setYKey(v as YKey)} prefix="Y" className="w-[205px]">
          {Y_AXES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </Select>
        <span className="mx-1 h-6 w-px bg-line-strong" />
        <Segmented
          mono
          options={(['ALL', 'GK', 'DF', 'MF', 'FW'] as Pos[]).map((p) => ({ value: p, label: p === 'ALL' ? 'All' : p }))}
          value={pos}
          onChange={setPos}
        />
        <label className="field flex items-center gap-2 px-3 font-mono text-xs text-muted">
          minutes ≥
          <input
            type="number"
            min={0}
            value={minMinutes}
            onChange={(e) => setMinMinutes(e.target.value)}
            className="w-14 bg-transparent text-sm text-ink outline-none"
          />
        </label>
        <button
          onClick={() => setHighlight((h) => !h)}
          className={`ml-auto inline-flex h-10 items-center gap-2.5 rounded-md border px-4 text-sm ${
            highlight ? 'border-accent-deep/60 bg-accent-soft text-accent' : 'border-line-strong bg-surface text-muted'
          }`}
        >
          <span className={`relative h-4 w-7 rounded-full transition-colors ${highlight ? 'bg-accent' : 'bg-line-strong'}`}>
            <span className={`absolute top-0.5 h-3 w-3 rounded-full bg-bg transition-all ${highlight ? 'left-3.5' : 'left-0.5'}`} />
          </span>
          Highlight outliers
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_320px]">
        <div className="h-[calc(100vh-17rem)] min-h-[520px] rounded-lg bg-surface p-2">
          {loading && <div className="flex h-full items-center justify-center text-sm text-muted">Loading…</div>}
          {error && <div className="flex h-full items-center justify-center text-sm text-danger">Could not load the scatter data.</div>}
          {!loading && !error && (
            <ScatterPlot points={points} xLabel={xLabel} yLabel={yShort} onPointClick={setSelectedId} />
          )}
        </div>

        <aside className="flex flex-col gap-5">
          <div className="rounded-lg bg-surface p-5">
            <div className="label-caps mb-3">Legend</div>
            <LegendItem color={COLORS.due} title="Due to score" text="below the line — xGI outruns returns" />
            <LegendItem color={COLORS.over} title="Overperforming" text="above the line — returns outrun xGI" />
            <LegendItem color="#56635c" title="In line" text="within the ±20% band of expectation" />
          </div>

          {selected && (
            <div className="rounded-lg border border-line-strong bg-surface p-5">
              <div className="label-caps mb-4">Selected point</div>
              <div className="mb-3 flex items-center gap-3">
                <Avatar name={selected.name} size="md" />
                <div>
                  <div className="text-lg font-semibold tracking-tight">{selected.name}</div>
                  <div className="text-sm text-muted">{selected.position} · {selected.team}</div>
                </div>
              </div>
              <StatRow label="xG + xA" value={selected.xg_xa.toFixed(2)} />
              <StatRow label="G + A" value={selected.g_a} />
              <StatRow
                label="xRatio"
                value={<span className="text-warn">{selected.xratio == null ? '—' : `${selected.xratio.toFixed(2)}×`}</span>}
              />
              <StatRow label="Minutes" value={selected.minutes.toLocaleString('en-US')} />
              <StatRow label="Fantasy Score" value={selected.s_final.toFixed(2)} />
              <div className="mt-4 flex items-center justify-between">
                {selected.flag ? <FlagBadge flag={selected.flag} /> : <span />}
                <button onClick={() => setModalId(selected.sofascore_player_id)} className="btn-ghost h-8 text-muted hover:text-ink">
                  Open profile <ArrowUpRight size={14} />
                </button>
              </div>
            </div>
          )}

          <div className="mt-auto flex items-center gap-2 text-sm text-muted">
            <MousePointerClick size={15} /> Click any point to inspect the player
          </div>
        </aside>
      </div>

      <PlayerModal playerId={modalId} onClose={() => setModalId(null)} />
    </div>
  )
}

function LegendItem({ color, title, text }: { color: string; title: string; text: string }) {
  return (
    <div className="mb-3 flex gap-3 last:mb-0">
      <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: color }} />
      <div>
        <div className="text-sm text-ink">{title}</div>
        <div className="text-xs text-muted">{text}</div>
      </div>
    </div>
  )
}

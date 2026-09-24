import { useState, useEffect } from 'react'
import { getPlayers, type Flag, type Player, type PlayerList } from '../api/players'
import { useApp } from '../context/AppContext'
import PlayerTable, { type Column } from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'
import { COL } from '../components/playerColumns'
import { TableSkeleton } from '../components/states/SystemStates'
import { FlagBadge } from '../components/ui/Badges'
import PageHeader, { Dot } from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import ScoreBar from '../components/ui/ScoreBar'
import Segmented from '../components/ui/Segmented'
import { signed, xgiGap } from '../lib/format'

const PAGE_SIZE = 50

// Thresholds mirror backend/app/domain/sleeper_detector.py.
const RULES: { flag: Flag; formula: string; text: string; border: string }[] = [
  {
    flag: 'HIGH_VALUE',
    formula: 'xG + xA  >  1.20 × (G + A)',
    text: 'Underlying numbers outrun the returns. These players have historically regressed upward — the buy-low signal.',
    border: 'border-l-warn',
  },
  {
    flag: 'OVERPERFORMING',
    formula: 'G + A  >  1.25 × (xG + xA)',
    text: 'Returns outrun the underlying numbers. Finishing is running hot and is likely to cool — the sell-high signal.',
    border: 'border-l-accent',
  },
]

// Due: 1.0x -> empty bar, 1.8x -> full. Over: 1.0x -> empty, 0.2x -> full.
const ratioFraction = (r: number | null, flag: Flag) =>
  r == null ? 1 : flag === 'HIGH_VALUE' ? (r - 1) / 0.8 : (1 - r) / 0.8

export default function Sleepers() {
  const { season } = useApp()
  const [data, setData] = useState<PlayerList | null>(null)
  const [flag, setFlag] = useState<Flag>('HIGH_VALUE')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalId, setModalId] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setLoading(true)
    getPlayers({
      season, underpredicted_flag: flag, page, page_size: PAGE_SIZE,
      sort_by: 'xratio', order: flag === 'HIGH_VALUE' ? 'desc' : 'asc',
    })
      .then((d) => live && setData(d))
      .catch(console.error)
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [flag, page, season])

  const xg = 'font-mono text-accent'
  const columns: Column[] = [
    COL.rank, { ...COL.player, className: 'min-w-[220px]' }, COL.pos, COL.team,
    {
      key: 'xratio', label: 'xRatio', sortKey: 'xratio',
      render: (p) => {
        const r = p.aggregated_scores.underpredicted_ratio
        return <ScoreBar label={r == null ? '—' : `${r.toFixed(2)}×`} fraction={ratioFraction(r, flag)} tone={flag === 'HIGH_VALUE' ? 'warn' : 'accent'} />
      },
    },
    COL.apps, COL.goals, COL.assists,
    { ...COL.xg, className: xg }, { ...COL.xa, className: xg },
    COL.minutes,
    { key: 'score', label: 'Score', className: 'font-mono text-ink/90', render: (p) => p.aggregated_scores.s_final.toFixed(2) },
    {
      key: 'signal', label: 'Signal',
      render: (p: Player) => (
        <div className="flex items-center gap-2">
          <FlagBadge flag={flag} />
          <span className="font-mono text-[11px] text-muted">{signed(xgiGap(p))} xGI</span>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="xGI Outliers"
        subtitle={<>Players whose expected output and actual output have diverged<Dot />gated on minutes &gt; 450</>}
      />

      <div className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {RULES.map((r) => (
          <div key={r.flag} className={`rounded-lg border-l-[3px] ${r.border} bg-surface px-5 py-4`}>
            <div className="flex items-center gap-3">
              <FlagBadge flag={r.flag} />
              <span className="whitespace-pre font-mono text-xs text-ink/90">{r.formula}</span>
            </div>
            <p className="mt-3 text-[13px] text-muted">{r.text}</p>
          </div>
        ))}
      </div>

      <div className="mb-4 flex items-center justify-between">
        <Segmented
          options={[{ value: 'HIGH_VALUE', label: 'Due to score' }, { value: 'OVERPERFORMING', label: 'Overperforming' }]}
          value={flag}
          onChange={(f) => { setFlag(f); setPage(1) }}
        />
        {data && (
          <span className="font-mono text-[11px] text-muted">
            {data.total.toLocaleString('en-US')} players flagged<Dot />sorted by xRatio {flag === 'HIGH_VALUE' ? '▼' : '▲'}
          </span>
        )}
      </div>

      {!data && <TableSkeleton />}
      {data && data.total === 0 && (
        <p className="py-16 text-center text-sm text-muted">No players carry this flag in {season}.</p>
      )}
      {data && data.total > 0 && (
        <>
          <PlayerTable
            players={data.data}
            columns={columns}
            rankOffset={(page - 1) * PAGE_SIZE}
            onRowClick={(p) => p.sofascore_player_id && setModalId(p.sofascore_player_id)}
            sortBy="xratio"
            order={flag === 'HIGH_VALUE' ? 'desc' : 'asc'}
            dimmed={loading}
          />
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} shown={data.data.length} onPage={setPage} />
        </>
      )}
      <PlayerModal playerId={modalId} onClose={() => setModalId(null)} />
    </div>
  )
}

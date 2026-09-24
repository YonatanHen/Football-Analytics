import { useEffect, useRef, useState } from 'react'
import { ArrowLeftRight, Search } from 'lucide-react'
import { getPlayer, getPlayers, type Player } from '../api/players'
import { useApp } from '../context/AppContext'
import Avatar from '../components/ui/Avatar'
import { PosBadge } from '../components/ui/Badges'
import PageHeader, { Dot } from '../components/ui/PageHeader'

interface Metric { label: string; get: (p: Player) => number; decimals: number; lowerIsBetter?: boolean }

const METRICS: Metric[] = [
  { label: 'Fantasy Score', get: (p) => p.aggregated_scores.s_final, decimals: 2 },
  { label: 'Offensive', get: (p) => p.aggregated_scores.offensive, decimals: 1 },
  { label: 'Defensive', get: (p) => p.aggregated_scores.defensive, decimals: 1 },
  { label: 'Tactical', get: (p) => p.aggregated_scores.tactical, decimals: 1 },
  { label: 'Goals', get: (p) => p.aggregated_stats.goals, decimals: 0 },
  { label: 'Assists', get: (p) => p.aggregated_stats.assists, decimals: 0 },
  { label: 'xG', get: (p) => p.aggregated_stats.xg, decimals: 1 },
  { label: 'xA', get: (p) => p.aggregated_stats.xa, decimals: 1 },
  { label: 'Minutes', get: (p) => p.aggregated_stats.minutes, decimals: 0 },
  { label: 'Appearances', get: (p) => p.aggregated_stats.appearances, decimals: 0 },
  { label: 'Key passes', get: (p) => p.aggregated_stats.key_passes, decimals: 0 },
  { label: 'Big chances created', get: (p) => p.aggregated_stats.big_chances_created, decimals: 0 },
  { label: 'Penalties won', get: (p) => p.aggregated_stats.pk_won, decimals: 0 },
  { label: 'Rating', get: (p) => p.aggregated_stats.rating, decimals: 1 },
  { label: 'Yellow cards', get: (p) => p.aggregated_stats.yellow_cards, decimals: 0, lowerIsBetter: true },
  { label: 'Red cards', get: (p) => p.aggregated_stats.red_cards, decimals: 0, lowerIsBetter: true },
]

const LOSER_A = '#1c4a33'
const LOSER_B = '#2b3c4d'

export default function Compare({ seedId, onSeedUsed }: { seedId: string | null; onSeedUsed: () => void }) {
  const { season } = useApp()
  const [a, setA] = useState<Player | null>(null)
  const [b, setB] = useState<Player | null>(null)

  useEffect(() => {
    if (!seedId) return
    getPlayer(seedId, season).then(setA).catch(console.error).finally(onSeedUsed)
  }, [seedId, season, onSeedUsed])

  return (
    <div>
      <PageHeader
        title="Compare"
        subtitle={<>Head-to-head across every scoring and stat dimension<Dot />Δ is A − B</>}
      />

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-6">
        <PlayerSlot tag="Player A" player={a} onPick={setA} />
        <span className="font-mono text-xs tracking-[0.2em] text-dim">VS</span>
        <PlayerSlot tag="Player B" player={b} onPick={setB} />
      </div>

      {a && b ? (
        <div className="mx-auto mt-8 max-w-[1180px]">
          <div className="grid grid-cols-[80px_1fr_220px_1fr_80px_120px] items-center border-b border-line-strong pb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
            <span className="text-right">A</span><span /><span className="text-center">Metric</span><span />
            <span>B</span><span className="text-center">Δ</span>
          </div>
          {METRICS.map((m) => <CompareRow key={m.label} m={m} a={a} b={b} />)}
        </div>
      ) : (
        <p className="mt-16 text-center text-sm text-muted">Pick two players to see them head-to-head.</p>
      )}
    </div>
  )
}

function CompareRow({ m, a, b }: { m: Metric; a: Player; b: Player }) {
  const va = m.get(a)
  const vb = m.get(b)
  const max = Math.max(Math.abs(va), Math.abs(vb)) || 1
  const aWins = m.lowerIsBetter ? va < vb : va > vb
  const bWins = m.lowerIsBetter ? vb < va : vb > va
  const diff = va - vb
  const fmt = (v: number) => v.toFixed(m.decimals)
  const good = m.lowerIsBetter ? diff < 0 : diff > 0

  return (
    <div className="grid h-11 grid-cols-[80px_1fr_220px_1fr_80px_120px] items-center border-b border-line font-mono text-[13px]">
      <span className={`text-right ${aWins ? 'text-accent' : 'text-ink/80'}`}>{fmt(va)}</span>
      <div className="flex justify-end pl-5">
        <div className="h-1 rounded" style={{ width: `${(Math.abs(va) / max) * 100}%`, minWidth: 2, background: aWins ? '#34d98c' : LOSER_A }} />
      </div>
      <span className="text-center font-sans text-sm text-ink/90">{m.label}</span>
      <div className="flex pr-5">
        <div className="h-1 rounded" style={{ width: `${(Math.abs(vb) / max) * 100}%`, minWidth: 2, background: bWins ? '#6fa8ea' : LOSER_B }} />
      </div>
      <span className={bWins ? 'text-info' : 'text-ink/80'}>{fmt(vb)}</span>
      <span className={`text-center ${diff === 0 ? 'text-dim' : good ? 'text-accent' : 'text-danger'}`}>
        {diff === 0 ? '—' : `${diff > 0 ? '+' : ''}${fmt(diff)}`}
      </span>
    </div>
  )
}

function PlayerSlot({ tag, player, onPick }: { tag: string; player: Player | null; onPick: (p: Player) => void }) {
  const [searching, setSearching] = useState(false)
  const show = searching || !player
  return (
    <div className="relative flex h-[92px] items-center gap-4 rounded-xl border border-line-strong bg-surface px-6">
      {player ? <Avatar name={player.name} size="md" /> : <Avatar name="?" size="md" />}
      <div className="min-w-0 flex-1">
        <div className="label-caps">{tag}</div>
        {show ? (
          <PlayerSearch onPick={(p) => { onPick(p); setSearching(false) }} onCancel={player ? () => setSearching(false) : undefined} />
        ) : (
          <>
            <div className="mt-1 truncate text-xl font-semibold tracking-tight">{player.name}</div>
            <div className="mt-1 flex items-center gap-2 text-sm text-ink/80">
              <PosBadge pos={player.position_exact || player.position} />
              {player.team}<span className="text-dim">·</span>{player.nationality}
            </div>
          </>
        )}
      </div>
      {player && !show && (
        <>
          <div className="text-right">
            <div className="label-caps">Fantasy Score</div>
            <div className="mt-1 font-mono text-[28px] leading-none text-accent">{player.aggregated_scores.s_final.toFixed(2)}</div>
          </div>
          <button
            onClick={() => setSearching(true)}
            aria-label={`Change ${tag}`}
            className="rounded-md border border-line-strong bg-surface-2 p-2 text-muted hover:text-ink"
          >
            <ArrowLeftRight size={15} />
          </button>
        </>
      )}
    </div>
  )
}

function PlayerSearch({ onPick, onCancel }: { onPick: (p: Player) => void; onCancel?: () => void }) {
  const { season } = useApp()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Player[]>([])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!query.trim()) { setResults([]); return }
    const t = setTimeout(() => {
      getPlayers({ name: query.trim(), page_size: 8, season })
        .then((d) => setResults(d.data))
        .catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(t)
  }, [query, season])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) { setResults([]); onCancel?.() }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [onCancel])

  return (
    <div ref={ref} className="relative mt-1.5">
      <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-dim" />
      <input
        autoFocus
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Escape' && onCancel?.()}
        placeholder="Search a player..."
        className="field h-9 w-full max-w-sm pl-9 pr-3"
      />
      {results.length > 0 && (
        <div className="absolute top-full z-20 mt-1 max-h-72 w-full max-w-sm overflow-y-auto rounded-lg border border-line-strong bg-surface shadow-2xl">
          {results.map((p) => (
            <button
              key={p.sofascore_player_id}
              onClick={() => onPick(p)}
              className="flex w-full items-center gap-3 border-b border-line px-3 py-2 text-left last:border-0 hover:bg-surface-2"
            >
              <Avatar name={p.name} />
              <div>
                <div className="text-sm">{p.name}</div>
                <div className="text-xs text-muted">{p.position_exact || p.position} · {p.team}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

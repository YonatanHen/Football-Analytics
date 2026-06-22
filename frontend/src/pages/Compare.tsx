import { useState, useEffect, useRef } from 'react'
import { getPlayers, type Player, type Stats } from '../api/players'

const STAT_LABELS: { key: keyof Stats; label: string; higherIsBetter: boolean }[] = [
  { key: 'goals', label: 'Goals', higherIsBetter: true },
  { key: 'assists', label: 'Assists', higherIsBetter: true },
  { key: 'xg', label: 'xG', higherIsBetter: true },
  { key: 'xa', label: 'xA', higherIsBetter: true },
  { key: 'minutes', label: 'Minutes', higherIsBetter: true },
  { key: 'key_passes', label: 'Key Passes', higherIsBetter: true },
  { key: 'big_chances_created', label: 'Big Chances', higherIsBetter: true },
  { key: 'clean_sheets', label: 'Clean Sheets', higherIsBetter: true },
  { key: 'pk_won', label: 'PK Won', higherIsBetter: true },
  { key: 'rating', label: 'Rating', higherIsBetter: true },
  { key: 'yellow_cards', label: 'Yellow Cards', higherIsBetter: false },
  { key: 'red_cards', label: 'Red Cards', higherIsBetter: false },
]

function fmt(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(2)
}

function DiffCell({ a, b, higherIsBetter }: { a: number; b: number; higherIsBetter: boolean }) {
  const diff = a - b
  if (diff === 0) return <td className="py-1.5 text-center text-gray-500 text-sm">—</td>
  const better = higherIsBetter ? diff > 0 : diff < 0
  const color = better ? 'text-green-400' : 'text-red-400'
  const sign = diff > 0 ? '+' : ''
  return <td className={`py-1.5 text-center text-sm font-mono ${color}`}>{sign}{fmt(diff)}</td>
}

function SearchInput({ label, onFound }: { label: string; onFound: (p: Player) => void }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Player[]>([])
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!query.trim()) { setResults([]); return }
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await getPlayers({ name: query.trim(), page_size: 8 })
        setResults(data.data)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setResults([])
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const pick = (p: Player) => {
    onFound(p)
    setQuery('')
    setResults([])
  }

  return (
    <div ref={containerRef} className="flex flex-col gap-1 relative">
      <span className="text-xs text-gray-400">{label}</span>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by name…"
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-56"
      />
      {loading && <div className="text-xs text-gray-500 mt-0.5">Searching…</div>}
      {results.length > 0 && (
        <div className="absolute top-full mt-1 w-56 bg-gray-900 border border-gray-700 rounded shadow-lg z-10 max-h-60 overflow-y-auto">
          {results.map(p => (
            <button
              key={p.sofascore_player_id}
              onClick={() => pick(p)}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-800 border-b border-gray-800 last:border-0"
            >
              <div className="font-medium">{p.name}</div>
              <div className="text-xs text-gray-400">{p.position_exact} · {p.team}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Compare() {
  const [playerA, setPlayerA] = useState<Player | null>(null)
  const [playerB, setPlayerB] = useState<Player | null>(null)

  const scoreRow = (label: string, a: number, b: number, higherIsBetter = true) => (
    <tr key={label} className="border-b border-gray-800">
      <td className={`py-1.5 text-right pr-3 text-sm font-mono ${
        (higherIsBetter ? a >= b : a <= b) && a !== b ? 'text-green-400' : 'text-gray-200'
      }`}>{fmt(a)}</td>
      <td className="py-1.5 text-center text-xs text-gray-400 px-2">{label}</td>
      <td className={`py-1.5 text-left pl-3 text-sm font-mono ${
        (higherIsBetter ? b >= a : b <= a) && a !== b ? 'text-green-400' : 'text-gray-200'
      }`}>{fmt(b)}</td>
      <DiffCell a={a} b={b} higherIsBetter={higherIsBetter} />
    </tr>
  )

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Compare Players</h1>

      <div className="flex gap-8 mb-8">
        <SearchInput label="Player A" onFound={setPlayerA} />
        <SearchInput label="Player B" onFound={setPlayerB} />
      </div>

      {playerA && playerB && (
        <div>
          {/* header */}
          <div className="grid grid-cols-[1fr_auto_1fr_auto] gap-x-2 mb-4 text-center">
            <div>
              <div className="font-semibold">{playerA.name}</div>
              <div className="text-xs text-gray-400">{playerA.position_exact} · {playerA.team}</div>
            </div>
            <div className="text-gray-600 self-center">vs</div>
            <div>
              <div className="font-semibold">{playerB.name}</div>
              <div className="text-xs text-gray-400">{playerB.position_exact} · {playerB.team}</div>
            </div>
            <div className="text-xs text-gray-500 self-end pb-1">Δ (A−B)</div>
          </div>

          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="py-1.5 text-right pr-3 text-xs text-gray-400 font-normal">A</th>
                <th className="py-1.5 text-center text-xs text-gray-400 font-normal">Stat</th>
                <th className="py-1.5 text-left pl-3 text-xs text-gray-400 font-normal">B</th>
                <th className="py-1.5 text-center text-xs text-gray-400 font-normal">Δ</th>
              </tr>
            </thead>
            <tbody>
              {/* scores */}
              {scoreRow('S_final', playerA.aggregated_scores.s_final, playerB.aggregated_scores.s_final)}
              {scoreRow('Offensive', playerA.aggregated_scores.offensive, playerB.aggregated_scores.offensive)}
              {scoreRow('Defensive', playerA.aggregated_scores.defensive, playerB.aggregated_scores.defensive)}
              {scoreRow('Tactical', playerA.aggregated_scores.tactical, playerB.aggregated_scores.tactical)}
              {/* stats */}
              {STAT_LABELS.map(({ key, label, higherIsBetter }) =>
                scoreRow(
                  label,
                  playerA.aggregated_stats[key] as number,
                  playerB.aggregated_stats[key] as number,
                  higherIsBetter,
                )
              )}
            </tbody>
          </table>
        </div>
      )}

      {(playerA || playerB) && !(playerA && playerB) && (
        <div className="text-gray-400 mt-4">Load both players to see the comparison.</div>
      )}
    </div>
  )
}

import type { Player } from '../api/players'

interface PlayerTableProps {
  players: Player[]
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onPlayerClick: (player: Player) => void
}

export default function PlayerTable({
  players, total, page, pageSize, onPageChange, onPlayerClick,
}: PlayerTableProps) {
  const totalPages = Math.ceil(total / pageSize)

  const flagBadge = (flag: string | null) => {
    if (!flag) return null
    const color = flag === 'HIGH_VALUE' ? 'bg-green-800 text-green-200' : 'bg-amber-800 text-amber-200'
    const label = flag === 'HIGH_VALUE' ? 'Underpredicted' : 'Overperforming'
    return <span className={`text-xs px-2 py-0.5 rounded ${color}`}>{label}</span>
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800 text-left">
              <th className="py-2 pr-4">#</th>
              <th className="py-2 pr-4">Player</th>
              <th className="py-2 pr-4">Pos</th>
              <th className="py-2 pr-4">Team</th>
              <th className="py-2 pr-4">S_final</th>
              <th className="py-2 pr-4">G</th>
              <th className="py-2 pr-4">A</th>
              <th className="py-2 pr-4">xG</th>
              <th className="py-2 pr-4">xA</th>
              <th className="py-2 pr-4">Min</th>
              <th className="py-2">Flag</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => (
              <tr
                key={p.sofascore_player_id ?? `${p.name}|${p.team}`}
                onClick={() => onPlayerClick(p)}
                className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer"
              >
                <td className="py-2 pr-4 text-gray-500">{(page - 1) * pageSize + i + 1}</td>
                <td className="py-2 pr-4 font-medium">{p.name}</td>
                <td className="py-2 pr-4 text-gray-400">{p.position}</td>
                <td className="py-2 pr-4 text-gray-400">{p.team}</td>
                <td className="py-2 pr-4 font-mono text-indigo-300">{p.aggregated_scores.s_final.toFixed(2)}</td>
                <td className="py-2 pr-4">{p.aggregated_stats.goals}</td>
                <td className="py-2 pr-4">{p.aggregated_stats.assists}</td>
                <td className="py-2 pr-4 text-gray-400">{p.aggregated_stats.xg.toFixed(1)}</td>
                <td className="py-2 pr-4 text-gray-400">{p.aggregated_stats.xa.toFixed(1)}</td>
                <td className="py-2 pr-4 text-gray-400">{p.aggregated_stats.minutes}</td>
                <td className="py-2">{flagBadge(p.aggregated_scores.underpredicted_flag)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex gap-2 mt-4 justify-center">
          <button
            disabled={page === 1}
            onClick={() => onPageChange(page - 1)}
            className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-gray-400">{page} / {totalPages}</span>
          <button
            disabled={page === totalPages}
            onClick={() => onPageChange(page + 1)}
            className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

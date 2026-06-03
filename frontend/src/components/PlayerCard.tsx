import type { Player } from '../api/players'

interface PlayerCardProps { player: Player }

const StatRow = ({ label, value }: { label: string; value: string | number }) => (
  <div className="flex justify-between py-1 border-b border-gray-800 text-sm">
    <span className="text-gray-400">{label}</span>
    <span>{value}</span>
  </div>
)

export default function PlayerCard({ player: p }: PlayerCardProps) {
  const s = p.aggregated_stats
  const sc = p.aggregated_scores
  return (
    <div className="bg-gray-800 rounded-lg p-4 w-72">
      <div className="flex items-center gap-3 mb-4">
        <img
          src={p.photo_url || '/default-player.jpg'}
          alt={p.name}
          className="w-12 h-12 rounded-full object-cover bg-gray-700"
        />
        <div>
          <div className="font-semibold">{p.name}</div>
          <div className="text-xs text-gray-400">{p.position_exact} · {p.team}</div>
          <div className="text-xs text-gray-500">{p.nationality}</div>
        </div>
      </div>

      <div className="mb-3">
        <div className="text-xs text-gray-400 uppercase mb-1">Score</div>
        <div className="text-2xl font-mono text-indigo-300">{sc.s_final.toFixed(2)}</div>
        {sc.underpredicted_ratio != null && (
          <div className="text-xs text-gray-500 mt-0.5">underpredicted ratio: {sc.underpredicted_ratio.toFixed(2)}</div>
        )}
        {sc.underpredicted_flag && (
          <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${
            sc.underpredicted_flag === 'HIGH_VALUE' ? 'bg-green-800 text-green-200' : 'bg-amber-800 text-amber-200'
          }`}>{sc.underpredicted_flag === 'HIGH_VALUE' ? 'Underpredicted' : 'Overperforming'}</span>
        )}
      </div>

      <div className="text-xs text-gray-400 uppercase mb-1">Aggregate Stats</div>
      <StatRow label="Goals" value={s.goals} />
      <StatRow label="Assists" value={s.assists} />
      <StatRow label="xG" value={s.xg.toFixed(2)} />
      <StatRow label="xA" value={s.xa.toFixed(2)} />
      <StatRow label="Minutes" value={s.minutes} />
      <StatRow label="Rating" value={s.rating.toFixed(1)} />
      <StatRow label="Key Passes" value={s.key_passes} />
      <StatRow label="Big Chances" value={s.big_chances_created} />

      {p.competitions.length > 1 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 uppercase mb-1">Per Competition</div>
          {p.competitions.map((c) => (
            <div key={c.competition} className="text-xs py-1 flex justify-between">
              <span className="text-gray-400 truncate max-w-36">{c.competition}</span>
              <span className="font-mono text-indigo-300">{c.scores.s_final.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

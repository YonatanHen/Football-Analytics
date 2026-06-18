import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import type { Player } from '../api/players'

interface PlayerCardProps { player: Player; bioLoading?: boolean }

const StatRow = ({ label, value }: { label: string; value: string | number }) => (
  <div className="flex justify-between py-1 border-b border-gray-800 text-sm">
    <span className="text-gray-400">{label}</span>
    <span>{value}</span>
  </div>
)

export default function PlayerCard({ player: p, bioLoading = false }: PlayerCardProps) {
  const s = p.aggregated_stats
  const sc = p.aggregated_scores

  const totwTotal = p.competitions.reduce(
    (n, c) => n + (((c.raw_stats?.totwAppearances) as number) ?? 0), 0
  )

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
          <div className="text-xs text-gray-400">
            {bioLoading && !p.position_exact ? <span className="animate-pulse">…</span> : p.position_exact}
            {p.position_exact ? ' · ' : ''}{p.team}
          </div>
          <div className="text-xs text-gray-500">
            {bioLoading && !p.nationality ? <span className="animate-pulse">…</span> : p.nationality}
          </div>
        </div>
      </div>

      <div className="mb-3">
        <div className="text-xs text-gray-400 uppercase mb-1">Score</div>
        <div className="text-2xl font-mono text-indigo-300">{sc.s_final.toFixed(2)}</div>
        <div className="flex gap-2 mt-1 flex-wrap">
          {sc.underpredicted_flag && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              sc.underpredicted_flag === 'HIGH_VALUE' ? 'bg-green-800 text-green-200' : 'bg-amber-800 text-amber-200'
            }`}>{sc.underpredicted_flag === 'HIGH_VALUE' ? 'Underpredicted' : 'Overperforming'}</span>
          )}
          {totwTotal > 0 && (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-700 text-yellow-100">
              TOTW ×{totwTotal}
            </span>
          )}
        </div>
        {sc.underpredicted_ratio != null && (
          <div className="text-xs text-gray-500 mt-0.5">xRatio: {sc.underpredicted_ratio.toFixed(2)}</div>
        )}
      </div>

      <div className="text-xs text-gray-400 uppercase mb-1">Aggregate Stats</div>
      {s.appearances > 0 && (
        <StatRow label="Apps (started)" value={`${s.appearances} (${s.matches_started})`} />
      )}
      <StatRow label="Goals" value={s.goals} />
      <StatRow label="Assists" value={s.assists} />
      <StatRow label="xG" value={s.xg.toFixed(2)} />
      <StatRow label="xA" value={s.xa.toFixed(2)} />
      <StatRow label="Minutes" value={s.minutes} />
      {(s.yellow_red_cards > 0 || s.direct_red_cards > 0) && (
        <>
          <StatRow label="2nd Yellow" value={s.yellow_red_cards} />
          <StatRow label="Direct Red" value={s.direct_red_cards} />
        </>
      )}
      <StatRow label="Rating" value={s.rating.toFixed(1)} />
      <StatRow label="Key Passes" value={s.key_passes} />
      <StatRow label="Big Chances" value={s.big_chances_created} />

      {p.position === 'GK' && s.saves > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 uppercase mb-1">GK Stats</div>
          <StatRow label="Saves" value={s.saves} />
          <StatRow label="Goals Prevented" value={s.goals_prevented.toFixed(2)} />
          <StatRow label="High Claims" value={s.high_claims} />
          <StatRow label="Penalty Faced" value={s.penalty_faced} />
        </div>
      )}

      {s.goals > 0 && (s.headed_goals + s.left_foot_goals + s.right_foot_goals) > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 uppercase mb-1">Goal Types</div>
          <PieChart width={200} height={120}>
            <Pie
              data={[
                { name: 'Head', value: s.headed_goals },
                { name: 'Left', value: s.left_foot_goals },
                { name: 'Right', value: s.right_foot_goals },
              ].filter(d => d.value > 0)}
              cx={60} cy={55} innerRadius={25} outerRadius={45} dataKey="value"
            >
              {['#6366f1', '#22c55e', '#f59e0b'].map((color, i) => <Cell key={i} fill={color} />)}
            </Pie>
            <Tooltip formatter={(v: number, name: string) => [`${v}`, name]} contentStyle={{ background: '#1f2937', border: 'none', fontSize: 11 }} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </div>
      )}

      {s.total_shots > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-400 uppercase mb-1">Shots ({s.total_shots} total)</div>
          <PieChart width={200} height={120}>
            <Pie
              data={[
                { name: 'On Target', value: s.shots_on_target },
                { name: 'Off Target', value: s.shots_off_target },
                { name: 'Blocked', value: Math.max(0, s.total_shots - s.shots_on_target - s.shots_off_target) },
              ].filter(d => d.value > 0)}
              cx={60} cy={55} innerRadius={25} outerRadius={45} dataKey="value"
            >
              {['#22c55e', '#ef4444', '#6b7280'].map((color, i) => <Cell key={i} fill={color} />)}
            </Pie>
            <Tooltip formatter={(v: number, name: string) => [`${v}`, name]} contentStyle={{ background: '#1f2937', border: 'none', fontSize: 11 }} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </div>
      )}

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

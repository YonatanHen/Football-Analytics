import { useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import type { Player, Stats } from '../api/players'

const ALL_STATS: { key: keyof Stats; label: string; decimals?: number }[] = [
  { key: 'appearances', label: 'Appearances' },
  { key: 'matches_started', label: 'Matches Started' },
  { key: 'minutes', label: 'Minutes' },
  { key: 'goals', label: 'Goals' },
  { key: 'assists', label: 'Assists' },
  { key: 'xg', label: 'xG', decimals: 2 },
  { key: 'xa', label: 'xA', decimals: 2 },
  { key: 'key_passes', label: 'Key Passes' },
  { key: 'big_chances_created', label: 'Big Chances Created' },
  { key: 'total_shots', label: 'Total Shots' },
  { key: 'shots_on_target', label: 'Shots On Target' },
  { key: 'shots_off_target', label: 'Shots Off Target' },
  { key: 'headed_goals', label: 'Headed Goals' },
  { key: 'right_foot_goals', label: 'Right Foot Goals' },
  { key: 'left_foot_goals', label: 'Left Foot Goals' },
  { key: 'scoring_frequency', label: 'Scoring Frequency', decimals: 2 },
  { key: 'pk_won', label: 'PK Won' },
  { key: 'pk_scored', label: 'PK Scored' },
  { key: 'pk_taken', label: 'PK Taken' },
  { key: 'pk_saved', label: 'PK Saved' },
  { key: 'penalty_miss', label: 'Penalty Miss' },
  { key: 'penalty_faced', label: 'Penalty Faced' },
  { key: 'penalty_conceded', label: 'Penalty Conceded' },
  { key: 'fouls_committed', label: 'Fouls Committed' },
  { key: 'yellow_cards', label: 'Yellow Cards' },
  { key: 'yellow_red_cards', label: '2nd Yellow (Red)' },
  { key: 'direct_red_cards', label: 'Direct Red' },
  { key: 'red_cards', label: 'Red Cards (total)' },
  { key: 'clean_sheets', label: 'Clean Sheets' },
  { key: 'saves', label: 'Saves' },
  { key: 'saves_outside_box', label: 'Saves Outside Box' },
  { key: 'goals_conceded', label: 'Goals Conceded' },
  { key: 'goals_prevented', label: 'Goals Prevented', decimals: 2 },
  { key: 'high_claims', label: 'High Claims' },
  { key: 'rating', label: 'Rating', decimals: 1 },
]

interface PlayerCardProps { player: Player; bioLoading?: boolean }

const StatRow = ({ label, value }: { label: string; value: string | number }) => (
  <div className="flex justify-between py-1 border-b border-gray-800 text-sm">
    <span className="text-gray-400">{label}</span>
    <span>{value}</span>
  </div>
)

const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <div className="text-xs text-gray-400 uppercase mb-1">{children}</div>
)

interface DonutDatum { name: string; value: number; color: string }

const Donut = ({ title, data }: { title: string; data: DonutDatum[] }) => {
  const slices = data.filter((d) => d.value > 0)
  return (
    <div className="flex flex-col items-center">
      <SectionTitle>{title}</SectionTitle>
      <PieChart width={240} height={190}>
        <Pie data={slices} cx={120} cy={80} innerRadius={38} outerRadius={64} dataKey="value">
          {slices.map((d) => <Cell key={d.name} fill={d.color} />)}
        </Pie>
        <Tooltip
          formatter={(v: number, name: string) => [`${v}`, name]}
          contentStyle={{ background: '#1f2937', border: 'none', fontSize: 11 }}
        />
        <Legend iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
      </PieChart>
    </div>
  )
}

export default function PlayerCard({ player: p, bioLoading = false }: PlayerCardProps) {
  const s = p.aggregated_stats
  const sc = p.aggregated_scores
  const [showAll, setShowAll] = useState(false)

  const totwTotal = p.competitions.reduce(
    (n, c) => n + (((c.raw_stats?.totwAppearances) as number) ?? 0), 0
  )

  const showGoalTypes = s.goals > 0 && (s.headed_goals + s.left_foot_goals + s.right_foot_goals) > 0
  const showShots = s.total_shots > 0

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center gap-4 mb-5">
        <img
          src={p.photo_url || '/default-player.jpg'}
          alt={p.name}
          className="w-16 h-16 rounded-full object-cover bg-gray-700"
        />
        <div>
          <div className="text-lg font-semibold">{p.name}</div>
          <div className="text-sm text-gray-400">
            {bioLoading && !p.position_exact ? <span className="animate-pulse">…</span> : p.position_exact}
            {p.position_exact ? ' · ' : ''}{p.team}
          </div>
          <div className="text-sm text-gray-500">
            {bioLoading && !p.nationality ? <span className="animate-pulse">…</span> : p.nationality}
          </div>
        </div>
      </div>

      {/* Score */}
      <div className="mb-5 flex items-end gap-4 flex-wrap">
        <div>
          <SectionTitle>Score</SectionTitle>
          <div className="text-3xl font-mono text-indigo-300 leading-none">{sc.s_final.toFixed(2)}</div>
        </div>
        <div className="flex gap-2 flex-wrap pb-1">
          {sc.underpredicted_flag && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              sc.underpredicted_flag === 'HIGH_VALUE' ? 'bg-amber-800 text-amber-200' : 'bg-green-800 text-green-200'
            }`}>{sc.underpredicted_flag === 'HIGH_VALUE' ? 'Underpredicted' : 'Overperforming'}</span>
          )}
          {totwTotal > 0 && (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-700 text-yellow-100">TOTW ×{totwTotal}</span>
          )}
          {sc.underpredicted_ratio != null && (
            <span className="text-xs text-gray-500 self-center">xRatio: {sc.underpredicted_ratio.toFixed(2)}</span>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
        <div>
          <SectionTitle>Aggregate Stats</SectionTitle>
          {s.appearances > 0 && (
            <StatRow label="Apps (started)" value={`${s.appearances} (${s.matches_started})`} />
          )}
          <StatRow label="Goals" value={s.goals} />
          <StatRow label="Assists" value={s.assists} />
          <StatRow label="xG" value={s.xg.toFixed(2)} />
          <StatRow label="xA" value={s.xa.toFixed(2)} />
          <StatRow label="Minutes" value={s.minutes} />
          <StatRow label="Yellow Cards" value={s.yellow_cards} />
          <StatRow label="Red Cards" value={s.red_cards} />
          <StatRow label="Rating" value={s.rating.toFixed(1)} />
          <StatRow label="Key Passes" value={s.key_passes} />
          <StatRow label="Big Chances" value={s.big_chances_created} />
        </div>

        <div>
          {p.position === 'GK' && s.saves > 0 && (
            <>
              <SectionTitle>GK Stats</SectionTitle>
              <StatRow label="Saves" value={s.saves} />
              <StatRow label="Goals Prevented" value={s.goals_prevented.toFixed(2)} />
              <StatRow label="High Claims" value={s.high_claims} />
              <StatRow label="Penalty Faced" value={s.penalty_faced} />
            </>
          )}

          {p.competitions.length > 1 && (
            <div className={p.position === 'GK' && s.saves > 0 ? 'mt-4' : ''}>
              <SectionTitle>Per Competition</SectionTitle>
              {p.competitions.map((c) => (
                <div key={c.competition} className="text-sm py-1 flex justify-between border-b border-gray-800">
                  <span className="flex items-center gap-1 text-gray-400 truncate max-w-44">
                    {c.competition}
                    <span className={`text-xs px-1 rounded shrink-0 ${
                      c.competition_type === 'national'
                        ? 'bg-blue-900 text-blue-300'
                        : 'bg-gray-700 text-gray-400'
                    }`}>
                      {c.competition_type === 'national' ? 'NT' : 'Club'}
                    </span>
                  </span>
                  <span className="font-mono text-indigo-300">{c.scores.s_final.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Charts row */}
      {(showGoalTypes || showShots) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5 justify-items-center">
          {showGoalTypes && (
            <Donut
              title="Goal Types"
              data={[
                { name: 'Head', value: s.headed_goals, color: '#6366f1' },
                { name: 'Left', value: s.left_foot_goals, color: '#22c55e' },
                { name: 'Right', value: s.right_foot_goals, color: '#f59e0b' },
              ]}
            />
          )}
          {showShots && (
            <Donut
              title={`Shots (${s.total_shots} total)`}
              data={[
                { name: 'On Target', value: s.shots_on_target, color: '#22c55e' },
                { name: 'Off Target', value: s.shots_off_target, color: '#ef4444' },
                { name: 'Blocked', value: Math.max(0, s.total_shots - s.shots_on_target - s.shots_off_target), color: '#6b7280' },
              ]}
            />
          )}
        </div>
      )}

      {/* All data toggle */}
      <div className="mt-5">
        <button
          onClick={() => setShowAll(v => !v)}
          className="text-xs text-indigo-400 hover:text-indigo-300 underline"
        >
          {showAll ? 'Hide full data' : 'Show all data'}
        </button>
        {showAll && (
          <div className="mt-3 grid grid-cols-2 gap-x-6">
            {ALL_STATS.map(({ key, label, decimals }) => {
              const val = s[key] as number
              const formatted = decimals !== undefined ? val.toFixed(decimals) : val
              return (
                <div key={key} className="flex justify-between py-1 border-b border-gray-800 text-sm">
                  <span className="text-gray-400">{label}</span>
                  <span className="font-mono">{formatted}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

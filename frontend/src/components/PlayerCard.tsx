import { useState } from 'react'
import { ArrowLeftRight, ChevronDown, ChevronUp, X } from 'lucide-react'
import type { Player, Stats } from '../api/players'
import { shortDate, totwCount } from '../lib/format'
import Avatar from './ui/Avatar'
import { Chip, CompTag, PosBadge, TotwBadge } from './ui/Badges'
import StackedBar from './ui/StackedBar'
import StatRow from './ui/StatRow'

const ALL_STATS: { key: keyof Stats; label: string; decimals?: number }[] = [
  { key: 'appearances', label: 'Appearances' },
  { key: 'matches_started', label: 'Matches started' },
  { key: 'minutes', label: 'Minutes' },
  { key: 'goals', label: 'Goals' },
  { key: 'assists', label: 'Assists' },
  { key: 'xg', label: 'xG', decimals: 2 },
  { key: 'xa', label: 'xA', decimals: 2 },
  { key: 'key_passes', label: 'Key passes' },
  { key: 'big_chances_created', label: 'Big chances created' },
  { key: 'total_shots', label: 'Total shots' },
  { key: 'shots_on_target', label: 'Shots on target' },
  { key: 'shots_off_target', label: 'Shots off target' },
  { key: 'headed_goals', label: 'Headed goals' },
  { key: 'right_foot_goals', label: 'Right-foot goals' },
  { key: 'left_foot_goals', label: 'Left-foot goals' },
  { key: 'scoring_frequency', label: 'Scoring frequency', decimals: 2 },
  { key: 'pk_won', label: 'Penalties won' },
  { key: 'pk_scored', label: 'Penalties scored' },
  { key: 'pk_taken', label: 'Penalties taken' },
  { key: 'pk_saved', label: 'Penalties saved' },
  { key: 'penalty_miss', label: 'Penalties missed' },
  { key: 'penalty_faced', label: 'Penalties faced' },
  { key: 'penalty_conceded', label: 'Penalties conceded' },
  { key: 'fouls_committed', label: 'Fouls committed' },
  { key: 'yellow_cards', label: 'Yellow cards' },
  { key: 'yellow_red_cards', label: 'Second-yellow reds' },
  { key: 'direct_red_cards', label: 'Direct reds' },
  { key: 'red_cards', label: 'Red cards (total)' },
  { key: 'clean_sheets', label: 'Clean sheets' },
  { key: 'saves', label: 'Saves' },
  { key: 'saves_outside_box', label: 'Saves outside box' },
  { key: 'goals_conceded', label: 'Goals conceded' },
  { key: 'goals_prevented', label: 'Goals prevented', decimals: 2 },
  { key: 'high_claims', label: 'High claims' },
  { key: 'rating', label: 'Rating', decimals: 1 },
]

const C = { green: '#34d98c', blue: '#6fa8ea', amber: '#e9b44c', red: '#e5564d', gray: '#2f3d36' }

interface PlayerCardProps {
  player: Player
  bioLoading?: boolean
  onClose: () => void
  onCompare?: () => void
}

export default function PlayerCard({ player: p, bioLoading = false, onClose, onCompare }: PlayerCardProps) {
  const s = p.aggregated_stats
  const sc = p.aggregated_scores
  const [showAll, setShowAll] = useState(false)
  const totw = totwCount(p)
  const blocked = Math.max(0, s.total_shots - s.shots_on_target - s.shots_off_target)
  const pending = <span className="animate-pulse">…</span>

  return (
    <div>
      <div className="flex items-start gap-5">
        <Avatar name={p.name} size="lg" />
        <div className="flex-1 pt-1">
          <h2 className="text-[26px] font-semibold leading-tight tracking-tight">{p.name}</h2>
          <div className="mt-1.5 flex items-center gap-2 text-sm text-ink/90">
            {bioLoading && !p.position_exact ? pending : <PosBadge pos={p.position_exact || p.position} />}
            <span>{p.team}</span>
            <span className="text-dim">·</span>
            <span className="text-muted">{bioLoading && !p.nationality ? pending : p.nationality}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 pt-2">
          {totw > 0 && <TotwBadge count={totw} />}
          {sc.underpredicted_ratio != null && <Chip>xRatio {sc.underpredicted_ratio.toFixed(2)}</Chip>}
          <button onClick={onClose} aria-label="Close" className="ml-3 rounded-md border border-line-strong p-2 text-muted hover:text-ink">
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="mt-7 flex items-center rounded-lg bg-surface-2/70 px-6 py-5">
        <div className="pr-8">
          <div className="label-caps">Fantasy Score</div>
          <div className="mt-2 font-mono text-[40px] font-medium leading-none text-accent">{sc.s_final.toFixed(2)}</div>
        </div>
        <div className="mx-2 h-16 w-px bg-line-strong" />
        <ScoreStat label="Offensive" value={sc.offensive} strong />
        <ScoreStat label="Defensive" value={sc.defensive} />
        <ScoreStat label="Tactical" value={sc.tactical} />
        <div className="ml-auto text-right">
          <div className="label-caps">Confidence</div>
          <div className="mt-3 flex items-center gap-3">
            <div className="h-[3px] w-24 rounded bg-line-strong">
              <div className="h-full rounded bg-accent" style={{ width: `${sc.confidence * 100}%` }} />
            </div>
            <span className="font-mono text-sm">{sc.confidence.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="mt-7 grid grid-cols-1 gap-10 md:grid-cols-2">
        <div>
          <div className="label-caps mb-2">Aggregate stats</div>
          <StatRow label="Appearances (started)" value={`${s.appearances} (${s.matches_started})`} />
          <StatRow label="Minutes" value={s.minutes} />
          <StatRow label="Goals" value={s.goals} />
          <StatRow label="Assists" value={s.assists} />
          <StatRow label="xG" value={s.xg.toFixed(2)} />
          <StatRow label="xA" value={s.xa.toFixed(2)} />
          {p.position === 'GK' ? (
            <>
              <StatRow label="Saves" value={s.saves} />
              <StatRow label="Goals prevented" value={s.goals_prevented.toFixed(2)} />
              <StatRow label="Clean sheets" value={s.clean_sheets} />
            </>
          ) : (
            <>
              <StatRow label="Key passes" value={s.key_passes} />
              <StatRow label="Big chances created" value={s.big_chances_created} />
              <StatRow label="Shots on target" value={s.shots_on_target} />
            </>
          )}
          <StatRow label="Yellow / Red" value={`${s.yellow_cards} / ${s.red_cards}`} />
          <StatRow label="Rating" value={s.rating.toFixed(1)} />
        </div>

        <div>
          <div className="label-caps mb-2">Per competition</div>
          {p.competitions.map((c) => (
            <div key={c.competition} className="flex items-center justify-between border-b border-line py-2.5 text-[13px]">
              <span className="flex min-w-0 items-center gap-2">
                <span className="truncate">{c.competition}</span>
                <CompTag national={c.competition_type === 'national'} />
              </span>
              <span className="font-mono text-accent">{c.scores.s_final.toFixed(2)}</span>
            </div>
          ))}
          {s.goals > 0 && (
            <div className="mt-6">
              <StackedBar
                title="Goal types"
                total={s.goals}
                segments={[
                  { label: 'Right foot', value: s.right_foot_goals, color: C.green },
                  { label: 'Left foot', value: s.left_foot_goals, color: C.blue },
                  { label: 'Header', value: s.headed_goals, color: C.amber },
                ]}
              />
            </div>
          )}
          {s.total_shots > 0 && (
            <div className="mt-6">
              <StackedBar
                title="Shot outcome"
                total={s.total_shots}
                segments={[
                  { label: 'On target', value: s.shots_on_target, color: C.green },
                  { label: 'Off target', value: s.shots_off_target, color: C.red },
                  { label: 'Blocked', value: blocked, color: C.gray },
                ]}
              />
            </div>
          )}
        </div>
      </div>

      {showAll && (
        <div className="mt-6 grid grid-cols-1 gap-x-10 md:grid-cols-2">
          {ALL_STATS.map(({ key, label, decimals }) => {
            const v = s[key] as number
            return <StatRow key={key} label={label} value={decimals !== undefined ? v.toFixed(decimals) : v} />
          })}
        </div>
      )}

      <div className="mt-7 flex items-center gap-3">
        <button onClick={() => setShowAll((v) => !v)} className="btn-ghost h-10 px-4">
          {showAll ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          {showAll ? 'Hide metrics' : `Show all ${ALL_STATS.length} metrics`}
        </button>
        {onCompare && (
          <button onClick={onCompare} className="btn-accent h-10 px-4">
            <ArrowLeftRight size={15} /> Compare with...
          </button>
        )}
        <span className="ml-auto font-mono text-[11px] text-muted">last updated {shortDate(p.last_updated, true)}</span>
      </div>
    </div>
  )
}

function ScoreStat({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className="w-40 pl-6">
      <div className="label-caps">{label}</div>
      <div className={`mt-2 font-mono text-2xl ${strong ? 'text-ink' : 'text-ink/70'}`}>{value.toFixed(1)}</div>
    </div>
  )
}

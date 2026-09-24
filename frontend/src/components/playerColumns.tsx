import { totwCount } from '../lib/format'
import Avatar from './ui/Avatar'
import { FlagBadge, PosBadge, TotwBadge } from './ui/Badges'
import type { Column } from './PlayerTable'

const num = 'font-mono text-ink/90'

export const COL = {
  rank: { key: 'rank', label: '#', className: 'w-10 font-mono text-dim', render: (_p, r) => r },
  player: {
    key: 'player',
    label: 'Player',
    render: (p) => (
      <div className="flex items-center gap-3">
        <Avatar name={p.name} />
        <div className="leading-tight">
          <div className="text-[13px] text-ink">{p.name}</div>
          <div className="text-[11px] text-muted">{p.nationality || '—'}</div>
        </div>
      </div>
    ),
  },
  pos: { key: 'pos', label: 'Pos', render: (p) => <PosBadge pos={p.position} /> },
  team: { key: 'team', label: 'Team', className: 'text-ink/90', render: (p) => p.team },
  apps: { key: 'apps', label: 'Apps', sortKey: 'appearances', className: num, render: (p) => p.aggregated_stats.appearances },
  goals: { key: 'g', label: 'G', sortKey: 'goals', className: 'font-mono text-ink', render: (p) => p.aggregated_stats.goals },
  assists: { key: 'a', label: 'A', sortKey: 'assists', className: 'font-mono text-ink', render: (p) => p.aggregated_stats.assists },
  xg: { key: 'xg', label: 'xG', sortKey: 'xg', className: num, render: (p) => p.aggregated_stats.xg.toFixed(1) },
  xa: { key: 'xa', label: 'xA', sortKey: 'xa', className: num, render: (p) => p.aggregated_stats.xa.toFixed(1) },
  minutes: { key: 'min', label: 'Min', sortKey: 'minutes', className: num, render: (p) => p.aggregated_stats.minutes },
  rating: { key: 'rating', label: 'Rating', sortKey: 'rating', className: num, render: (p) => p.aggregated_stats.rating.toFixed(1) },
  signal: {
    key: 'signal',
    label: 'Signal',
    render: (p) => {
      const flag = p.aggregated_scores.underpredicted_flag
      const totw = totwCount(p)
      if (!flag && !totw) return <span className="text-dim">—</span>
      return (
        <div className="flex gap-2">
          {flag && <FlagBadge flag={flag} />}
          {totw > 0 && <TotwBadge count={totw} />}
        </div>
      )
    },
  },
} satisfies Record<string, Column>

import type { Player } from '../api/players'

export const initials = (name: string) =>
  name
    .replace(/^[A-Z]\.\s*/, '')
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || '?'

export const int = (n: number) => Math.round(n).toLocaleString('en-US')

export const signed = (n: number, d = 1) => `${n > 0 ? '+' : ''}${n.toFixed(d)}`

// Sofascore reports TOTW per competition, in untyped raw_stats.
export const totwCount = (p: Player) =>
  p.competitions.reduce((n, c) => n + (Number(c.raw_stats?.totwAppearances) || 0), 0)

export const xgiGap = (p: Player) => {
  const s = p.aggregated_stats
  return s.xg + s.xa - (s.goals + s.assists)
}

export const shortDate = (iso: string | null | undefined, withYear = false) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}

import type { ReactNode } from 'react'
import { Plus } from 'lucide-react'
import type { Meta } from '../api/meta'
import type { Tab } from '../context/AppContext'
import { shortDate } from '../lib/format'
import { Select } from './ui/Fields'

export type Status = 'loading' | 'ok' | 'empty' | 'down'

const TABS: { id: Tab; label: string }[] = [
  { id: 'players', label: 'Player details' },
  { id: 'compare', label: 'Compare' },
  { id: 'sleepers', label: 'xGI Outliers' },
  { id: 'scatter', label: 'Scatter Plot' },
  { id: 'chat', label: 'Ask AI' },
]

interface ShellProps {
  tab: Tab
  onTab: (t: Tab) => void
  status: Status
  meta: Meta | null
  season: string
  onSeason: (s: string) => void
  onNewChat: () => void
  children: ReactNode
}

export default function AppShell({ tab, onTab, status, meta, season, onSeason, onNewChat, children }: ShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="sticky top-0 z-40 border-b border-line bg-header">
        <div className="flex h-14 items-center gap-10 px-8">
          <div className="whitespace-nowrap text-[15px] font-semibold tracking-[0.12em]">
            FOOTBALL <span className="text-accent">ANALYTICS</span>
          </div>
          <nav className="flex h-full">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => onTab(t.id)}
                className={`relative h-full px-4 text-[14px] transition-colors ${
                  tab === t.id ? 'text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {t.label}
                {tab === t.id && <span className="absolute inset-x-0 -bottom-px h-[2px] bg-accent" />}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-6">
            <HeaderStatus tab={tab} status={status} meta={meta} />
            {tab === 'chat' ? (
              <button onClick={onNewChat} className="btn-ghost h-8 text-muted hover:text-ink">
                <Plus size={14} /> New chat
              </button>
            ) : (
              status === 'ok' && meta && meta.seasons.length > 0 && (
                <Select value={season} onChange={onSeason} size="sm" className="w-32 font-mono">
                  {meta.seasons.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
              )
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 px-8 pb-10 pt-8">{children}</main>
    </div>
  )
}

function HeaderStatus({ tab, status, meta }: { tab: Tab; status: Status; meta: Meta | null }) {
  const cls = 'flex items-center gap-2 whitespace-nowrap font-mono text-[11px]'
  if (status === 'down') {
    return <span className={`${cls} text-danger`}><span className="h-1.5 w-1.5 rounded-full bg-danger" />backend unreachable</span>
  }
  if (!meta) return null
  if (tab === 'chat') {
    return (
      <span className={`${cls} text-muted`}>
        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
        {meta.agent.model}<span className="mx-1 text-dim">·</span>{meta.agent.max_tool_calls} tool calls max
      </span>
    )
  }
  if (status === 'empty') {
    return (
      <span className={`${cls} text-warn`}>
        <span className="h-1.5 w-1.5 rounded-full bg-warn" />0 players<span className="mx-1">·</span>database empty
      </span>
    )
  }
  const updated = shortDate(meta.last_updated)
  return (
    <span className={`${cls} text-muted`}>
      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
      {meta.players_total.toLocaleString('en-US')} players
      {updated && <><span className="mx-1 text-dim">·</span>updated {updated}</>}
    </span>
  )
}

import type { ReactNode } from 'react'
import type { Player, SortOrder } from '../api/players'

export interface Column {
  key: string
  label: string
  sortKey?: string
  className?: string
  render: (p: Player, rank: number) => ReactNode
}

interface PlayerTableProps {
  players: Player[]
  columns: Column[]
  rankOffset: number
  onRowClick: (p: Player) => void
  sortBy?: string
  order?: SortOrder
  onSort?: (key: string) => void
  dimmed?: boolean
}

export default function PlayerTable({
  players, columns, rankOffset, onRowClick, sortBy, order, onSort, dimmed = false,
}: PlayerTableProps) {
  return (
    <div className={`overflow-x-auto transition-opacity ${dimmed ? 'opacity-50' : ''}`}>
      <table className="w-full border-separate border-spacing-0 text-left">
        <thead>
          <tr>
            {columns.map((c, i) => {
              const active = c.sortKey !== undefined && c.sortKey === sortBy
              const sortable = c.sortKey !== undefined && onSort
              return (
                <th
                  key={c.key}
                  onClick={sortable ? () => onSort(c.sortKey!) : undefined}
                  className={`h-11 bg-surface px-3 font-mono text-[10px] font-normal uppercase tracking-[0.16em] ${
                    i === 0 ? 'rounded-tl-lg pl-4' : ''
                  } ${i === columns.length - 1 ? 'rounded-tr-lg' : ''} ${
                    active ? 'text-accent' : 'text-dim'
                  } ${sortable ? 'cursor-pointer select-none hover:text-ink' : ''} ${c.className ?? ''}`}
                >
                  {c.label}
                  {active && <span className="ml-1.5">{order === 'asc' ? '▲' : '▼'}</span>}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr
              key={p.sofascore_player_id || `${p.name}|${p.team}`}
              onClick={() => onRowClick(p)}
              className="cursor-pointer transition-colors hover:bg-surface/70"
            >
              {columns.map((c, j) => (
                <td
                  key={c.key}
                  className={`h-[46px] border-b border-line px-3 text-[13px] ${j === 0 ? 'pl-4' : ''} ${c.className ?? ''}`}
                >
                  {c.render(p, rankOffset + i + 1)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

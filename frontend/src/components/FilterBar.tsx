import { useEffect, useRef, useState } from 'react'
import { Flag, Plus, Search, Shield } from 'lucide-react'
import type { CompetitionList, FilterClause, FilterOp, SortOrder } from '../api/players'
import { clauseLabel, metricLabel, type Filters } from '../lib/filters'
import { FILTER_OP_OPTIONS, METRIC_OPTIONS } from '../api/players'
import { IconInput, Select } from './ui/Fields'
import FilterChip from './ui/FilterChip'
import Segmented from './ui/Segmented'

const VIEWS = [
  { value: 'all', label: 'All' },
  { value: 'club', label: 'Club' },
  { value: 'national', label: 'National' },
] as const

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
  competitions?: CompetitionList
  sortBy: string
  order: SortOrder
}

export default function FilterBar({ filters, onChange, competitions, sortBy, order }: FilterBarProps) {
  const set = (key: keyof Filters) => (v: string) => onChange({ ...filters, [key]: v })
  const isView = ['', 'club', 'national'].includes(filters.stats_view)
  const removeClause = (i: number) =>
    onChange({ ...filters, clauses: filters.clauses.filter((_, j) => j !== i) })

  return (
    <div className="mb-5 flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2.5">
        <IconInput icon={Search} value={filters.name} onChange={set('name')} placeholder="Player name..." className="w-[236px]" />
        <Select value={filters.position} onChange={set('position')} className="w-[156px]">
          <option value="">All positions</option>
          {['GK', 'DF', 'MF', 'FW'].map((p) => <option key={p} value={p}>{p}</option>)}
        </Select>
        <IconInput icon={Shield} value={filters.team} onChange={set('team')} placeholder="Team..." className="w-[168px]" />
        <IconInput icon={Flag} value={filters.nationality} onChange={set('nationality')} placeholder="Nationality..." className="w-[168px]" />
        <Select value={filters.underpredicted_flag} onChange={set('underpredicted_flag')} className="w-[156px]">
          <option value="">All flags</option>
          <option value="HIGH_VALUE">Due to score</option>
          <option value="OVERPERFORMING">Overperforming</option>
        </Select>
        <div className="ml-auto">
          <AddMetricFilter onAdd={(c) => onChange({ ...filters, clauses: [...filters.clauses, c] })} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <span className="label-caps mr-1">Stats view</span>
        <Segmented
          size="sm"
          options={[...VIEWS]}
          value={isView ? (filters.stats_view || 'all') : null}
          onChange={(v) => set('stats_view')(v === 'all' ? '' : v)}
        />
        {competitions && (
          <Select
            size="sm"
            value={isView ? '' : filters.stats_view}
            onChange={set('stats_view')}
            className="w-[120px]"
          >
            <option value="">Competition...</option>
            {competitions.club.length > 0 && (
              <optgroup label="Club">
                {competitions.club.map((c) => <option key={c} value={c}>{c}</option>)}
              </optgroup>
            )}
            {competitions.national.length > 0 && (
              <optgroup label="National">
                {competitions.national.map((c) => <option key={c} value={c}>{c}</option>)}
              </optgroup>
            )}
          </Select>
        )}
        {filters.clauses.length > 0 && <span className="mx-1 h-5 w-px bg-line-strong" />}
        {filters.clauses.map((c, i) => (
          <FilterChip key={`${c.field}-${i}`} label={clauseLabel(c)} onRemove={() => removeClause(i)} />
        ))}
        <span className="ml-auto font-mono text-[11px] text-muted">
          sorted by {metricLabel(sortBy)} {order === 'asc' ? '▲' : '▼'}
        </span>
      </div>
    </div>
  )
}

function AddMetricFilter({ onAdd }: { onAdd: (c: FilterClause) => void }) {
  const [open, setOpen] = useState(false)
  const [field, setField] = useState('minutes')
  const [op, setOp] = useState<FilterOp>('gte')
  const [value, setValue] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const n = Number(value)
  const valid = value.trim() !== '' && Number.isFinite(n)
  const add = () => {
    if (!valid) return
    onAdd({ field, op, value: n })
    setValue('')
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((o) => !o)} className="btn-accent h-10 px-4">
        <Plus size={15} /> Add metric filter
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-30 w-[340px] rounded-lg border border-line-strong bg-surface p-3 shadow-2xl">
          <div className="label-caps mb-2">New clause</div>
          <div className="flex gap-2">
            <Select value={field} onChange={setField} size="sm" className="flex-1">
              {METRIC_OPTIONS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </Select>
            <Select value={op} onChange={(v) => setOp(v as FilterOp)} size="sm" className="w-16">
              {FILTER_OP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </Select>
            <input
              autoFocus
              type="number"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && add()}
              placeholder="0"
              className="field h-8 w-20 px-2 font-mono text-xs"
            />
          </div>
          <button disabled={!valid} onClick={add} className="btn-solid mt-3 h-8 w-full justify-center">
            Apply
          </button>
        </div>
      )}
    </div>
  )
}

import type { CompetitionList } from '../api/players'

export interface Filters {
  position: string; team: string; nationality: string; underpredicted_flag: string; stats_view: string
}

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
  competitions?: CompetitionList
}

const POSITIONS = ['', 'GK', 'DF', 'MF', 'FW']
const VIEW_SEGMENTS = [
  { value: '', label: 'All' },
  { value: 'club', label: 'Club' },
  { value: 'national', label: 'National' },
]

export default function FilterBar({ filters, onChange, competitions }: FilterBarProps) {
  const set = (key: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...filters, [key]: e.target.value })

  const setView = (value: string) => onChange({ ...filters, stats_view: value })

  const isCompView = filters.stats_view !== '' && filters.stats_view !== 'club' && filters.stats_view !== 'national'

  return (
    <div className="flex flex-col gap-3 mb-4">
      <div className="flex flex-wrap gap-3">
        <select
          value={filters.position}
          onChange={set('position')}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
        >
          {POSITIONS.map((p) => <option key={p} value={p}>{p || 'All positions'}</option>)}
        </select>

        <input
          value={filters.team}
          onChange={set('team')}
          placeholder="Team..."
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-40"
        />

        <input
          value={filters.nationality}
          onChange={set('nationality')}
          placeholder="Nationality..."
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-40"
        />

        <select
          value={filters.underpredicted_flag}
          onChange={set('underpredicted_flag')}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
        >
          <option value="">All flags</option>
          <option value="HIGH_VALUE">Underpredicted</option>
          <option value="OVERPERFORMING">Overperforming</option>
        </select>
      </div>

      {/* Stats View selector */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-400 mr-1">Stats view:</span>
        {VIEW_SEGMENTS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setView(value)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filters.stats_view === value && !isCompView
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}

        {competitions && (
          <select
            value={isCompView ? filters.stats_view : ''}
            onChange={(e) => e.target.value ? setView(e.target.value) : setView('')}
            className={`bg-gray-800 border rounded px-2 py-1 text-xs ${
              isCompView ? 'border-indigo-500 text-white' : 'border-gray-700 text-gray-400'
            }`}
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
          </select>
        )}
      </div>
    </div>
  )
}

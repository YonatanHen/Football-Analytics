interface Filters {
  position: string; team: string; nationality: string; sleeper_flag: string
}

interface FilterBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
}

const POSITIONS = ['', 'GK', 'DF', 'MF', 'FW']
const SLEEPER_FLAGS = ['', 'HIGH_VALUE', 'OVERPERFORMING']

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  const set = (key: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...filters, [key]: e.target.value })

  return (
    <div className="flex flex-wrap gap-3 mb-4">
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
        value={filters.sleeper_flag}
        onChange={set('sleeper_flag')}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
      >
        {SLEEPER_FLAGS.map((f) => <option key={f} value={f}>{f || 'All sleeper flags'}</option>)}
      </select>
    </div>
  )
}

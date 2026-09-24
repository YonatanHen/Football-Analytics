import { useState, useEffect, useCallback, useRef } from 'react'
import { getPlayers, getPlayerCompetitions, serializeFilters, type Player, type PlayerList, type CompetitionList, type SortOrder } from '../api/players'
import { useApp } from '../context/AppContext'
import FilterBar from '../components/FilterBar'
import { EMPTY_FILTERS, clauseLabel, type Filters } from '../lib/filters'
import PlayerTable, { type Column } from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'
import { COL } from '../components/playerColumns'
import { NoResults, TableSkeleton } from '../components/states/SystemStates'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import ScoreBar from '../components/ui/ScoreBar'

const SEARCH_DEBOUNCE_MS = 250
const PAGE_SIZE = 50

// Wait for a pause in typing so one keystroke does not mean one request.
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

const TEXT_FILTERS: { key: keyof Filters; label: string }[] = [
  { key: 'name', label: 'name' },
  { key: 'position', label: 'position' },
  { key: 'team', label: 'team' },
  { key: 'nationality', label: 'nationality' },
  { key: 'underpredicted_flag', label: 'flag' },
  { key: 'stats_view', label: 'view' },
]

export default function PlayerDetails() {
  const { season } = useApp()
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [sortBy, setSortBy] = useState('s_final')
  const [order, setOrder] = useState<SortOrder>('desc')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalId, setModalId] = useState<string | null>(null)
  const [modalPlayer, setModalPlayer] = useState<Player | null>(null)
  const [competitions, setCompetitions] = useState<CompetitionList | undefined>(undefined)
  const requestId = useRef(0)

  const debouncedFilters = useDebounced(filters, SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    getPlayerCompetitions(season).then(setCompetitions).catch(console.error)
  }, [season])

  const openPlayer = (p: Player) =>
    p.sofascore_player_id ? setModalId(p.sofascore_player_id) : setModalPlayer(p)
  const closeModal = () => { setModalId(null); setModalPlayer(null) }

  const load = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    try {
      const f = debouncedFilters
      const params: Record<string, string | number> = { season, page, page_size: PAGE_SIZE, sort_by: sortBy, order }
      if (f.name) params.name = f.name
      if (f.position) params.position = f.position
      if (f.team) params.team = f.team
      if (f.nationality) params.nationality = f.nationality
      if (f.underpredicted_flag) params.underpredicted_flag = f.underpredicted_flag
      if (f.stats_view) params.stats_view = f.stats_view
      const serialized = serializeFilters(f.clauses)
      if (serialized) params.filters = serialized
      const result = await getPlayers(params)
      // A slower earlier request must not overwrite a newer one's rows.
      if (id === requestId.current) { setData(result); setError('') }
    } catch (e) {
      console.error(e)
      // Drop the rows too: stale ones would read as results for the new search.
      if (id === requestId.current) { setData(null); setError(e instanceof Error ? e.message : 'Search failed') }
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [debouncedFilters, page, sortBy, order, season])

  const handleSort = (field: string) => {
    if (field === sortBy) setOrder((o) => (o === 'desc' ? 'asc' : 'desc'))
    else { setSortBy(field); setOrder('desc') }
    setPage(1)
  }

  const update = (f: Filters) => { setFilters(f); setPage(1) }

  // Hold every request until typing settles, so a page reset cannot fire an unfiltered one first.
  const settling = filters !== debouncedFilters
  useEffect(() => { if (!settling) load() }, [load, settling])

  const active = [
    ...TEXT_FILTERS.filter((t) => filters[t.key]).map((t) => `${t.label}: ${filters[t.key]}`),
    ...filters.clauses.map(clauseLabel),
  ]
  const removeLast = () => {
    if (filters.clauses.length) return update({ ...filters, clauses: filters.clauses.slice(0, -1) })
    const last = [...TEXT_FILTERS].reverse().find((t) => filters[t.key])
    if (last) update({ ...filters, [last.key]: '' })
  }

  const maxScore = Math.max(...(data?.data.map((p) => p.aggregated_scores.s_final) ?? [0]), 0.01)
  const columns: Column[] = [
    COL.rank, { ...COL.player, className: 'min-w-[220px]' }, COL.pos, COL.team,
    {
      key: 'score', label: 'Fantasy Score', sortKey: 's_final',
      render: (p) => (
        <ScoreBar label={p.aggregated_scores.s_final.toFixed(2)} fraction={p.aggregated_scores.s_final / (maxScore * 1.08)} />
      ),
    },
    COL.apps, COL.goals, COL.assists, COL.xg, COL.xa, COL.minutes, COL.rating, COL.signal,
  ]

  return (
    <div>
      <PageHeader
        title="Player details"
        subtitle={<>Ranked by Fantasy Score<span className="ml-6">S_final = raw/90 × starter × confidence + playing-time bonus</span></>}
        right={data && (
          <span className="text-sm text-muted">
            <span className="mr-1 font-mono text-base text-ink">{data.total.toLocaleString('en-US')}</span> results
          </span>
        )}
      />

      <FilterBar filters={filters} onChange={update} competitions={competitions} sortBy={sortBy} order={order} />

      {error && <div className="py-12 text-center text-sm text-danger">{error}</div>}
      {!data && !error && <TableSkeleton />}
      {data && data.total === 0 && (
        <NoResults
          active={active}
          onClearAll={() => update(EMPTY_FILTERS)}
          onRemoveLast={active.length ? removeLast : undefined}
        />
      )}
      {data && data.total > 0 && (
        <>
          <PlayerTable
            players={data.data}
            columns={columns}
            rankOffset={(page - 1) * PAGE_SIZE}
            onRowClick={openPlayer}
            sortBy={sortBy}
            order={order}
            onSort={handleSort}
            dimmed={loading}
          />
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} shown={data.data.length} onPage={setPage} />
        </>
      )}
      <PlayerModal playerId={modalId} player={modalPlayer ?? undefined} onClose={closeModal} />
    </div>
  )
}

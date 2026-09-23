import { useState, useEffect, useCallback, useRef } from 'react'
import { getPlayers, getPlayerCompetitions, serializeFilters, type Player, type PlayerList, type CompetitionList, type SortOrder } from '../api/players'
import FilterBar, { type Filters } from '../components/FilterBar'
import PlayerTable from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'

const SEARCH_DEBOUNCE_MS = 250

// Wait for a pause in typing so one keystroke does not mean one request.
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

export default function PlayerDetails() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>({
    name: '', position: '', team: '', nationality: '', underpredicted_flag: '', stats_view: '', clauses: [],
  })
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
    getPlayerCompetitions().then(setCompetitions).catch(console.error)
  }, [])

  const openPlayer = (p: Player) =>
    p.sofascore_player_id ? setModalId(p.sofascore_player_id) : setModalPlayer(p)
  const closeModal = () => { setModalId(null); setModalPlayer(null) }

  const load = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50, sort_by: sortBy, order }
      if (debouncedFilters.name) params.name = debouncedFilters.name
      if (debouncedFilters.position) params.position = debouncedFilters.position
      if (debouncedFilters.team) params.team = debouncedFilters.team
      if (debouncedFilters.nationality) params.nationality = debouncedFilters.nationality
      if (debouncedFilters.underpredicted_flag) params.underpredicted_flag = debouncedFilters.underpredicted_flag
      if (debouncedFilters.stats_view && debouncedFilters.stats_view !== 'all') params.stats_view = debouncedFilters.stats_view
      const serialized = serializeFilters(debouncedFilters.clauses)
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
  }, [debouncedFilters, page, sortBy, order])

  const handleSortChange = (field: string) => {
    if (field === sortBy) {
      setOrder((o) => (o === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(field)
      setOrder('desc')
    }
    setPage(1)
  }

  // Hold every request until typing settles, so a page reset cannot fire an unfiltered one first.
  const settling = filters !== debouncedFilters
  useEffect(() => { if (!settling) load() }, [load, settling])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Player details</h1>
      </div>

      <FilterBar
        filters={filters}
        onChange={(f) => { setFilters(f); setPage(1) }}
        competitions={competitions}
      />

      {error && <div className="text-red-400 text-sm py-8 text-center">{error}</div>}
      {!data && !error && <div className="text-gray-400 py-8 text-center">Loading…</div>}
      {data && (
        // Keep the rows on screen while the next search runs, so the table does not blank out.
        <div className={loading ? 'opacity-50 transition-opacity' : 'transition-opacity'}>
          <div className="text-xs text-gray-500 mb-2">
            {data.total} {data.total === 1 ? 'player' : 'players'}
          </div>
          {data.total === 0 ? (
            <div className="text-gray-400 text-sm py-8 text-center">
              No players match this search.
            </div>
          ) : (
            <PlayerTable
              players={data.data}
              total={data.total}
              page={page}
              pageSize={50}
              onPageChange={setPage}
              onPlayerClick={openPlayer}
              sortBy={sortBy}
              order={order}
              onSortChange={handleSortChange}
            />
          )}
        </div>
      )}
      <PlayerModal playerId={modalId} player={modalPlayer ?? undefined} onClose={closeModal} />
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { getPlayers, getPlayerCompetitions, serializeFilters, type Player, type PlayerList, type CompetitionList, type SortOrder } from '../api/players'
import FilterBar, { type Filters } from '../components/FilterBar'
import PlayerTable from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'

export default function Rankings() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>({
    position: '', team: '', nationality: '', underpredicted_flag: '', stats_view: '', clauses: [],
  })
  const [sortBy, setSortBy] = useState('s_final')
  const [order, setOrder] = useState<SortOrder>('desc')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalId, setModalId] = useState<string | null>(null)
  const [modalPlayer, setModalPlayer] = useState<Player | null>(null)
  const [competitions, setCompetitions] = useState<CompetitionList | undefined>(undefined)

  useEffect(() => {
    getPlayerCompetitions().then(setCompetitions).catch(console.error)
  }, [])

  const openPlayer = (p: Player) =>
    p.sofascore_player_id ? setModalId(p.sofascore_player_id) : setModalPlayer(p)
  const closeModal = () => { setModalId(null); setModalPlayer(null) }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50, sort_by: sortBy, order }
      if (filters.position) params.position = filters.position
      if (filters.team) params.team = filters.team
      if (filters.nationality) params.nationality = filters.nationality
      if (filters.underpredicted_flag) params.underpredicted_flag = filters.underpredicted_flag
      if (filters.stats_view && filters.stats_view !== 'all') params.stats_view = filters.stats_view
      const serialized = serializeFilters(filters.clauses)
      if (serialized) params.filters = serialized
      setData(await getPlayers(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [filters, page, sortBy, order])

  const handleSortChange = (field: string) => {
    if (field === sortBy) {
      setOrder((o) => (o === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(field)
      setOrder('desc')
    }
    setPage(1)
  }

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Player Rankings</h1>
      </div>

      <FilterBar
        filters={filters}
        onChange={(f) => { setFilters(f); setPage(1) }}
        competitions={competitions}
      />

      {loading && <div className="text-gray-400 py-8 text-center">Loading…</div>}
      {data && !loading && (
        <>
          <div className="text-xs text-gray-500 mb-2">{data.total} players</div>
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
        </>
      )}
      <PlayerModal playerId={modalId} player={modalPlayer ?? undefined} onClose={closeModal} />
    </div>
  )
}

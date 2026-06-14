import { useState, useEffect, useCallback } from 'react'
import { getPlayers, type Player, type PlayerList } from '../api/players'
import { triggerFetch } from '../api/fetch'
import FilterBar from '../components/FilterBar'
import PlayerTable from '../components/PlayerTable'
import PlayerModal from '../components/PlayerModal'

interface Filters { position: string; team: string; nationality: string; underpredicted_flag: string }

export default function Rankings() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>({ position: '', team: '', nationality: '', underpredicted_flag: '' })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [fetchMsg, setFetchMsg] = useState('')
  const [modalId, setModalId] = useState<string | null>(null)
  const [modalPlayer, setModalPlayer] = useState<Player | null>(null)

  const openPlayer = (p: Player) =>
    p.sofascore_player_id ? setModalId(p.sofascore_player_id) : setModalPlayer(p)
  const closeModal = () => { setModalId(null); setModalPlayer(null) }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50 }
      if (filters.position) params.position = filters.position
      if (filters.team) params.team = filters.team
      if (filters.nationality) params.nationality = filters.nationality
      if (filters.underpredicted_flag) params.underpredicted_flag = filters.underpredicted_flag
      setData(await getPlayers(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => { load() }, [load])

  const handleFetch = async () => {
    setFetchMsg('Fetching… this may take several minutes.')
    try {
      const r = await triggerFetch()
      setFetchMsg(`Done: ${r.season}`)
      load()
    } catch (e) {
      setFetchMsg(`Error: ${e instanceof Error ? e.message : 'Unknown'}`)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Player Rankings</h1>
        <div className="flex items-center gap-3">
          {fetchMsg && <span className="text-sm text-gray-400">{fetchMsg}</span>}
          <button
            onClick={handleFetch}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-sm font-medium"
          >
            Refresh Data
          </button>
        </div>
      </div>

      <FilterBar filters={filters} onChange={(f) => { setFilters(f); setPage(1) }} />

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
          />
        </>
      )}
      <PlayerModal playerId={modalId} player={modalPlayer ?? undefined} onClose={closeModal} />
    </div>
  )
}

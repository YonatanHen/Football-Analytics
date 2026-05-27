import { useState, useEffect, useCallback } from 'react'
import { getPlayers, type PlayerList } from '../api/players'
import { triggerFetch } from '../api/fetch'
import FilterBar from '../components/FilterBar'
import PlayerTable from '../components/PlayerTable'

interface Filters { position: string; team: string; nationality: string; sleeper_flag: string }

export default function Rankings() {
  const [data, setData] = useState<PlayerList | null>(null)
  const [filters, setFilters] = useState<Filters>({ position: '', team: '', nationality: '', sleeper_flag: '' })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [fetchMsg, setFetchMsg] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 50 }
      if (filters.position) params.position = filters.position
      if (filters.team) params.team = filters.team
      if (filters.nationality) params.nationality = filters.nationality
      if (filters.sleeper_flag) params.sleeper_flag = filters.sleeper_flag
      setData(await getPlayers(params))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => { load() }, [load])

  const handleFetch = async () => {
    setFetchMsg('Scraping… this may take several minutes.')
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
            onPlayerClick={() => {}}
          />
        </>
      )}
    </div>
  )
}

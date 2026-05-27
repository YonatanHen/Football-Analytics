import { useState, useEffect } from 'react'
import { getPlayers } from './api/players'
import SeedPrompt from './components/SeedPrompt'
import Rankings from './pages/Rankings'
import PlayerDetail from './pages/PlayerDetail'
import Compare from './pages/Compare'
import Sleepers from './pages/Sleepers'
import ScatterPage from './pages/ScatterPage'

type Tab = 'rankings' | 'detail' | 'compare' | 'sleepers' | 'scatter'

const TABS: { id: Tab; label: string }[] = [
  { id: 'rankings', label: 'Rankings' },
  { id: 'detail', label: 'Player Detail' },
  { id: 'compare', label: 'Compare' },
  { id: 'sleepers', label: 'Sleepers' },
  { id: 'scatter', label: 'Scatter Plot' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('rankings')
  const [isEmpty, setIsEmpty] = useState<boolean | null>(null)
  const [dbError, setDbError] = useState(false)

  useEffect(() => {
    getPlayers({ page_size: 1 })
      .then(r => setIsEmpty(r.total === 0))
      .catch(() => setDbError(true))
  }, [])

  const handleSeeded = () => {
    setTab('rankings')
    setIsEmpty(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="bg-gray-900 border-b border-gray-800 px-4">
        <div className="flex gap-1 max-w-7xl mx-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      <main className="max-w-7xl mx-auto p-4">
        {dbError && (
          <div className="flex items-center justify-center min-h-[60vh] text-red-400 text-sm">
            Cannot reach the backend. Make sure the server is running.
          </div>
        )}
        {!dbError && isEmpty === null && (
          <div className="flex items-center justify-center min-h-[60vh] text-gray-500 text-sm">
            Checking database…
          </div>
        )}
        {!dbError && isEmpty === true && <SeedPrompt onSeeded={handleSeeded} />}
        {!dbError && isEmpty === false && (
          <>
            {tab === 'rankings' && <Rankings />}
            {tab === 'detail' && <PlayerDetail />}
            {tab === 'compare' && <Compare />}
            {tab === 'sleepers' && <Sleepers />}
            {tab === 'scatter' && <ScatterPage />}
          </>
        )}
      </main>
    </div>
  )
}

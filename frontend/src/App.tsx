import { useState, useEffect } from 'react'
import { getPlayers } from './api/players'
import SeedPrompt from './components/SeedPrompt'
import Rankings from './pages/Rankings'
import PlayerDetail from './pages/PlayerDetail'
import Compare from './pages/Compare'
import Sleepers from './pages/Sleepers'
import ScatterPage from './pages/ScatterPage'
import LoadData from './pages/LoadData'

type Tab = 'rankings' | 'detail' | 'compare' | 'sleepers' | 'scatter'

const TABS: { id: Tab; label: string }[] = [
  { id: 'rankings', label: 'Rankings' },
  { id: 'detail', label: 'Player Detail' },
  { id: 'compare', label: 'Compare' },
  { id: 'sleepers', label: 'Underpredicted' },
  { id: 'scatter', label: 'Scatter Plot' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('rankings')
  const [isEmpty, setIsEmpty] = useState<boolean | null>(null)
  const [dbError, setDbError] = useState(false)
  const [showLoad, setShowLoad] = useState(false)

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
        <div className="flex gap-1 max-w-7xl mx-auto items-center">
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
          <div className="ml-auto">
            <button
              onClick={() => setShowLoad(true)}
              className="px-3 py-1 text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              Load Kaggle data
            </button>
          </div>
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

      {showLoad && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setShowLoad(false)}
        >
          <div
            className="bg-gray-900 rounded-xl max-w-lg w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Load Kaggle Dataset</h2>
              <button onClick={() => setShowLoad(false)} className="text-gray-400 hover:text-gray-200">✕</button>
            </div>
            <LoadData />
          </div>
        </div>
      )}
    </div>
  )
}

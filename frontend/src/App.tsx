import { useState, useEffect } from 'react'
import { getPlayers } from './api/players'
import ChatWidget from './components/ChatWidget'
import ChatFullScreen from './pages/ChatFullScreen'
import SeedPrompt from './components/SeedPrompt'
import PlayerDetails from './pages/PlayerDetails'
import Compare from './pages/Compare'
import Sleepers from './pages/Sleepers'
import ScatterPage from './pages/ScatterPage'

type Tab = 'players' | 'compare' | 'sleepers' | 'scatter'

const TABS: { id: Tab; label: string }[] = [
  { id: 'players', label: 'Player details' },
  { id: 'compare', label: 'Compare' },
  { id: 'sleepers', label: 'Underpredicted' },
  { id: 'scatter', label: 'Scatter Plot' },
]

// One query param does not justify adding a router. The chat has no navbar tab by design.
const fullScreenChat = new URLSearchParams(window.location.search).get('chat') === '1'

export default function App() {
  return fullScreenChat ? <ChatFullScreen /> : <Dashboard />
}

function Dashboard() {
  const [tab, setTab] = useState<Tab>('players')
  const [isEmpty, setIsEmpty] = useState<boolean | null>(null)
  const [dbError, setDbError] = useState(false)

  useEffect(() => {
    getPlayers({ page_size: 1 })
      .then(r => setIsEmpty(r.total === 0))
      .catch(() => setDbError(true))
  }, [])

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
        {!dbError && isEmpty === true && <SeedPrompt />}
        {!dbError && isEmpty === false && (
          <>
            {tab === 'players' && <PlayerDetails />}
            {tab === 'compare' && <Compare />}
            {tab === 'sleepers' && <Sleepers />}
            {tab === 'scatter' && <ScatterPage />}
          </>
        )}
      </main>

      {!dbError && isEmpty === false && <ChatWidget />}
    </div>
  )
}

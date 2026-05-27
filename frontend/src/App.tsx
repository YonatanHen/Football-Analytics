import { useState } from 'react'
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
        {tab === 'rankings' && <Rankings />}
        {tab === 'detail' && <PlayerDetail />}
        {tab === 'compare' && <Compare />}
        {tab === 'sleepers' && <Sleepers />}
        {tab === 'scatter' && <ScatterPage />}
      </main>
    </div>
  )
}

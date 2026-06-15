import { useState, type ReactNode } from 'react'
import LoadData from '../pages/LoadData'

export default function SeedPrompt({ onSeeded }: { onSeeded: () => void }) {
  const [showFetcher, setShowFetcher] = useState(false)

  if (showFetcher) return (
    <div className="max-w-2xl mx-auto mt-8">
      <button
        onClick={() => setShowFetcher(false)}
        className="text-sm text-gray-400 hover:text-gray-200 mb-6"
      >
        ← Back
      </button>
      <LoadData onDone={onSeeded} />
    </div>
  )

  return (
    <Center>
      <div className="text-5xl mb-4">⚽</div>
      <h2 className="text-xl font-bold text-gray-100 mb-3">No player data loaded</h2>
      <p className="text-gray-400 text-sm max-w-md text-center mb-8 leading-relaxed">
        Fetch live data from Sofascore to get started.
      </p>
      <button
        onClick={() => setShowFetcher(true)}
        className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-semibold"
      >
        Fetch Live Data
      </button>
    </Center>
  )
}

function Center({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {children}
    </div>
  )
}

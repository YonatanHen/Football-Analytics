import { useState, useRef, type ReactNode } from 'react'
import { triggerFetch, getFetchStatus } from '../api/fetch'
import LoadData from '../pages/LoadData'

const POLL_MS = 3000
type Status = 'idle' | 'loading' | 'done' | 'error'

export default function SeedPrompt({ onSeeded }: { onSeeded: () => void }) {
  const [status, setStatus] = useState<Status>('idle')
  const [count, setCount] = useState(0)
  const [showScraper, setShowScraper] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleKaggle = async () => {
    setStatus('loading')
    try {
      const { job_id } = await triggerFetch({ mode: 'kaggle' })
      pollRef.current = setInterval(async () => {
        try {
          const s = await getFetchStatus(job_id)
          if (s.status !== 'running') {
            clearInterval(pollRef.current!)
            pollRef.current = null
            if (s.status === 'error') {
              setStatus('error')
            } else {
              setCount(s.players_upserted)
              setStatus('done')
              setTimeout(onSeeded, 1500)
            }
          }
        } catch {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setStatus('error')
        }
      }, POLL_MS)
    } catch {
      setStatus('error')
    }
  }

  if (status === 'loading') return (
    <Center>
      <div className="text-5xl mb-4">⏳</div>
      <h2 className="text-xl font-bold text-gray-100 mb-2">Loading season data…</h2>
      <p className="text-gray-400 text-sm mb-1">Fetching and processing player stats. This usually takes 10–30 seconds.</p>
      <p className="text-gray-600 text-xs">Please don't close this tab.</p>
    </Center>
  )

  if (status === 'done') return (
    <Center>
      <div className="text-5xl mb-4">✅</div>
      <h2 className="text-xl font-bold text-gray-100 mb-2">Ready!</h2>
      <p className="text-gray-400 text-sm">{count.toLocaleString()} players loaded. Taking you to Rankings…</p>
    </Center>
  )

  if (status === 'error') return (
    <Center>
      <div className="text-5xl mb-4">⚠️</div>
      <h2 className="text-xl font-bold text-gray-100 mb-2">Something went wrong</h2>
      <p className="text-gray-400 text-sm mb-6">Couldn't load player data. Please try again.</p>
      <button onClick={handleKaggle} className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-semibold">
        Try Again
      </button>
    </Center>
  )

  if (showScraper) return (
    <div className="max-w-2xl mx-auto mt-8">
      <button
        onClick={() => setShowScraper(false)}
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
        Scrape live data from Sofascore, or load the Kaggle demo dataset to explore the app quickly.
      </p>
      <button
        onClick={() => setShowScraper(true)}
        className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-semibold mb-4"
      >
        Scrape Live Data
      </button>
      <button
        onClick={handleKaggle}
        className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        or load Kaggle demo data (2025/26, ~2,800 players)
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

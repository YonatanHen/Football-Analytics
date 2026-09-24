import { useCallback, useEffect, useMemo, useState } from 'react'
import { getMeta, type Meta } from './api/meta'
import { clearSession, getSessionId } from './api/chat'
import AppShell, { type Status } from './components/AppShell'
import ChatPanel from './components/ChatPanel'
import ChatWidget from './components/ChatWidget'
import { BackendUnreachable, EmptyDatabase } from './components/states/SystemStates'
import { AppContext, type GoOptions, type Tab } from './context/AppContext'
import ChatFullScreen from './pages/ChatFullScreen'
import PlayerDetails from './pages/PlayerDetails'
import Compare from './pages/Compare'
import Sleepers from './pages/Sleepers'
import ScatterPage from './pages/ScatterPage'

const RETRY_MS = 10_000

// One query param does not justify adding a router.
const fullScreenChat = new URLSearchParams(window.location.search).get('chat') === '1'

export default function App() {
  return fullScreenChat ? <ChatFullScreen /> : <Dashboard />
}

function Dashboard() {
  const [tab, setTab] = useState<Tab>('players')
  const [season, setSeason] = useState('')
  const [meta, setMeta] = useState<Meta | null>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [tick, setTick] = useState(0)
  const [compareSeed, setCompareSeed] = useState<string | null>(null)
  const [chatKey, setChatKey] = useState(0)

  const retry = useCallback(() => setTick((t) => t + 1), [])
  const clearSeed = useCallback(() => setCompareSeed(null), [])

  useEffect(() => {
    let live = true
    getMeta(season || undefined)
      .then((m) => {
        if (!live) return
        setMeta(m)
        setStatus(m.seasons.length === 0 ? 'empty' : 'ok')
        if (!season && m.seasons.length) setSeason(m.seasons[0])
      })
      .catch(() => live && setStatus('down'))
    return () => { live = false }
  }, [season, tick])

  useEffect(() => {
    if (status !== 'down') return
    const t = setInterval(retry, RETRY_MS)
    return () => clearInterval(t)
  }, [status, retry])

  const go = useCallback((next: Tab, opts?: GoOptions) => {
    if (opts?.comparePlayerId) setCompareSeed(opts.comparePlayerId)
    setTab(next)
  }, [])

  const newChat = async () => {
    try { await clearSession(getSessionId()) } catch { /* the TTL removes the thread later */ }
    setChatKey((k) => k + 1)
  }

  const ctx = useMemo(() => ({ season, meta, go }), [season, meta, go])
  const ready = status === 'ok' && season !== ''

  return (
    <AppContext.Provider value={ctx}>
      <AppShell
        tab={tab}
        onTab={setTab}
        status={status}
        meta={meta}
        season={season}
        onSeason={setSeason}
        onNewChat={newChat}
      >
        {status === 'down' && <BackendUnreachable onRetry={retry} />}
        {status === 'empty' && <EmptyDatabase onRetry={retry} />}
        {ready && (
          <>
            {tab === 'players' && <PlayerDetails key={season} />}
            {tab === 'compare' && (
              <Compare key={season} seedId={compareSeed} onSeedUsed={clearSeed} />
            )}
            {tab === 'sleepers' && <Sleepers key={season} />}
            {tab === 'scatter' && <ScatterPage key={season} />}
            {tab === 'chat' && (
              <div className="mx-auto flex h-[calc(100vh-7.5rem)] max-w-[900px] flex-col">
                <ChatPanel key={chatKey} fullScreen />
              </div>
            )}
          </>
        )}
      </AppShell>
      {ready && tab !== 'chat' && <ChatWidget key={chatKey} />}
    </AppContext.Provider>
  )
}

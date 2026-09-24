import { ArrowLeft } from 'lucide-react'
import ChatPanel from '../components/ChatPanel'
import { AppContext } from '../context/AppContext'

// Standalone page: "Open in Player details" leaves for the dashboard.
const ctx = { season: '', meta: null, go: () => { window.location.href = '/' } }

export default function ChatFullScreen() {
  return (
    <AppContext.Provider value={ctx}>
      <div className="flex min-h-screen justify-center bg-bg">
        <div className="flex h-screen w-full max-w-[900px] flex-col px-6 py-6">
          <a href="/" className="mb-5 inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent">
            <ArrowLeft size={13} /> Back to dashboard
          </a>
          <ChatPanel fullScreen />
        </div>
      </div>
    </AppContext.Provider>
  )
}

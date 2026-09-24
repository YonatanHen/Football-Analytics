import { useState } from 'react'
import { ArrowUpRight, MessageSquare, X } from 'lucide-react'
import ChatPanel from './ChatPanel'

export default function ChatWidget() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="Open chat"
        className="fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-bg shadow-lg shadow-black/40 transition hover:brightness-110"
      >
        <MessageSquare size={20} />
      </button>
    )
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex h-[560px] max-h-[calc(100vh-2.5rem)] w-[400px] max-w-[calc(100vw-2.5rem)] flex-col rounded-xl border border-line-strong bg-header p-4 shadow-2xl shadow-black/50">
      <div className="mb-3 flex items-center gap-3">
        <h2 className="text-sm font-semibold">Ask AI</h2>
        <a href="?chat=1" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-muted hover:text-accent">
          Open full screen <ArrowUpRight size={12} />
        </a>
        <button onClick={() => setOpen(false)} aria-label="Close chat" className="ml-auto text-muted hover:text-ink">
          <X size={16} />
        </button>
      </div>
      <ChatPanel />
    </div>
  )
}

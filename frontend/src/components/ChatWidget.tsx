import { useState } from 'react'
import ChatPanel from './ChatPanel'

const INSTRUCTIONS =
  'Ask about any player or metric in the database. I can rank, filter and compare.'

export default function ChatWidget() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="Open chat"
        className="fixed bottom-4 right-4 z-50 w-14 h-14 rounded-full bg-indigo-600 hover:bg-indigo-500 text-2xl shadow-lg"
      >
        💬
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[380px] h-[540px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)] flex flex-col bg-gray-900 border border-gray-800 rounded-xl shadow-2xl p-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-100">Ask the data</h2>
        <button
          onClick={() => setOpen(false)}
          aria-label="Close chat"
          className="text-gray-400 hover:text-gray-200 text-sm"
        >
          ✕
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-1 leading-relaxed">{INSTRUCTIONS}</p>

      <a
        href="?chat=1"
        target="_blank"
        rel="noreferrer"
        className="self-start mt-1 mb-2 text-xs text-indigo-400 hover:text-indigo-300"
      >
        Open full screen ↗
      </a>

      <ChatPanel />
    </div>
  )
}

import { useEffect, useRef, useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clearSession, getSession, getSessionId, sendChat, type ChatTurn } from '../api/chat'

interface Turn extends ChatTurn {
  degraded?: boolean
}

const NETWORK_ERROR = 'Could not reach the server. Please try again.'

export default function ChatPanel({ fullScreen = false }: { fullScreen?: boolean }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getSession(getSessionId())
      .then(setTurns)
      .catch(() => {})
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, sending])

  async function send(e: FormEvent) {
    e.preventDefault()
    const message = draft.trim()
    if (!message || sending) return
    setDraft('')
    setTurns((prev) => [...prev, { role: 'user', content: message }])
    setSending(true)
    try {
      const res = await sendChat(message, getSessionId())
      setTurns((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, degraded: res.degraded },
      ])
    } catch {
      // The backend answers 200 even when it fails, so this is a network error only.
      setTurns((prev) => [...prev, { role: 'assistant', content: NETWORK_ERROR }])
    } finally {
      setSending(false)
    }
  }

  async function startNewChat() {
    setTurns([])
    try {
      await clearSession(getSessionId())
    } catch {
      // The thread stays on the server; the user still gets a clean view.
    }
  }

  return (
    <div className={`flex flex-col min-h-0 ${fullScreen ? 'flex-1' : 'h-full'}`}>
      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1">
        {turns.length === 0 && !sending && (
          <p className="text-gray-500 text-sm">
            No messages yet. Try “Who are the top 5 scorers?”
          </p>
        )}
        {turns.map((turn, i) => (
          <Bubble key={i} turn={turn} />
        ))}
        {sending && <p className="text-gray-500 text-sm">Thinking…</p>}
        <div ref={bottom} />
      </div>

      <form onSubmit={send} className="flex gap-2 pt-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about a player or a metric..."
          maxLength={2000}
          aria-label="Your question"
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={sending || draft.trim() === ''}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 rounded px-3 py-2 text-sm font-medium"
        >
          Send
        </button>
      </form>

      <button
        onClick={startNewChat}
        className="self-start pt-2 text-xs text-gray-500 hover:text-gray-300"
      >
        New chat
      </button>
    </div>
  )
}

function Bubble({ turn }: { turn: Turn }) {
  const mine = turn.role === 'user'
  return (
    <div className={mine ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
          mine ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-100'
        }`}
      >
        {mine ? (
          <span className="whitespace-pre-wrap">{turn.content}</span>
        ) : (
          <Answer text={turn.content} />
        )}
        {turn.degraded && (
          <div className="mt-1 text-xs text-amber-400/80">Not verified against the app's data.</div>
        )}
      </div>
    </div>
  )
}

// Answers come back as markdown. react-markdown escapes HTML, so no raw html is rendered.
const MARKDOWN_STYLES = [
  '[&_p]:mb-2 [&_p:last-child]:mb-0',
  '[&_ol]:list-decimal [&_ul]:list-disc [&_ol]:pl-5 [&_ul]:pl-5 [&_li]:mb-1',
  '[&_strong]:font-semibold [&_code]:text-xs [&_code]:bg-black/30 [&_code]:px-1 [&_code]:rounded',
  '[&_table]:w-full [&_th]:text-left [&_th]:pr-3 [&_td]:pr-3 [&_a]:underline',
].join(' ')

function Answer({ text }: { text: string }) {
  return (
    <div className={MARKDOWN_STYLES}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {text}
      </Markdown>
    </div>
  )
}

import { useEffect, useRef, useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Check, Copy, ExternalLink, Sparkles, TriangleAlert } from 'lucide-react'
import { getSession, getSessionId, sendChat, type ChatTurn, type ToolCall } from '../api/chat'
import { useApp } from '../context/AppContext'

interface Turn extends ChatTurn {
  degraded?: boolean
  tool_calls?: ToolCall[]
  uncited?: string[]
}

const NETWORK_ERROR = 'Could not reach the server. Please try again.'
const MAX_CHARS = 2000
const SUGGESTIONS = [
  'Top 5 scorers this season',
  'Best value midfielders',
  'Compare Saka and Palmer',
  'Who is regressing?',
]

export default function ChatPanel({ fullScreen = false }: { fullScreen?: boolean }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getSession(getSessionId())
      // Keep whatever the user sent while this was still loading.
      .then((stored) => setTurns((current) => (current.length ? current : stored)))
      .catch(() => {})
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, sending])

  async function ask(text: string) {
    const message = text.trim()
    if (!message || sending) return
    setDraft('')
    setTurns((prev) => [...prev, { role: 'user', content: message }])
    setSending(true)
    try {
      const res = await sendChat(message, getSessionId())
      setTurns((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, degraded: res.degraded, tool_calls: res.tool_calls, uncited: res.uncited },
      ])
    } catch {
      // The backend answers 200 even when it fails, so this is a network error only.
      setTurns((prev) => [...prev, { role: 'assistant', content: NETWORK_ERROR }])
    } finally {
      setSending(false)
    }
  }

  const submit = (e: FormEvent) => { e.preventDefault(); ask(draft) }
  const pad = fullScreen ? 'space-y-7' : 'space-y-4'

  return (
    <div className="flex h-full min-h-0 flex-col">
      {fullScreen && (
        <div className="mb-6">
          <h1 className="text-[22px] font-semibold tracking-tight">Ask AI</h1>
          <p className="mt-1.5 font-mono text-[11px] text-muted">
            Answers are assembled from live database queries. Anything the data cannot support is labelled.
          </p>
        </div>
      )}

      <div className={`min-h-0 flex-1 overflow-y-auto pr-1 ${pad}`}>
        {turns.length === 0 && !sending && (
          <p className="pt-2 text-sm text-muted">Ask about any player or metric in the database. I can rank, filter and compare.</p>
        )}
        {turns.map((turn, i) =>
          turn.role === 'user'
            ? <UserBubble key={i} text={turn.content} compact={!fullScreen} />
            : <AssistantMessage key={i} turn={turn} compact={!fullScreen} />,
        )}
        {sending && (
          <div className="flex items-center gap-4">
            <AiIcon />
            <span className="flex gap-1">
              {[0, 150, 300].map((d) => (
                <span key={d} className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted" style={{ animationDelay: `${d}ms` }} />
              ))}
            </span>
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="pt-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              disabled={sending}
              className={`rounded-full border border-line-strong bg-surface text-muted transition-colors hover:text-ink disabled:opacity-40 ${
                fullScreen ? 'px-4 py-2 text-sm' : 'px-3 py-1 text-xs'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="flex items-center gap-3 rounded-lg border border-line-strong bg-surface p-1.5 pl-4 focus-within:border-accent-deep">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about a player, a metric, or a comparison..."
            maxLength={MAX_CHARS}
            aria-label="Your question"
            className={`min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-dim ${fullScreen ? 'text-[15px]' : 'text-sm'}`}
          />
          {fullScreen && <span className="font-mono text-[10px] text-dim">{draft.length} / {MAX_CHARS}</span>}
          <button type="submit" disabled={sending || draft.trim() === ''} className={`btn-solid ${fullScreen ? 'h-10 px-5 text-[15px]' : 'h-8 px-3'}`}>
            Send <ArrowUp size={15} />
          </button>
        </form>
        {fullScreen && (
          <p className="mt-3 font-mono text-[10px] text-dim">Session history is kept for 7 days after the last message.</p>
        )}
      </div>
    </div>
  )
}

function AiIcon() {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
      <Sparkles size={16} />
    </span>
  )
}

function UserBubble({ text, compact }: { text: string; compact: boolean }) {
  return (
    <div className="flex justify-end">
      <div className={`max-w-[75%] whitespace-pre-wrap rounded-lg bg-accent-deep text-white ${compact ? 'px-3 py-2 text-sm' : 'px-5 py-3 text-[15px] leading-relaxed'}`}>
        {text}
      </div>
    </div>
  )
}

function AssistantMessage({ turn, compact }: { turn: Turn; compact: boolean }) {
  const { go } = useApp()
  const [copied, setCopied] = useState(false)
  const calls = turn.tool_calls ?? []
  const rows = calls.reduce((n, c) => n + c.rows, 0)
  const uncited = turn.uncited ?? []

  const copy = () => {
    navigator.clipboard?.writeText(turn.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }

  return (
    <div className="flex gap-4">
      {!compact && <AiIcon />}
      <div className="min-w-0 flex-1">
        {calls.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2 font-mono text-[10px] text-dim">
            <span className="tracking-[0.16em]">RAN</span>
            {calls.map((c, i) => (
              <span key={i} className="rounded border border-line-strong bg-surface px-2 py-1 text-ink/80">{c.name}()</span>
            ))}
            <span>→ {rows} rows</span>
          </div>
        )}
        <Answer text={turn.content} compact={compact} />
        {turn.degraded && (
          <div className="mt-4 flex items-start gap-2.5 rounded-md bg-warn-soft px-4 py-3 text-[13px] text-warn">
            <TriangleAlert size={15} className="mt-0.5 shrink-0" />
            <span>
              {uncited.length > 0
                ? `${uncited.length === 1 ? 'One figure' : `${uncited.length} figures`} in this answer — ${uncited.join(', ')} — could not be matched to a stored row and may come from the model's own knowledge.`
                : "This answer is not backed by the app's data."}
            </span>
          </div>
        )}
        {!compact && (
          <div className="mt-4 flex gap-2">
            <button onClick={copy} className="btn-ghost h-8 text-muted hover:text-ink">
              {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}
            </button>
            <button onClick={() => go('players')} className="btn-ghost h-8 text-muted hover:text-ink">
              <ExternalLink size={13} /> Open in Player details
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Ratio cells ("1.77×") are the xRatio column; they get the amber signal color.
const RATIO_CELL = /^\d+(\.\d+)?\s*[×x]$/

// Answers come back as markdown. react-markdown escapes HTML, so no raw html is rendered.
function Answer({ text, compact }: { text: string; compact: boolean }) {
  return (
    <div className={`${compact ? 'text-sm' : 'text-[15px]'} leading-relaxed text-ink [&_li]:mb-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_p:last-child]:mb-0 [&_p]:mb-3 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a {...props} target="_blank" rel="noreferrer" className="text-accent underline" />,
          code: (props) => <code {...props} className="rounded bg-surface-2 px-1 font-mono text-[0.85em]" />,
          table: (props) => (
            <div className="my-4 overflow-x-auto rounded-lg bg-surface">
              <table {...props} className="w-full text-left text-sm" />
            </div>
          ),
          th: (props) => (
            <th {...props} className="bg-surface-2/60 px-4 py-2.5 font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-dim" />
          ),
          td: ({ children, ...props }) => {
            const ratio = typeof children === 'string' && RATIO_CELL.test(children.trim())
            const numeric = typeof children === 'string' && /^[\d.,+-]+$/.test(children.trim())
            return (
              <td
                {...props}
                className={`border-t border-line px-4 py-2.5 ${ratio ? 'font-mono text-warn' : numeric ? 'font-mono text-ink/80' : ''}`}
              >
                {children}
              </td>
            )
          },
        }}
      >
        {text}
      </Markdown>
    </div>
  )
}

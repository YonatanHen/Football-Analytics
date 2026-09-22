import { apiFetch } from './client'

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  answer: string
  session_id: string
  degraded: boolean
}

const SESSION_KEY = 'fa.chat.session_id'
let memorySessionId: string | null = null

function newId(): string {
  // randomUUID exists only in secure contexts (https or localhost).
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
    b.toString(16).padStart(2, '0'),
  ).join('')
}

/** The browser's chat session id, created once and kept across reloads. */
export function getSessionId(): string {
  try {
    let id = localStorage.getItem(SESSION_KEY)
    if (!id) {
      id = newId()
      localStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    // Storage blocked (e.g. private mode): keep the session for this page load only.
    memorySessionId ??= newId()
    return memorySessionId
  }
}

const sessionPath = (sessionId: string) => `/v1/chat/sessions/${encodeURIComponent(sessionId)}`

export function sendChat(message: string, sessionId: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message }),
  })
}

export async function getSession(sessionId: string): Promise<ChatTurn[]> {
  const res = await apiFetch<{ turns: ChatTurn[] }>(sessionPath(sessionId))
  return res.turns
}

export function clearSession(sessionId: string): Promise<void> {
  return apiFetch<void>(sessionPath(sessionId), { method: 'DELETE' })
}

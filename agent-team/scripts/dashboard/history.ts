import { cleanRow, cleanThreadId } from './api.ts'
import type { Session, SnapshotRow, TeamRole } from './api.ts'

export type HistoryEntry = { ticket: string; session: Session } | { role: TeamRole; session: Session }
export type History = { sessions: Record<string, HistoryEntry> }

const MAX_SESSIONS = 500
const MAX_TEAM_SESSIONS = 50
const TICKET = /^[A-Za-z][A-Za-z0-9]*-\d+$/
const ROLES = ['ranking', 'hygiene']

const isTicketEntry = (e: HistoryEntry): e is { ticket: string; session: Session } => 'ticket' in e

/** Keeps the newest 500 ticket sessions (a ticket helper's session is one) and, apart from them, the newest 50 project manager sessions. */
const build = (entries: [string, HistoryEntry][]): History => {
  const newest = (list: [string, HistoryEntry][], max: number) => [...list].sort((a, b) => b[1].session.updatedAt - a[1].session.updatedAt).slice(0, max)
  const kept = [...newest(entries.filter(([, e]) => isTicketEntry(e)), MAX_SESSIONS), ...newest(entries.filter(([, e]) => !isTicketEntry(e)), MAX_TEAM_SESSIONS)]
  return { sessions: Object.fromEntries(newest(kept, kept.length)) }
}

/** Reads the history file. Bad JSON gives an empty history; bad entries are dropped; rows get the cleaning a live snapshot gets. */
export function parseHistory(text: string): History {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    return build([])
  }
  const sessions = (data as { sessions?: unknown } | null)?.sessions
  if (typeof sessions !== 'object' || sessions === null || Array.isArray(sessions)) return build([])
  const out: [string, HistoryEntry][] = []
  for (const [id, e] of Object.entries(sessions)) {
    if (typeof e !== 'object' || e === null) continue
    const { ticket, role, session: s } = e as { ticket?: unknown; role?: unknown; session?: Record<string, unknown> | null }
    const isTicket = typeof ticket === 'string' && TICKET.test(ticket)
    if (!isTicket && !(ticket === undefined && typeof role === 'string' && ROLES.includes(role))) continue
    if (typeof s !== 'object' || s === null) continue
    const { sessionId, cwd, updatedAt, total, pricing, rows, threadId } = s
    if (sessionId !== id || typeof cwd !== 'string' || typeof updatedAt !== 'number' || !Number.isFinite(updatedAt) || updatedAt < 0 || !Array.isArray(rows)) continue
    const cleaned = rows.map((r) => cleanRow(r, null)).filter((r): r is SnapshotRow => r !== null)
    const session: Session = { sessionId: id, cwd, updatedAt, stale: false, total: typeof total === 'number' && Number.isFinite(total) ? total : null, pricing: typeof pricing === 'number' && Number.isFinite(pricing) ? pricing : null, rows: cleaned }
    const thread = cleanThreadId(threadId)
    if (thread) session.threadId = thread
    out.push([id, isTicket ? { ticket: ticket as string, session } : { role: role as TeamRole, session }])
  }
  return build(out)
}

/** Adds entries. A session replaces its own entry when its snapshot is newer or equal. */
function record(history: History, add: HistoryEntry[]): History {
  const map = new Map(Object.entries(history.sessions))
  for (const entry of add) {
    const { session } = entry
    if (!session.sessionId || (map.get(session.sessionId)?.session.updatedAt ?? -Infinity) > session.updatedAt) continue
    map.set(session.sessionId, entry)
  }
  return build([...map])
}

/** Adds the sessions matched to tickets. The newest 500 ticket sessions stay. */
export const recordHistory = (history: History, matched: { ticket: string; session: Session }[]): History => record(history, matched)

/** Adds the project manager sessions. The newest 50 stay, apart from the ticket sessions. */
export const recordTeamHistory = (history: History, matched: { role: TeamRole; session: Session }[]): History => record(history, matched)

const finish = (s: Session): Session => {
  const at = s.updatedAt
  const rows = s.rows.map((r) => ({ ...r, end: r.end ?? at, segments: r.segments.map(([a, b]): [number, number | null] => [a, b ?? Math.max(a, at)]) }))
  return { ...s, stale: false, rows }
}

/** Each ticket's sessions, ticket helper sessions included, oldest update first, all shown as finished so no bar is drawn running. */
export function historyByTicket(history: History): Record<string, Session[]> {
  const out = new Map<string, Session[]>()
  for (const entry of Object.values(history.sessions)) if (isTicketEntry(entry)) out.set(entry.ticket, [...(out.get(entry.ticket) ?? []), finish(entry.session)])
  for (const list of out.values()) list.sort((a, b) => a.updatedAt - b.updatedAt)
  return Object.fromEntries(out)
}

/** The project manager sessions, all shown as finished. */
export function teamHistory(history: History): { role: TeamRole; session: Session }[] {
  return Object.values(history.sessions).flatMap((e) => (isTicketEntry(e) ? [] : [{ role: e.role, session: finish(e.session) }]))
}

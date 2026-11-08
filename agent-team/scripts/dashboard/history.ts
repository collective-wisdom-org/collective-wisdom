import { cleanRow } from './api.ts'
import type { Session, SnapshotRow } from './api.ts'

export type HistoryEntry = { ticket: string; session: Session }
export type History = { sessions: Record<string, HistoryEntry> }

const MAX_SESSIONS = 500
const TICKET = /^[A-Za-z][A-Za-z0-9]*-\d+$/

const build = (entries: [string, HistoryEntry][]): History => ({ sessions: Object.fromEntries(entries) })

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
    const { ticket, session: s } = e as { ticket?: unknown; session?: Record<string, unknown> | null }
    if (typeof ticket !== 'string' || !TICKET.test(ticket) || typeof s !== 'object' || s === null) continue
    const { sessionId, cwd, updatedAt, total, rows } = s
    if (sessionId !== id || typeof cwd !== 'string' || typeof updatedAt !== 'number' || !Number.isFinite(updatedAt) || updatedAt < 0 || !Array.isArray(rows)) continue
    const cleaned = rows.map((r) => cleanRow(r, null)).filter((r): r is SnapshotRow => r !== null)
    out.push([id, { ticket, session: { sessionId: id, cwd, updatedAt, stale: false, total: typeof total === 'number' && Number.isFinite(total) ? total : null, rows: cleaned } }])
  }
  return build(out)
}

/** Adds the sessions matched to tickets. A session replaces its own entry when its snapshot is newer or equal; the newest 500 stay. */
export function recordHistory(history: History, matched: { ticket: string; session: Session }[]): History {
  const map = new Map(Object.entries(history.sessions))
  for (const { ticket, session } of matched) {
    if (!session.sessionId || (map.get(session.sessionId)?.session.updatedAt ?? -Infinity) > session.updatedAt) continue
    map.set(session.sessionId, { ticket, session })
  }
  return build([...map].sort((a, b) => b[1].session.updatedAt - a[1].session.updatedAt).slice(0, MAX_SESSIONS))
}

const finish = (s: Session): Session => {
  const at = s.updatedAt
  const rows = s.rows.map((r) => ({ ...r, end: r.end ?? at, segments: r.segments.map(([a, b]): [number, number | null] => [a, b ?? Math.max(a, at)]) }))
  return { ...s, stale: false, rows }
}

/** Each ticket's sessions, oldest update first, all shown as finished so no bar is drawn running. */
export function historyByTicket(history: History): Record<string, Session[]> {
  const out: Record<string, Session[]> = {}
  for (const { ticket, session } of Object.values(history.sessions)) (out[ticket] ??= []).push(finish(session))
  for (const list of Object.values(out)) list.sort((a, b) => a.updatedAt - b.updatedAt)
  return out
}

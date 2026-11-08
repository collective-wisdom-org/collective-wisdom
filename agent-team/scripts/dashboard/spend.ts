import type { Session } from './api.ts'

export type SpendEntry = { ticket: string; cost: number | null; tokens: number; updatedAt: number }
export type Ledger = { sessions: Record<string, SpendEntry> }
export type Spend = { cost: number | null; tokens: number }

const MAX_SESSIONS = 2000
const TICKET = /^[A-Za-z][A-Za-z0-9]*-\d+$/

const nonNeg = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x) && x >= 0
const build = (entries: [string, SpendEntry][]): Ledger => ({ sessions: Object.fromEntries(entries) })

/** Reads the ledger file. Bad JSON gives an empty ledger; bad entries are dropped. */
export function parseLedger(text: string): Ledger {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    return build([])
  }
  const sessions = (data as { sessions?: unknown } | null)?.sessions
  if (typeof sessions !== 'object' || sessions === null || Array.isArray(sessions)) return build([])
  const out: [string, SpendEntry][] = []
  for (const [id, e] of Object.entries(sessions)) {
    if (typeof e !== 'object' || e === null) continue
    const { ticket, cost, tokens, updatedAt } = e as Record<string, unknown>
    if (typeof ticket !== 'string' || !TICKET.test(ticket) || !nonNeg(tokens) || !nonNeg(updatedAt)) continue
    if (cost !== null && !nonNeg(cost)) continue
    out.push([id, { ticket, cost: cost as number | null, tokens, updatedAt }])
  }
  return build(out)
}

/** Adds the sessions matched to tickets. A session replaces its own entry when its snapshot is newer or equal; the newest 2000 stay. */
export function recordSpend(ledger: Ledger, matched: { ticket: string; session: Session }[]): Ledger {
  const map = new Map(Object.entries(ledger.sessions))
  for (const { ticket, session: s } of matched) {
    if (!s.sessionId || (map.get(s.sessionId)?.updatedAt ?? -Infinity) > s.updatedAt) continue
    // Main's work is the session row in older snapshots (its task rows repeat it), else the task rows.
    const mainKind = s.rows.some((r) => r.kind === 'session') ? 'session' : 'task'
    const tokens = s.rows.reduce((n, r) => (r.kind === mainKind || r.kind === 'agent' ? n + r.tokens : n), 0)
    map.set(s.sessionId, { ticket, cost: s.total, tokens, updatedAt: s.updatedAt })
  }
  return build([...map].sort((a, b) => b[1].updatedAt - a[1].updatedAt).slice(0, MAX_SESSIONS))
}

/** Each ticket's total over its sessions. The cost is null only when no session has one. */
export function spendByTicket(ledger: Ledger): Record<string, Spend> {
  const out = new Map<string, Spend>()
  for (const e of Object.values(ledger.sessions)) {
    const t = out.get(e.ticket) ?? { cost: null, tokens: 0 }
    t.tokens += e.tokens
    if (e.cost !== null) t.cost = (t.cost ?? 0) + e.cost
    out.set(e.ticket, t)
  }
  return Object.fromEntries(out)
}

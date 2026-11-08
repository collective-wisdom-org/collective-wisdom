import { groupTickets } from '../../.claude/mods/status-pane/hooks/groups.ts'
import type { MergedEntry } from './merged.ts'
import { specUrlOf } from './details.ts'
import type { Detail, Found } from './details.ts'
import { isWorktree } from '../../../mods/agent-gantt/hooks/rows.ts'

export type SnapshotRow = { id: string; depth: number; name: string; repo: string; start: number; end: number | null; tokens: number; cost: number | null; kind: 'session' | 'task' | 'agent'; segments: [number, number | null][]; model: string | null; harness: string | null }
export type Snapshot = { sessionId: string; cwd: string; updatedAt: number; total: number | null; pricing: number | null; rows: SnapshotRow[] }
export type Session = { sessionId: string; cwd: string; updatedAt: number; stale: boolean; total: number | null; pricing: number | null; rows: SnapshotRow[]; threadId?: string | null; heading?: string | null }
export type TeamRole = 'ranking' | 'hygiene'
type TeamState = 'running' | 'idle' | 'paused'
type PmRow = { sessionId: string; role: TeamRole; state: 'running' | 'finished'; threadLink?: string; gantt: Session[] }
type StatusRow = { id: string; title: string; risk: string; next: string; stage: string; issueUrl?: string; prUrl?: string; specUrl?: string; threadLink?: string; gantt?: Session[]; detail?: Detail }
export type Worktree = { path: string; branch: string }
export type Api = {
  generatedAt: number
  status: { name: string; count: number; rows: StatusRow[] }[]
  merged: MergedEntry[]
  chief: { state: TeamState; threadLink?: string; gantt?: Session[] }
  pm: PmRow[]
}
type Repo = { url: string; isGithubIssues: boolean }

const DAY = 24 * 3600 * 1000
const STALE_MS = 30_000
const NAME_MAX = 60
const LABEL_MAX = 40
const SEGMENTS_MAX = 500
const KINDS = ['session', 'task', 'agent']
const RUNNING_MS = 60_000
const THREAD_MAX = 200
const HEADING_MAX = 40
const HEADINGS: Record<string, TeamRole> = { 'BACKLOG RANKING': 'ranking', 'PROJECT MANAGER HYGIENE': 'hygiene' }

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)
const str = (x: unknown): string => (typeof x === 'string' ? x : '')
const num = (x: unknown): number => (typeof x === 'number' && Number.isFinite(x) ? x : 0)
const numOrNull = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null)

function trackerIsGithub(markdown: string): boolean {
  for (const line of markdown.split(/\r?\n/)) {
    if (!line.trimStart().startsWith('|')) continue
    const cells = line.split('|').map((c) => c.trim())
    const [, name, value] = cells
    if (name !== 'Tracker' && !name?.startsWith('Tracker (')) continue
    return value?.match(/`([^`]+)`/)?.[1].toLowerCase() === 'github'
  }
  return false
}

export function repoUrlFromProject(markdown: string): Repo | null {
  const m = markdown.match(/^\|\s*Repo\b[^|]*\|[^|]*<(https?:\/\/[^>\s]+)>/m)
  if (!m) return null
  return { url: m[1].replace(/\/+$/, ''), isGithubIssues: trackerIsGithub(markdown) }
}

/** Parses `git worktree list --porcelain`; detached worktrees have no branch line and are skipped. */
export function parseWorktrees(text: string): Worktree[] {
  const out: Worktree[] = []
  for (const block of text.split(/\r?\n\r?\n/)) {
    const path = block.match(/^worktree (.+)$/m)?.[1]
    const branch = block.match(/^branch refs\/heads\/(.+)$/m)?.[1]
    if (path && branch) out.push({ path, branch })
  }
  return out
}

const label = (x: unknown): string | null => (typeof x === 'string' ? x.slice(0, LABEL_MAX) : null)

/** The last SEGMENTS_MAX valid [start, end] pairs, oldest first. */
function cleanSegments(x: unknown): [number, number | null][] {
  if (!Array.isArray(x)) return []
  const out: [number, number | null][] = []
  for (const p of x.slice(-SEGMENTS_MAX)) {
    if (!Array.isArray(p)) continue
    const [a, b] = p
    const start = numOrNull(a)
    const end = b === null ? null : numOrNull(b)
    if (start !== null && (b === null || (end !== null && end >= start))) out.push([start, end])
  }
  return out.sort((p, q) => p[0] - q[0])
}

export function cleanRow(r: unknown, endFill: number | null): SnapshotRow | null {
  if (!isObj(r)) return null
  const end = numOrNull(r.end)
  const start = num(r.start)
  const segments = cleanSegments(r.segments)
  return {
    id: str(r.id),
    depth: num(r.depth),
    name: str(r.name).slice(0, NAME_MAX),
    repo: str(r.repo),
    start,
    end: end === null ? endFill : end,
    tokens: num(r.tokens),
    cost: numOrNull(r.cost),
    kind: KINDS.includes(r.kind as string) ? (r.kind as SnapshotRow['kind']) : 'agent',
    segments: segments.length ? segments : [[start, end === null ? endFill : end]],
    model: label(r.model),
    harness: label(r.harness),
  }
}

/** A thread id safe to put in a `t3-thread://` link, else null. */
export function cleanThreadId(x: unknown): string | null {
  return typeof x === 'string' && x.length <= THREAD_MAX && /^[A-Za-z0-9:%._-]+$/.test(x) ? x : null
}

/** Cleans a snapshot whose cwd passes `keep`. `open` is true when a turn of the main loop is in progress: its `main` row or one of its `main:task:N` rows has an open last segment, which the closing rules below would hide. */
function cleanWith(s: unknown, now: number, keep: (cwd: string) => boolean): { session: Session; open: boolean } | null {
  if (!isObj(s) || !Array.isArray(s.rows) || !keep(str(s.cwd))) return null
  const updatedAt = numOrNull(s.updatedAt)
  if (updatedAt === null || now - updatedAt > DAY) return null
  const cleaned = s.rows.map((r) => cleanRow(r, null)).filter((r): r is SnapshotRow => r !== null)
  const open = cleaned.some((r) => /^main(:task:\d+)?$/.test(r.id) && r.segments.at(-1)?.[1] === null)
  // The main row and its task rows never end while the session lives, so only the other agents say whether it is stale.
  const working = cleaned.some((r) => r.kind === 'agent' && r.id !== 'main' && r.end === null)
  const stale = now - updatedAt > STALE_MS && working
  const close = (r: SnapshotRow): SnapshotRow => ({ ...r, end: updatedAt, segments: r.segments.map(([a, b]) => [a, b === null ? Math.max(a, updatedAt) : b]) })
  const rows = cleaned.map((r) => (r.end === null && (stale || (!working && (r.id === 'main' || r.kind === 'task'))) ? close(r) : r))
  return { session: { sessionId: str(s.sessionId), cwd: str(s.cwd), updatedAt, stale, total: numOrNull(s.total), pricing: numOrNull(s.pricing), rows }, open }
}

export const cleanSnapshot = (s: unknown, now: number): Session | null => cleanWith(s, now, isWorktree)?.session ?? null

/** Like cleanSnapshot, but for a session outside any worktree (the root checkout), with its thread id and heading. */
export function cleanTeamSnapshot(s: unknown, now: number): { session: Session; open: boolean } | null {
  const got = cleanWith(s, now, (cwd) => !isWorktree(cwd))
  if (!got || !isObj(s)) return null
  const heading = typeof s.heading === 'string' && s.heading.length <= HEADING_MAX ? s.heading : null
  return { open: got.open, session: { ...got.session, threadId: cleanThreadId(s.threadId), heading } }
}

/** The chief of staff, a project manager child, or null for any other session. The chief is matched by state first, then the heading. */
export function teamRole(session: Session, state: unknown): 'chief' | TeamRole | null {
  const st = isObj(state) ? state : {}
  if ((typeof st.chiefSessionId === 'string' && st.chiefSessionId && session.sessionId === st.chiefSessionId) || (typeof st.chiefThreadId === 'string' && st.chiefThreadId && session.threadId === st.chiefThreadId)) return 'chief'
  return Object.hasOwn(HEADINGS, session.heading ?? '') ? HEADINGS[session.heading!] : null
}

type TeamItem = { role: 'chief' | TeamRole; session: Session; open: boolean }

function teamItems(snapshots: unknown[], state: unknown, now: number): TeamItem[] {
  const out: TeamItem[] = []
  for (const raw of snapshots) {
    const got = cleanTeamSnapshot(raw, now)
    const role = got && teamRole(got.session, state)
    if (got && role) out.push({ role, ...got })
  }
  return out
}

/** The project manager sessions among the snapshots, for the history. */
export function teamSessions(input: { snapshots: unknown[]; state: unknown; now: number }): { role: TeamRole; session: Session }[] {
  return teamItems(input.snapshots, input.state, input.now).flatMap((i) => (i.role === 'chief' ? [] : [{ role: i.role, session: i.session }]))
}

/** The ticket a snapshot belongs to: its worktree's branch, matched by state `branch`, else by `feat/<prefix>-N-`. With `onBoard` only those tickets count; with null any ticket id from the branch does. */
function ticketOf(cwd: string, worktrees: Worktree[], tickets: Record<string, unknown>, onBoard: Set<string> | null, prefix: string | null): string | null {
  let best: Worktree | null = null
  for (const w of worktrees) {
    if ((cwd === w.path || cwd.startsWith(w.path.replace(/\/+$/, '') + '/')) && (!best || w.path.length > best.path.length)) best = w
  }
  if (!best) return null
  for (const id of onBoard ?? Object.keys(tickets)) {
    const t = tickets[id]
    if (isObj(t) && t.branch === best.branch) return id
  }
  const n = prefix ? best.branch.match(new RegExp(`^feat/${prefix.toLowerCase()}-(\\d+)(?:-|$)`))?.[1] : undefined
  const id = n ? `${prefix}-${n}` : null
  return id && (!onBoard || onBoard.has(id)) ? id : null
}

/** The sessions that belong to a ticket for the spend ledger. Unlike the charts, the ticket need not be on the board. */
export function ledgerSessions(input: { snapshots: unknown[]; worktrees: Worktree[]; state: unknown; prefix: string | null; now: number }): { ticket: string; session: Session }[] {
  const { snapshots, worktrees, state, prefix, now } = input
  const tickets = isObj(state) && isObj(state.tickets) ? state.tickets : {}
  const out: { ticket: string; session: Session }[] = []
  for (const raw of snapshots) {
    const session = cleanSnapshot(raw, now)
    const ticket = session && ticketOf(session.cwd, worktrees, tickets, null, prefix)
    if (session && ticket) out.push({ ticket, session })
  }
  return out
}

const QUEUED = ['merge-queued', 'build-queued', 'spec-queued']

/** Rows of queued stages keep their places; the others go newest update first, rows with no time last. The sort is stable. */
function newestFirst(rows: StatusRow[], updated: Record<string, number>): StatusRow[] {
  const sorted = rows.filter((r) => !QUEUED.includes(r.stage)).sort((a, b) => (updated[b.id] ?? -Infinity) - (updated[a.id] ?? -Infinity) || 0)
  return rows.map((r) => (QUEUED.includes(r.stage) ? r : sorted.shift()!))
}

export function buildApi(input: { state: unknown; snapshots: unknown[]; repo: Repo | null; titles: Record<string, string>; environmentId: string | null; now: number; worktrees?: Worktree[]; prefix?: string | null; merged?: MergedEntry[]; updated?: Record<string, number>; spend?: Record<string, { cost: number | null; tokens: number }>; history?: Record<string, Session[]>; details?: Record<string, Found>; teamHistory?: { role: TeamRole; session: Session }[] }): Api {
  const { state, snapshots, repo, titles, environmentId, now, worktrees = [], prefix = null, merged = [], updated = {}, spend = {}, history = {}, details = {}, teamHistory = [] } = input
  const tickets = isObj(state) && isObj(state.tickets) ? state.tickets : {}
  // A ticket whose PR is already in `merged` shows there only, even while state still has it in a stage.
  const mergedPrs = new Set(merged.filter((e) => e.number !== undefined).map((e) => `${e.id}#${e.number}`))
  const open = groupTickets(state).map((g) => ({ ...g, rows: g.rows.filter((r) => !mergedPrs.has(`${r.id}#${numOrNull(isObj(tickets[r.id]) ? tickets[r.id].pr : null)}`)) })).filter((g) => g.rows.length)
  const status = open.map((g) => ({
    name: g.name,
    count: g.rows.length,
    rows: newestFirst(g.rows.map((r) => {
      const t = isObj(tickets[r.id]) ? (tickets[r.id] as Record<string, unknown>) : {}
      const out: StatusRow = { id: r.id, title: r.title || titles[r.id] || '', risk: r.risk, next: r.next, stage: str(t.stage) }
      const digits = r.id.match(/-(\d+)$/)
      if (repo && repo.isGithubIssues && digits) out.issueUrl = `${repo.url}/issues/${digits[1]}`
      if (repo && typeof t.pr === 'number' && Number.isInteger(t.pr)) out.prUrl = `${repo.url}/pull/${t.pr}`
      if (environmentId && typeof t.childThreadId === 'string' && t.childThreadId)
        out.threadLink = `<t3-thread://v2/${environmentId}/${t.childThreadId}>`
      const specUrl = specUrlOf(repo?.url, t.specPath, t.specSha)
      if (specUrl) out.specUrl = specUrl
      const d = Object.hasOwn(details, r.id) ? details[r.id] : undefined
      if (d) {
        const { spec: _, ...plain } = d
        const url = d.kind === 'spec' ? out.specUrl : out.prUrl
        out.detail = url ? { ...plain, url } : plain
      }
      return out
    }), updated),
  }))
  const cleaned = snapshots.map((s) => cleanSnapshot(s, now)).filter((s): s is NonNullable<typeof s> => s !== null)
  const rowById = new Map(status.flatMap((g) => g.rows).map((r) => [r.id, r]))
  const onBoard = new Set(rowById.keys())
  for (const s of cleaned) {
    const row = rowById.get(ticketOf(s.cwd, worktrees, tickets, onBoard, prefix) ?? '')
    if (row) (row.gantt ??= []).push(s)
  }
  for (const r of rowById.values()) r.gantt?.sort((a, b) => a.updatedAt - b.updatedAt)
  const withExtras = ({ number, ...e }: MergedEntry): MergedEntry => {
    let out: MergedEntry = Object.hasOwn(spend, e.id) ? { ...e, spend: spend[e.id] } : e
    if (Object.hasOwn(history, e.id) && history[e.id].length) out = { ...out, gantt: history[e.id] }
    const key = `${e.id}#${number}`
    const found = Object.hasOwn(details, key) ? details[key] : undefined
    if (found) {
      const { spec, ...plain } = found
      const specUrl = repo && spec ? specUrlOf(repo.url, spec.path, spec.sha) : undefined
      out = { ...out, detail: e.prUrl ? { ...plain, url: e.prUrl } : plain, ...(specUrl ? { specUrl } : {}) }
    }
    return out
  }
  const link = (id: string | null) => (environmentId && id ? `<t3-thread://v2/${environmentId}/${id}>` : undefined)
  const isRunning = (i: TeamItem) => i.open && now - i.session.updatedAt <= RUNNING_MS
  const team = teamItems(snapshots, state, now)
  const live = team.filter((i) => i.role === 'chief').sort((a, b) => b.session.updatedAt - a.session.updatedAt)[0]
  const st = isObj(state) ? state : {}
  const chiefLink = link(cleanThreadId(st.chiefThreadId))
  const chief: Api['chief'] = { state: st.paused === true ? 'paused' : live && isRunning(live) ? 'running' : 'idle' }
  if (chiefLink) chief.threadLink = chiefLink
  if (live) chief.gantt = [live.session]
  const pm = new Map<string, TeamItem>()
  for (const { role, session } of teamHistory) pm.set(session.sessionId, { role, session, open: false })
  for (const i of team) {
    const old = pm.get(i.session.sessionId)
    if (i.role !== 'chief' && i.session.sessionId && (!old || i.session.updatedAt >= old.session.updatedAt)) pm.set(i.session.sessionId, i)
  }
  const pmRows = [...pm.values()]
    .sort((a, b) => b.session.updatedAt - a.session.updatedAt)
    .map((i): PmRow => {
      const row: PmRow = { sessionId: i.session.sessionId, role: i.role as TeamRole, state: isRunning(i) ? 'running' : 'finished', gantt: [i.session] }
      const threadLink = link(cleanThreadId(i.session.threadId))
      if (threadLink) row.threadLink = threadLink
      return row
    })
  return { generatedAt: now, status, merged: merged.map(withExtras), chief, pm: pmRows }
}

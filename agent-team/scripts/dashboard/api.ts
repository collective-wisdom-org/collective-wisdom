import { GROUP_ORDER, groupTickets } from './groups.ts'
import type { MergedEntry } from './merged.ts'
import { specUrlOf } from './details.ts'
import type { Detail, Found } from './details.ts'
import type { BacklogItem, Priority } from './backlog.ts'
import { headsPattern, idForNumber, prefixesPattern } from './titles.ts'
import type { Retired } from './titles.ts'
import { isWorktree } from '../../../mods/agent-gantt/hooks/rows.ts'

export type SnapshotRow = { id: string; depth: number; name: string; repo: string; start: number; end: number | null; tokens: number; cost: number | null; kind: 'session' | 'task' | 'agent'; segments: [number, number | null][]; model: string | null; harness: string | null }
export type Snapshot = { sessionId: string; cwd: string; updatedAt: number; total: number | null; pricing: number | null; rows: SnapshotRow[] }
export type Session = { sessionId: string; cwd: string; updatedAt: number; stale: boolean; total: number | null; pricing: number | null; rows: SnapshotRow[]; threadId?: string | null; heading?: string | null; ticket?: string | null; request?: string | null }
export type TeamRole = 'ranking' | 'hygiene'
type TeamState = 'running' | 'idle' | 'paused'
type PmRow = { sessionId: string; role: TeamRole; state: 'running' | 'finished'; threadLink?: string; gantt: Session[] }
type StatusRow = { id: string; title: string; risk: string; next: string; stage: string; stageAt?: string; stale?: true; helper?: boolean; issueUrl?: string; prUrl?: string; specUrl?: string; threadLink?: string; gantt?: Session[]; detail?: Detail; ci?: [number, number | null][] }
export type Worktree = { path: string; branch: string }
export type Api = {
  generatedAt: number
  status: { name: string; count: number; rows: StatusRow[]; moreUrl?: string; readAt?: number; stale?: true }[]
  merged: MergedEntry[]
  chief: { state: TeamState; threadLink?: string; gantt?: Session[] }
  pm: PmRow[]
}
type Repo = { url: string; isGithubIssues: boolean }
/** Where a ticket id and the full backlog open in the repo's tracker. `issue` gives nothing for an id the tracker would not own. */
export type TrackerLinks = { issue(id: string): string | undefined; backlog: string | null }

const DAY = 24 * 3600 * 1000
const STALE_MS = 30_000
const NAME_MAX = 60
const LABEL_MAX = 40
const SEGMENTS_MAX = 500
const KINDS = ['session', 'task', 'agent']
const RUNNING_MS = 60_000
const THREAD_MAX = 200
const HEADING_MAX = 40
const REQUEST_MAX = 80
const HELPER = 'TICKET HELPER'
const LIST_STALE_MS = 3600 * 1000 // a saved Todo or Backlog list older than this is called stale
const PRIORITY_RANK: Record<Priority, number> = { urgent: 0, high: 1, medium: 2, low: 3 }
const HEADINGS: Record<string, TeamRole | 'helper'> = { 'BACKLOG RANKING': 'ranking', 'PROJECT MANAGER HYGIENE': 'hygiene', [HELPER]: 'helper' }

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)
const str = (x: unknown): string => (typeof x === 'string' ? x : '')
const num = (x: unknown): number => (typeof x === 'number' && Number.isFinite(x) ? x : 0)
const numOrNull = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null)

/** The value cell of the first row named `name` or `name (...)`, else undefined. */
function rowValue(markdown: string, name: string): string | undefined {
  for (const line of markdown.split(/\r?\n/)) {
    if (!line.trimStart().startsWith('|')) continue
    const [, key, value] = line.split('|').map((c) => c.trim())
    if (key === name || key?.startsWith(`${name} (`)) return value
  }
  return undefined
}

const firstTicked = (cell: string | undefined): string | undefined => cell?.match(/`([^`]+)`/)?.[1]

function trackerIsGithub(markdown: string): boolean {
  return firstTicked(rowValue(markdown, 'Tracker'))?.toLowerCase() === 'github'
}

export function repoUrlFromProject(markdown: string): Repo | null {
  const m = markdown.match(/^\|\s*Repo\b[^|]*\|[^|]*<(https?:\/\/[^>\s]+)>/m)
  if (!m) return null
  return { url: m[1].replace(/\/+$/, ''), isGithubIssues: trackerIsGithub(markdown) }
}

const githubLinks = (url: string): TrackerLinks => ({
  issue: (id) => {
    const n = id.match(/-(\d+)$/)?.[1]
    return n ? `${url}/issues/${n}` : undefined
  },
  backlog: `${url}/issues`,
})

const ticketLinks = (key: string, link: (id: string) => string, backlog: string | null): TrackerLinks => {
  const own = new RegExp(`^${key}-\\d+$`)
  return { issue: (id) => (own.test(id) ? link(id) : undefined), backlog }
}

/** Ticket and backlog links for the tracker in the `Tracker` row, or null when none can be built (a missing row, a `TODO` or a template placeholder gives no link). */
export function trackerLinksFromProject(markdown: string): TrackerLinks | null {
  const tracker = firstTicked(rowValue(markdown, 'Tracker'))?.toLowerCase()
  if (tracker === 'github') {
    const repo = repoUrlFromProject(markdown)
    return repo && githubLinks(repo.url)
  }
  if (tracker === 'jira') {
    const cell = rowValue(markdown, 'Jira site')
    const key = firstTicked(rowValue(markdown, 'Jira project key'))
    const raw = firstTicked(cell) ?? cell?.match(/<([^>\s]+)>/)?.[1]
    if (!raw || !key || !/^[A-Z][A-Z0-9_]+$/.test(key) || /TODO|</.test(raw)) return null
    let url: URL
    try {
      url = new URL(raw)
    } catch {
      return null
    }
    if (url.protocol !== 'https:' || url.hostname === 'example.atlassian.net') return null
    const site = (url.origin + url.pathname).replace(/\/+$/, '')
    const jql = `project = ${key} AND statusCategory = "To Do" ORDER BY created DESC`
    return ticketLinks(key, (id) => `${site}/browse/${id}`, `${site}/issues/?jql=${encodeURIComponent(jql)}`)
  }
  // `linear`, or a missing or TODO tracker row, which means linear.
  const cell = rowValue(markdown, 'Linear team name')
  const link = cell?.match(/https:\/\/linear\.app\/([A-Za-z0-9-]+)\/([^\s>)`]*)/)
  const key = link?.[2].match(/(?:^|\/)team\/([A-Z][A-Z0-9]*)(?:\/|$)/)?.[1] ?? firstTicked(rowValue(markdown, 'Issue identifier prefix'))
  if (!link || !key || !/^[A-Z][A-Z0-9]*$/.test(key) || /TODO/.test(key)) return null
  const base = `https://linear.app/${link[1]}`
  return ticketLinks(key, (id) => `${base}/issue/${id}`, `${base}/team/${key}/backlog`)
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
function cleanWith(s: unknown, now: number, keep: (cwd: string) => boolean): { session: Session; open: boolean; cursor: boolean } | null {
  if (!isObj(s) || !Array.isArray(s.rows) || !keep(str(s.cwd))) return null
  const updatedAt = numOrNull(s.updatedAt)
  if (updatedAt === null || now - updatedAt > DAY) return null
  const cleaned = s.rows.map((r) => cleanRow(r, null)).filter((r): r is SnapshotRow => r !== null)
  // The Claude Code mod rewrites its snapshot every 5 s, so silence means a stopped session. The Cursor hook writes only when an event fires: its open spans stay open and are drawn to now.
  const cursor = cleaned.length > 0 && cleaned.every((r) => r.harness === 'Cursor')
  const open = cleaned.some((r) => /^main(:task:\d+)?$/.test(r.id) && r.segments.at(-1)?.[1] === null)
  // The main row and its task rows never end while the session lives, so only the other agents say whether it is stale.
  const working = cleaned.some((r) => r.kind === 'agent' && r.id !== 'main' && r.end === null)
  const stale = !cursor && now - updatedAt > STALE_MS && working
  const close = (r: SnapshotRow): SnapshotRow => ({ ...r, end: updatedAt, segments: r.segments.map(([a, b]) => [a, b === null ? Math.max(a, updatedAt) : b]) })
  const rows = cleaned.map((r) => (r.end === null && !cursor && (stale || (!working && (r.id === 'main' || r.kind === 'task'))) ? close(r) : r))
  return { session: { sessionId: str(s.sessionId), cwd: str(s.cwd), updatedAt, stale, total: numOrNull(s.total), pricing: numOrNull(s.pricing), rows }, open, cursor }
}

export const cleanSnapshot = (s: unknown, now: number): Session | null => cleanWith(s, now, isWorktree)?.session ?? null

/** Like cleanSnapshot, but for a session outside any worktree (the root checkout), with its thread id, heading, the ticket a helper filed (kept only as `<prefix>-N`) and its request line. */
export function cleanTeamSnapshot(s: unknown, now: number, prefix: string | null = null, retired: Retired = []): { session: Session; open: boolean; cursor: boolean } | null {
  const got = cleanWith(s, now, (cwd) => !isWorktree(cwd))
  if (!got || !isObj(s)) return null
  const heading = typeof s.heading === 'string' && s.heading.length <= HEADING_MAX ? s.heading : null
  const ticket = prefix && typeof s.ticket === 'string' && new RegExp(`^${prefixesPattern(prefix, retired)}-\\d+$`).test(s.ticket) ? s.ticket : null
  const request = typeof s.request === 'string' && s.request.length <= REQUEST_MAX ? s.request : null
  return { open: got.open, cursor: got.cursor, session: { ...got.session, threadId: cleanThreadId(s.threadId), heading, ticket, request } }
}

/** The chief of staff, a project manager child, a ticket helper, or null for any other session. The chief is matched by state; the others by heading. */
export function teamRole(session: Session, state: unknown): 'chief' | 'helper' | TeamRole | null {
  const st = isObj(state) ? state : {}
  if ((typeof st.chiefSessionId === 'string' && st.chiefSessionId && session.sessionId === st.chiefSessionId) || (typeof st.chiefThreadId === 'string' && st.chiefThreadId && session.threadId === st.chiefThreadId)) return 'chief'
  return Object.hasOwn(HEADINGS, session.heading ?? '') ? HEADINGS[session.heading!] : null
}

type TeamItem = { role: 'chief' | 'helper' | TeamRole; session: Session; open: boolean; cursor?: boolean }

function teamItems(snapshots: unknown[], state: unknown, now: number, prefix: string | null = null, retired: Retired = []): TeamItem[] {
  const out: TeamItem[] = []
  for (const raw of snapshots) {
    const got = cleanTeamSnapshot(raw, now, prefix, retired)
    const role = got && teamRole(got.session, state)
    if (got && role) out.push({ role, ...got })
  }
  return out
}

/** The project manager sessions among the snapshots, for the history. */
export function teamSessions(input: { snapshots: unknown[]; state: unknown; now: number }): { role: TeamRole; session: Session }[] {
  return teamItems(input.snapshots, input.state, input.now).flatMap((i) => (i.role === 'chief' || i.role === 'helper' ? [] : [{ role: i.role, session: i.session }]))
}

/** The ticket a snapshot belongs to: its worktree's branch, matched by state `branch`, else by `<head><prefix>-N-` for a head in `heads`. With `onBoard` only those tickets count; with null any ticket id from the branch does. */
function ticketOf(cwd: string, worktrees: Worktree[], tickets: Record<string, unknown>, onBoard: Set<string> | null, prefix: string | null, heads: string[] = ['feat/'], retired: Retired = []): string | null {
  let best: Worktree | null = null
  for (const w of worktrees) {
    if ((cwd === w.path || cwd.startsWith(w.path.replace(/\/+$/, '') + '/')) && (!best || w.path.length > best.path.length)) best = w
  }
  if (!best) return null
  for (const id of onBoard ?? Object.keys(tickets)) {
    const t = tickets[id]
    if (isObj(t) && t.branch === best.branch) return id
  }
  const n = prefix ? best.branch.match(new RegExp(`^${headsPattern(heads)}${prefixesPattern(prefix, retired, true)}-(\\d+)(?:-|$)`))?.[1] : undefined
  const id = prefix && n ? idForNumber(Number(n), prefix, retired) : null
  return id && (!onBoard || onBoard.has(id)) ? id : null
}

/** The sessions that belong to a ticket for the spend ledger: worktree sessions by branch, and root checkout ticket helper sessions by the ticket they filed. Unlike the charts, the ticket need not be on the board. */
export function ledgerSessions(input: { snapshots: unknown[]; worktrees: Worktree[]; state: unknown; prefix: string | null; retired?: Retired; heads?: string[]; now: number }): { ticket: string; session: Session }[] {
  const { snapshots, worktrees, state, prefix, retired = [], heads, now } = input
  const tickets = isObj(state) && isObj(state.tickets) ? state.tickets : {}
  const out: { ticket: string; session: Session }[] = []
  for (const raw of snapshots) {
    const session = cleanSnapshot(raw, now)
    const ticket = session && ticketOf(session.cwd, worktrees, tickets, null, prefix, heads, retired)
    if (session && ticket) out.push({ ticket, session })
    else if (!session) {
      const helper = cleanTeamSnapshot(raw, now, prefix, retired)?.session
      if (helper?.heading === HELPER && helper.ticket) out.push({ ticket: helper.ticket, session: helper })
    }
  }
  return out
}

const SPEC_QUEUE = 'Waiting to spec'
const QUEUED = ['merge-queued', 'build-queued', 'spec-queued']

/** Rows of queued stages keep their places; the others go newest update first, rows with no time last. The sort is stable. */
function newestFirst(rows: StatusRow[], updated: Record<string, number>): StatusRow[] {
  const sorted = rows.filter((r) => !QUEUED.includes(r.stage)).sort((a, b) => (updated[b.id] ?? -Infinity) - (updated[a.id] ?? -Infinity) || 0)
  return rows.map((r) => (QUEUED.includes(r.stage) ? r : sorted.shift()!))
}

export function buildApi(input: { state: unknown; snapshots: unknown[]; repo: Repo | null; links?: TrackerLinks | null; titles: Record<string, string>; environmentId: string | null; now: number; worktrees?: Worktree[]; prefix?: string | null; retired?: Retired; heads?: string[]; merged?: MergedEntry[]; openPrs?: Record<string, number>; updated?: Record<string, number>; spend?: Record<string, { cost: number | null; tokens: number }>; history?: Record<string, Session[]>; details?: Record<string, Found>; ci?: Record<string, [number, number | null][]>; teamHistory?: { role: TeamRole; session: Session }[]; backlog?: BacklogItem[] }): Api {
  const { state, snapshots, repo, titles, environmentId, now, worktrees = [], prefix = null, retired = [], heads, merged = [], openPrs = {}, updated = {}, spend = {}, history = {}, details = {}, ci = {}, teamHistory = [], backlog = [] } = input
  const tickets = isObj(state) && isObj(state.tickets) ? state.tickets : {}
  // Without `links`, the GitHub links come from `repo`.
  const links = input.links !== undefined ? input.links : repo?.isGithubIssues ? githubLinks(repo.url) : null
  // A ticket whose PR is already in `merged` shows there only, even while state still has it in a stage.
  const mergedPrs = new Set(merged.filter((e) => e.number !== undefined).map((e) => `${e.id}#${e.number}`))
  const open = groupTickets(state).map((g) => ({ ...g, rows: g.rows.filter((r) => !mergedPrs.has(`${r.id}#${numOrNull(isObj(tickets[r.id]) ? tickets[r.id].pr : null)}`)) })).filter((g) => g.rows.length)
  const status = open.map((g) => ({
    name: g.name,
    count: g.rows.length,
    rows: newestFirst(g.rows.map((r) => {
      const t = isObj(tickets[r.id]) ? (tickets[r.id] as Record<string, unknown>) : {}
      const out: StatusRow = { id: r.id, title: titles[r.id] || r.title || '', risk: r.risk, next: r.next, stage: str(t.stage) }
      if (r.stageAt) out.stageAt = r.stageAt
      const issueUrl = links?.issue(r.id)
      if (issueUrl) out.issueUrl = issueUrl
      // State `pr` (set at MERGE READY) wins; before that the open PR found by its branch gives the link.
      const openPr = Object.hasOwn(openPrs, r.id) ? openPrs[r.id] : undefined
      const prNum = typeof t.pr === 'number' && Number.isInteger(t.pr) ? t.pr : Number.isInteger(openPr) && openPr! > 0 ? openPr : undefined
      if (repo && prNum !== undefined) out.prUrl = `${repo.url}/pull/${prNum}`
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
      const waits = Object.hasOwn(ci, `${r.id}#${t.pr}`) ? ci[`${r.id}#${t.pr}`] : undefined
      if (waits?.length) out.ci = waits
      return out
    }), updated),
  }))
  // Todo and Backlog come from the tracker; a ticket in state or in the merged list shows there only.
  const shown = new Set([...Object.keys(tickets), ...merged.map((e) => e.id)])
  const listRow = (b: BacklogItem): StatusRow => {
    const row: StatusRow = { id: b.id, title: b.title, risk: '', next: '', stage: '' }
    const issueUrl = links?.issue(b.id)
    if (issueUrl) row.issueUrl = issueUrl
    return row
  }
  // A list read from the saved file carries a read time; one over an hour old is stale.
  const readAtOf = (items: BacklogItem[]): Pick<Api['status'][number], 'readAt' | 'stale'> => {
    const readAt = items[0].readAt
    return readAt === undefined ? {} : { readAt, ...(now - readAt > LIST_STALE_MS ? { stale: true as const } : {}) }
  }
  // Todo tickets wait to be specced after the spec-queued ones, in the order cos_todo.py tries them: priority, then oldest first (no date last), then tracker order (the sort is stable).
  const todo = backlog
    .filter((b) => b.state === 'Todo' && !shown.has(b.id))
    .sort((a, b) => (a.priority ? PRIORITY_RANK[a.priority] : 4) - (b.priority ? PRIORITY_RANK[b.priority] : 4) || (a.createdAt ?? Infinity) - (b.createdAt ?? Infinity) || 0)
  if (todo.length) {
    const extra = readAtOf(todo)
    const rows = todo.map((b) => ({ ...listRow(b), ...(extra.stale ? { stale: true as const } : {}) }))
    const queue = status.find((g) => g.name === SPEC_QUEUE)
    if (queue) {
      queue.rows.push(...rows)
      queue.count = queue.rows.length
      Object.assign(queue, extra)
    } else {
      // Where groupTickets would put it: after the last group that comes before it in the status layout.
      const before = GROUP_ORDER.slice(0, GROUP_ORDER.indexOf(SPEC_QUEUE))
      const at = status.findLastIndex((g) => before.includes(g.name)) + 1
      status.splice(at, 0, { name: SPEC_QUEUE, count: rows.length, rows, ...extra })
    }
  }
  const link = (id: string | null) => (environmentId && id ? `<t3-thread://v2/${environmentId}/${id}>` : undefined)
  const isRunning = (i: TeamItem) => i.open && (i.cursor === true || now - i.session.updatedAt <= RUNNING_MS)
  const team = teamItems(snapshots, state, now, prefix, retired)
  // A running helper that has filed no ticket yet is a placeholder row; a finished one shows nowhere.
  const writing = team
    .filter((i) => i.role === 'helper' && !i.session.ticket && i.session.sessionId && isRunning(i))
    .sort((a, b) => b.session.updatedAt - a.session.updatedAt)
    .map((i): StatusRow => {
      const row: StatusRow = { id: `helper:${i.session.sessionId}`, title: i.session.request ?? '', helper: true, risk: '', next: '', stage: '', gantt: [i.session] }
      const threadLink = link(cleanThreadId(i.session.threadId))
      if (threadLink) row.threadLink = threadLink
      return row
    })
  if (writing.length) status.push({ name: 'Writing tickets', count: writing.length, rows: writing })
  // Backlog is sorted by priority, then newest first (no date last), then tracker order (the sort is stable); the page pages it.
  const queued = backlog
    .filter((b) => b.state === 'Backlog' && !shown.has(b.id))
    .sort((a, b) => (a.priority ? PRIORITY_RANK[a.priority] : 4) - (b.priority ? PRIORITY_RANK[b.priority] : 4) || (b.createdAt ?? -Infinity) - (a.createdAt ?? -Infinity) || 0)
  if (queued.length) {
    const group: Api['status'][number] = { name: 'Backlog', count: queued.length, rows: queued.map(listRow), ...readAtOf(queued) }
    if (links?.backlog) group.moreUrl = links.backlog
    status.push(group)
  }
  const cleaned = snapshots.map((s) => cleanSnapshot(s, now)).filter((s): s is NonNullable<typeof s> => s !== null)
  const rowById = new Map(status.flatMap((g) => g.rows).map((r) => [r.id, r]))
  const onBoard = new Set(rowById.keys())
  for (const s of cleaned) {
    const row = rowById.get(ticketOf(s.cwd, worktrees, tickets, onBoard, prefix, heads, retired) ?? '')
    if (row) (row.gantt ??= []).push(s)
  }
  // A helper's session joins every ticket row it filed: live copies from the snapshots, finished ones from the history, the live copy winning.
  const helpers = new Map<string, Map<string, Session>>()
  const addHelper = (ticket: string, s: Session) => {
    if (!s.sessionId || !rowById.has(ticket)) return
    if (!helpers.has(ticket)) helpers.set(ticket, new Map())
    helpers.get(ticket)!.set(s.sessionId, s)
  }
  for (const id of rowById.keys()) for (const s of Object.hasOwn(history, id) ? history[id] : []) if (!isWorktree(s.cwd)) addHelper(id, s)
  for (const i of team) if (i.role === 'helper' && i.session.ticket) addHelper(i.session.ticket, i.session)
  for (const [id, byId] of helpers) (rowById.get(id)!.gantt ??= []).push(...byId.values())
  for (const r of rowById.values()) r.gantt?.sort((a, b) => a.updatedAt - b.updatedAt)
  const withExtras = ({ number, ...e }: MergedEntry): MergedEntry => {
    let out: MergedEntry = Object.hasOwn(spend, e.id) ? { ...e, spend: spend[e.id] } : e
    if (Object.hasOwn(history, e.id) && history[e.id].length) out = { ...out, gantt: history[e.id] }
    const key = `${e.id}#${number}`
    if (Object.hasOwn(ci, key) && ci[key].length) out = { ...out, ci: ci[key] }
    const found = Object.hasOwn(details, key) ? details[key] : undefined
    if (found) {
      const { spec, ...plain } = found
      const specUrl = repo && spec ? specUrlOf(repo.url, spec.path, spec.sha) : undefined
      out = { ...out, detail: e.prUrl ? { ...plain, url: e.prUrl } : plain, ...(specUrl ? { specUrl } : {}) }
    }
    return out
  }
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
    if (i.role !== 'chief' && i.role !== 'helper' && i.session.sessionId && (!old || i.session.updatedAt >= old.session.updatedAt)) pm.set(i.session.sessionId, i)
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

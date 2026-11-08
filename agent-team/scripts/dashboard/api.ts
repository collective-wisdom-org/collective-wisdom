import { groupTickets } from '../../.claude/mods/status-pane/hooks/groups.ts'
import { isWorktree } from '../../../mods/agent-gantt/hooks/rows.ts'

export type SnapshotRow = { id: string; depth: number; name: string; repo: string; start: number; end: number | null; tokens: number; cost: number | null; childCount: number }
export type Snapshot = { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: SnapshotRow[] }
type StatusRow = { id: string; title: string; risk: string; next: string; stage: string; issueUrl?: string; prUrl?: string; threadLink?: string; gantt?: Api['gantt'] }
export type Worktree = { path: string; branch: string }
export type Api = {
  generatedAt: number
  status: { name: string; count: number; rows: StatusRow[] }[]
  gantt: { sessionId: string; cwd: string; updatedAt: number; stale: boolean; total: number | null; rows: SnapshotRow[] }[]
}
type Repo = { url: string; isGithubIssues: boolean }

const DAY = 24 * 3600 * 1000
const STALE_MS = 30_000
const NAME_MAX = 60

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)
const str = (x: unknown): string => (typeof x === 'string' ? x : '')
const num = (x: unknown): number => (typeof x === 'number' && Number.isFinite(x) ? x : 0)
const numOrNull = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null)

export function repoUrlFromProject(markdown: string): Repo | null {
  const m = markdown.match(/^\|\s*Repo\b[^|]*\|[^|]*<(https?:\/\/[^>\s]+)>/m)
  if (!m) return null
  return { url: m[1].replace(/\/+$/, ''), isGithubIssues: markdown.includes('Tickets are GitHub issues') }
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

function cleanRow(r: unknown, endFill: number | null): SnapshotRow | null {
  if (!isObj(r)) return null
  const end = numOrNull(r.end)
  return {
    id: str(r.id),
    depth: num(r.depth),
    name: str(r.name).slice(0, NAME_MAX),
    repo: str(r.repo),
    start: num(r.start),
    end: end === null ? endFill : end,
    tokens: num(r.tokens),
    cost: numOrNull(r.cost),
    childCount: num(r.childCount),
  }
}

function cleanSnapshot(s: unknown, now: number): Api['gantt'][number] | null {
  if (!isObj(s) || !Array.isArray(s.rows) || !isWorktree(str(s.cwd))) return null
  const updatedAt = numOrNull(s.updatedAt)
  if (updatedAt === null || now - updatedAt > DAY) return null
  const cleaned = s.rows.map((r) => cleanRow(r, null)).filter((r): r is SnapshotRow => r !== null)
  // The main row never ends while the session lives, so only the other rows say whether it is stale.
  const working = cleaned.some((r) => r.id !== 'main' && r.end === null)
  const stale = now - updatedAt > STALE_MS && working
  const rows = cleaned.map((r) => (r.end === null && (stale || (!working && r.id === 'main')) ? { ...r, end: updatedAt } : r))
  return { sessionId: str(s.sessionId), cwd: str(s.cwd), updatedAt, stale, total: numOrNull(s.total), rows }
}

/** The board ticket a snapshot belongs to: its worktree's branch, matched by state `branch`, else by `feat/<prefix>-N-`. */
function ticketOf(cwd: string, worktrees: Worktree[], tickets: Record<string, unknown>, onBoard: Set<string>, prefix: string | null): string | null {
  let best: Worktree | null = null
  for (const w of worktrees) {
    if ((cwd === w.path || cwd.startsWith(w.path.replace(/\/+$/, '') + '/')) && (!best || w.path.length > best.path.length)) best = w
  }
  if (!best) return null
  for (const id of onBoard) {
    const t = tickets[id]
    if (isObj(t) && t.branch === best.branch) return id
  }
  const n = prefix ? best.branch.match(new RegExp(`^feat/${prefix.toLowerCase()}-(\\d+)(?:-|$)`))?.[1] : undefined
  const id = n ? `${prefix}-${n}` : null
  return id && onBoard.has(id) ? id : null
}

export function buildApi(input: { state: unknown; snapshots: unknown[]; repo: Repo | null; titles: Record<string, string>; environmentId: string | null; now: number; worktrees?: Worktree[]; prefix?: string | null }): Api {
  const { state, snapshots, repo, titles, environmentId, now, worktrees = [], prefix = null } = input
  const tickets = isObj(state) && isObj(state.tickets) ? state.tickets : {}
  const status = groupTickets(state).map((g) => ({
    name: g.name,
    count: g.count,
    rows: g.rows.map((r) => {
      const t = isObj(tickets[r.id]) ? (tickets[r.id] as Record<string, unknown>) : {}
      const out: StatusRow = { id: r.id, title: r.title || titles[r.id] || '', risk: r.risk, next: r.next, stage: str(t.stage) }
      const digits = r.id.match(/-(\d+)$/)
      if (repo && repo.isGithubIssues && digits) out.issueUrl = `${repo.url}/issues/${digits[1]}`
      if (repo && typeof t.pr === 'number' && Number.isInteger(t.pr)) out.prUrl = `${repo.url}/pull/${t.pr}`
      if (environmentId && typeof t.childThreadId === 'string' && t.childThreadId)
        out.threadLink = `<t3-thread://v2/${environmentId}/${t.childThreadId}>`
      return out
    }),
  }))
  const cleaned = snapshots.map((s) => cleanSnapshot(s, now)).filter((s): s is NonNullable<typeof s> => s !== null)
  const rowById = new Map(status.flatMap((g) => g.rows).map((r) => [r.id, r]))
  const onBoard = new Set(rowById.keys())
  const gantt: Api['gantt'] = []
  for (const s of cleaned) {
    const row = rowById.get(ticketOf(s.cwd, worktrees, tickets, onBoard, prefix) ?? '')
    if (row) (row.gantt ??= []).push(s)
    else gantt.push(s)
  }
  for (const r of rowById.values()) r.gantt?.sort((a, b) => a.updatedAt - b.updatedAt)
  return { generatedAt: now, status, gantt }
}

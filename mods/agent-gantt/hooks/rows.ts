import type { AgentRecord, Prices, Segment, Tokens } from '../types/index.d.ts'

export type Row = {
  id: string
  depth: number // 1 for a task, 2 for the subagents of a task, and so on
  kind: 'session' | 'task' | 'agent' // 'session' only in older snapshots; buildRows no longer emits it
  name: string
  repo: string
  start: number // ms since epoch
  end: number | null // null while running
  tokens: number // input + output + cache read + cache write
  cost: number | null // dollars; null without a price table or for an unknown model family
  segments: Segment[] // working spans; the gaps between them are waiting
  model: string | null // the model with the most output tokens, without its `claude-` prefix
  harness: string | null // `T3 Code` or `Claude Code`
}

/** The part of an `$.agent.list()` entry the builder reads. */
export type ListedAgent = { id: string; parentId?: string; name?: string }

export const MAIN = 'main'

const T3_WORKTREE = /\/\.t3\/worktrees\/([^/]+)\/[^/]+/
const NESTED_WORKTREE = /^(.*)\/\.worktrees\/[^/]+/

/** True when the working directory is inside a T3 worktree or a `.worktrees/` checkout. */
export function isWorktree(cwd: string): boolean {
  return T3_WORKTREE.test(cwd) || NESTED_WORKTREE.test(cwd)
}

/** The repo name for a working directory: T3 and `.worktrees/` paths map to the main checkout's name. */
export function repoOf(cwd: string): string {
  const t3 = T3_WORKTREE.exec(cwd)
  if (t3?.[1]) return t3[1]
  const nested = NESTED_WORKTREE.exec(cwd)
  const path = nested?.[1] ?? cwd
  return path.split('/').filter(Boolean).pop() ?? ''
}

const total = (t: Tokens) => t.input + t.output + t.read + t.write

/** Dollars for one model's tokens, or null when its family is not in the table. Cache writes use the 1h rate: TurnUsage has no 5m/1h split, and the sessions checked wrote only 1h entries. */
function modelCost(model: string, t: Tokens, prices: Prices): number | null {
  const family = Object.keys(prices).find(f => model.includes(f))
  const p = family === undefined ? undefined : prices[family]
  if (!p) return null
  return (t.input * p.input + t.output * p.output + t.read * p.read + t.write * p.write_1h) / 1e6
}

function costOf(usage: Record<string, Tokens>, prices: Prices | null): number | null {
  if (!prices) return null
  let sum = 0
  for (const [model, t] of Object.entries(usage)) {
    const c = modelCost(model, t, prices)
    if (c === null) return null
    sum += c
  }
  return sum
}

/** The model id with the most output tokens, `claude-` dropped; null without usage. */
function topModel(usage: Record<string, Tokens>): string | null {
  let best: string | null = null
  let most = -1
  for (const [model, t] of Object.entries(usage)) {
    if (t.output > most) {
      best = model
      most = t.output
    }
  }
  return best === null ? null : best.replace(/^claude-/, '')
}

const tokensOf = (usage: Record<string, Tokens>) => Object.values(usage).reduce((n, t) => n + total(t), 0)

/** What `all` holds beyond `parts`, per model; models with nothing left are dropped. */
function minusUsage(all: Record<string, Tokens>, parts: Record<string, Tokens>[]): Record<string, Tokens> {
  const left: Record<string, Tokens> = {}
  for (const [model, t] of Object.entries(all)) {
    const d: Tokens = { input: t.input, output: t.output, read: t.read, write: t.write }
    for (const part of parts) {
      const p = part[model]
      if (p === undefined) continue
      d.input -= p.input
      d.output -= p.output
      d.read -= p.read
      d.write -= p.write
    }
    if (total(d) > 0) left[model] = d
  }
  return left
}

/** The rows of the chart, depth first: a row per task with the subagents spawned in it, then subagents the mod could not place. Main's usage outside any task is one `outside a task` row. */
export function buildRows(
  records: AgentRecord[],
  agents: ListedAgent[],
  prices: Prices | null,
  harness: string | null = null,
): Row[] {
  const known = new Set(records.map(r => r.id))
  const parentOf = (r: AgentRecord) =>
    r.parentId !== null && r.parentId !== r.id && known.has(r.parentId) ? r.parentId : MAIN
  const kids = new Map<string, AgentRecord[]>()
  for (const r of records) {
    if (r.id === MAIN) continue
    const parent = parentOf(r)
    kids.set(parent, [...(kids.get(parent) ?? []), r])
  }
  const listed = new Map(agents.map(a => [a.id, a]))
  const byStart = (list: AgentRecord[]) => [...list].sort((a, b) => a.start - b.start)

  const rows: Row[] = []
  const base = (r: AgentRecord) => ({ repo: repoOf(r.cwd), harness })
  const agentRow = (r: AgentRecord, depth: number) => {
    rows.push({
      ...base(r),
      id: r.id,
      depth,
      kind: 'agent',
      name: listed.get(r.id)?.name || r.name,
      start: r.start,
      end: r.end,
      tokens: tokensOf(r.usage),
      cost: costOf(r.usage, prices),
      // A run no hook saw has no spans: draw it as one bar, as before.
      segments: r.segments.length === 0 ? [[r.start, r.end]] : r.segments,
      model: topModel(r.usage),
    })
    for (const k of byStart(kids.get(r.id) ?? [])) agentRow(k, depth + 1)
  }
  const main = records.find(r => r.id === MAIN)
  if (!main) {
    for (const k of byStart(kids.get(MAIN) ?? [])) agentRow(k, 1)
    return rows
  }
  const top = byStart(kids.get(MAIN) ?? [])
  // A task with no spans gets no row, so a subagent of it goes to depth 1 with the unplaced.
  const placed = (r: AgentRecord) => r.taskIndex !== null && (main.tasks[r.taskIndex]?.segments.length ?? 0) > 0
  // Usage that landed before any task opened, or in a task with no spans, would otherwise drop out of the total.
  const outside = minusUsage(main.usage, main.tasks.filter(k => k.segments.length > 0).map(k => k.usage))
  if (Object.keys(outside).length > 0) {
    rows.push({
      ...base(main),
      id: `${MAIN}:outside`,
      depth: 1,
      kind: 'task',
      name: 'outside a task',
      start: main.start,
      end: main.start,
      tokens: tokensOf(outside),
      cost: costOf(outside, prices),
      segments: [],
      model: topModel(outside),
    })
  }
  main.tasks.forEach((task, i) => {
    // A prompt that started no turn (a slash command) has no spans: no row.
    if (task.segments.length === 0) return
    const last = task.segments[task.segments.length - 1]!
    rows.push({
      ...base(main),
      id: `${MAIN}:task:${i}`,
      depth: 1,
      kind: 'task',
      name: task.name,
      start: task.start,
      end: last[1],
      tokens: tokensOf(task.usage),
      cost: costOf(task.usage, prices),
      segments: task.segments,
      model: topModel(task.usage),
    })
    for (const k of top) if (k.taskIndex === i) agentRow(k, 2)
  })
  for (const k of top) if (!placed(k)) agentRow(k, 1)
  return rows
}

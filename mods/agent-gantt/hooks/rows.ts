import type { AgentRecord, Prices, Tokens } from '../types/index.d.ts'

export type Row = {
  id: string
  depth: number // 0 for main, 1 for its children, and so on
  name: string
  repo: string
  start: number // ms since epoch
  end: number | null // null while running
  tokens: number // input + output + cache read + cache write
  cost: number | null // dollars; null without a price table or for an unknown model family
  childCount: number
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

/** Dollars for one model's tokens, or null when its family is not in the table. Cache writes use the 5m rate. */
function modelCost(model: string, t: Tokens, prices: Prices): number | null {
  const family = Object.keys(prices).find(f => model.includes(f))
  const p = family === undefined ? undefined : prices[family]
  if (!p) return null
  return (t.input * p.input + t.output * p.output + t.read * p.read + t.write * p.write_5m) / 1e6
}

function costOf(record: AgentRecord, prices: Prices | null): number | null {
  if (!prices) return null
  let sum = 0
  for (const [model, t] of Object.entries(record.usage)) {
    const c = modelCost(model, t, prices)
    if (c === null) return null
    sum += c
  }
  return sum
}

/** The rows of the chart: depth first, each parent followed by its children sorted by start. */
export function buildRows(
  records: AgentRecord[],
  agents: ListedAgent[],
  prices: Prices | null,
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
  const childCount = (id: string) =>
    agents.filter(a => (a.parentId ?? MAIN) === id).length

  const rows: Row[] = []
  const walk = (r: AgentRecord, depth: number) => {
    rows.push({
      id: r.id,
      depth,
      name: listed.get(r.id)?.name || r.name,
      repo: repoOf(r.cwd),
      start: r.start,
      end: r.end,
      tokens: Object.values(r.usage).reduce((n, t) => n + total(t), 0),
      cost: costOf(r, prices),
      childCount: childCount(r.id),
    })
    const sorted = [...(kids.get(r.id) ?? [])].sort((a, b) => a.start - b.start)
    for (const k of sorted) walk(k, depth + 1)
  }
  const main = records.find(r => r.id === MAIN)
  if (main) walk(main, 0)
  else for (const k of [...(kids.get(MAIN) ?? [])].sort((a, b) => a.start - b.start)) walk(k, 1)
  return rows
}

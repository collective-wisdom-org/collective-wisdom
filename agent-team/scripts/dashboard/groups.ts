export type Row = { id: string; title: string; risk: string; next: string }
export type Group = { name: string; count: number; rows: Row[] }

// The groups of chief-of-staff/status.md § Status layout, in that order.
// A queued stage lists its tickets by queuedAt: the order they will start.
const GROUPS: { name: string; stages: string[] }[] = [
  { name: 'Awaiting merge approval', stages: ['awaiting-merge'] },
  { name: 'Awaiting teammate review', stages: ['awaiting-review'] },
  { name: 'Merging', stages: ['merge'] },
  { name: 'Queued to merge', stages: ['merge-queued'] },
  { name: 'Speccing', stages: ['spec'] },
  { name: 'Awaiting build approval', stages: ['awaiting-build'] },
  { name: 'Building', stages: ['build'] },
  { name: 'Queued to build', stages: ['build-queued'] },
  { name: 'Other', stages: ['spec-queued', 'blocked'] },
]

const NO_RISK = 'not rated yet'

const text = (x: unknown): string => (typeof x === 'string' ? x : '')

function row(id: string, t: Record<string, unknown>): Row {
  const status = text(t.status)
  const at = status.indexOf('Risk:')
  const risk = at < 0 ? '' : status.slice(at + 5).trim()
  const next = (at < 0 ? status : status.slice(0, at)).trim().replace(/[\s;,.]+$/, '')
  return {
    id,
    title: text(t.title),
    risk: risk || NO_RISK,
    next,
  }
}

export function groupTickets(state: unknown): Group[] {
  try {
    const tickets = (state as { tickets?: unknown } | null)?.tickets
    if (typeof tickets !== 'object' || tickets === null || Array.isArray(tickets)) return []
    const all = Object.entries(tickets as Record<string, unknown>).filter(
      (e): e is [string, Record<string, unknown>] =>
        typeof e[1] === 'object' && e[1] !== null,
    )
    const groups: Group[] = []
    for (const { name, stages } of GROUPS) {
      const mine = all.filter(([, t]) => stages.includes(text(t.stage)))
      // Stage order first, then queuedAt (the start order of a queued stage);
      // the sort is stable, so ties keep state order.
      mine.sort(
        (a, b) =>
          stages.indexOf(text(a[1].stage)) - stages.indexOf(text(b[1].stage)) ||
          text(a[1].queuedAt).localeCompare(text(b[1].queuedAt)),
      )
      if (mine.length === 0) continue
      const rows = mine.map(([id, t]) => row(id, t))
      groups.push({ name, count: rows.length, rows })
    }
    return groups
  } catch {
    return []
  }
}

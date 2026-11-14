type Run = (args: string[]) => Promise<string>
export type Span = [number, number | null]

const REFRESH_MS = 60_000

/** The PR's last 100 commits with their check suites (first 20) and check runs (first 50). */
export const CI_QUERY = `query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){commits(last:100){nodes{commit{checkSuites(first:20){nodes{checkRuns(first:50){nodes{name startedAt completedAt}}}}}}}}}}`

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)
const nodes = (x: unknown): unknown[] => (isObj(x) && Array.isArray(x.nodes) ? x.nodes : [])
const time = (x: unknown): number | null => {
  const t = typeof x === 'string' ? Date.parse(x) : NaN
  return Number.isFinite(t) ? t : null
}

/** The `Required CI checks` row of project.md: `none` when the cell starts with `none`, else the backticked names (none listed when the row is missing or unset). */
export function requiredFromProject(markdown: string): { none: boolean; names: string[] } {
  const cell = markdown.split(/\r?\n/).filter((l) => /^\|\s*Required CI checks\b/.test(l))[0]?.split('|')[2]?.trim() ?? ''
  if (/^`?none\b/i.test(cell)) return { none: true, names: [] }
  if (cell.startsWith('TODO(')) return { none: false, names: [] }
  return { none: false, names: [...cell.matchAll(/`([^`]+)`/g)].flatMap((m) => m[1].split(',')).map((s) => s.trim()).filter(Boolean) }
}

/** Turns the `CI_QUERY` answer into one wait span per commit that ran a required check, sorted by start. Bad JSON, or no PR in it, gives null. */
export function ciWait(json: string, required: string[]): Span[] | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  const pr = isObj(data) && isObj(data.data) && isObj(data.data.repository) ? data.data.repository.pullRequest : null
  if (!isObj(pr)) return null
  const spans: Span[] = []
  for (const c of nodes(pr.commits)) {
    const commit = isObj(c) ? c.commit : null
    const runs = nodes(isObj(commit) ? commit.checkSuites : null).flatMap((s) => nodes(isObj(s) ? s.checkRuns : null)).filter(isObj)
    const counted = runs.filter((r) => required.length === 0 || required.includes(r.name as string))
    const starts = runs.map((r) => time(r.startedAt)).filter((t): t is number => t !== null)
    if (!counted.length || !starts.length) continue
    const ends = counted.map((r) => time(r.completedAt))
    spans.push([Math.min(...starts), ends.includes(null) ? null : Math.max(...(ends as number[]))])
  }
  return spans.sort((a, b) => a[0] - b[0])
}

export type CiWant = { id: string; pr: unknown; merged?: boolean }

/**
 * CI wait spans per PR, read from GitHub in the background, one read at a time. Keys are `<id>#<pr>`.
 * An open PR is read at most once a minute, a merged PR once. A failed read keeps the last spans and is retried after a minute. An entry no longer wanted is dropped after a minute.
 */
export function createCi(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  const entries = new Map<string, { pr: number; startedAt: number; merged: boolean; spans?: Span[]; ok: boolean }>()
  const queue: string[] = []
  const reading = new Set<Promise<void>>()
  let wanted = new Set<string>()

  async function drain(cfg: { slug: string; required?: string[] }) {
    const [owner, repo] = cfg.slug.split('/')
    for (let key = queue.shift(); key; key = queue.shift()) {
      const e = entries.get(key)
      if (!e) continue
      try {
        const out = await opts.run(['api', 'graphql', '-f', `query=${CI_QUERY}`, '-f', `o=${owner}`, '-f', `r=${repo}`, '-F', `n=${e.pr}`])
        const spans = ciWait(out, cfg.required ?? [])
        if (spans && entries.get(key) === e) Object.assign(e, { spans, ok: true })
      } catch {}
    }
  }

  return {
    want(wants: CiWant[], cfg: { slug: string; required?: string[] } | null) {
      wanted = new Set()
      const t = now()
      for (const w of cfg ? wants : []) {
        if (!Number.isInteger(w.pr) || (w.pr as number) <= 0) continue
        const key = `${w.id}#${w.pr}`
        wanted.add(key)
        const have = entries.get(key)
        if (have) have.merged ||= w.merged === true
        const due = !have || (!(have.merged && have.ok) && t - have.startedAt >= REFRESH_MS)
        if (!due || queue.includes(key)) continue
        entries.set(key, { pr: w.pr as number, startedAt: t, merged: have?.merged ?? w.merged === true, spans: have?.spans, ok: false })
        queue.push(key)
      }
      for (const [k, e] of entries) if (!wanted.has(k) && t - e.startedAt >= REFRESH_MS) entries.delete(k)
      if (cfg && queue.length && !reading.size) {
        const p: Promise<void> = drain(cfg).then(() => {
          reading.delete(p)
        })
        reading.add(p)
      }
    },
    get(): Record<string, Span[]> {
      const out: Record<string, Span[]> = {}
      for (const k of wanted) {
        const spans = entries.get(k)?.spans
        if (spans?.length) out[k] = spans
      }
      return out
    },
    idle: async () => {
      while (reading.size) await Promise.all([...reading])
    },
  }
}

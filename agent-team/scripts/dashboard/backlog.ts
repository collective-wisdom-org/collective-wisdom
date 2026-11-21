import { idForNumber, loginOf } from './titles.ts'
import type { TitleConfig } from './titles.ts'

type Run = (args: string[]) => Promise<string>
const PRIORITIES = ['urgent', 'high', 'medium', 'low'] as const
export type Priority = (typeof PRIORITIES)[number]
export type BacklogItem = { id: string; title: string; state: 'Todo' | 'Backlog'; priority: Priority | null; createdAt: number | null; owner?: string; readAt?: number }
type Ref = { id: string; title: string }
/** By ticket id: the open epic a ticket belongs to and its open blockers, for every open issue of the repo. */
export type Relations = Record<string, { epic?: Ref; blockedBy: Ref[] }>

const REFRESH_MS = 60_000
const RETRY_MS = 5 * 60 * 1000
const LIMIT = '200'
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g
const LOGIN = /^[A-Za-z0-9_.-]+$/
const TEAM_ROLES = ['triage', 'write', 'maintain', 'admin']

/** The page line for a failed read: the first line of the reason, control characters stripped, 120 characters. */
function failure(e: unknown): string {
  const text = e instanceof Error ? e.message : String(e)
  // execFile puts `Command failed: <path and arguments>` first; the reason is the next line.
  const line = text.split(/\r?\n/).map((l) => l.replace(BAD, ' ').trim()).find((l) => l && !l.startsWith('Command failed:')) ?? 'gh did not answer'
  return `Could not read Todo and Backlog from GitHub: ${line.slice(0, 120)}. Showing the last list read.`
}

const clean = (x: unknown): string => (typeof x === 'string' ? x : '').replace(BAD, ' ').trim().slice(0, 200)
const isNum = (x: unknown): x is number => typeof x === 'number' && Number.isInteger(x) && x >= 1
// `gh api --jq` prints one value per line when each is passed through `tojson`, across pages.
const jsonLines = (text: string): unknown[] => String(text).split(/\r?\n/).filter((l) => l.trim()).map((l) => JSON.parse(l))

/** The open Todo and Backlog tickets of a GitHub repo, in the tracker's order with their priority label and creation time, read once a minute in the background, and at once when `want` sees a new change stamp. Only issues by authors with triage or higher permission count; the last good list stays when a read fails, and `error()` says why until the next good read. Each good read also reads the relations of every open issue: an epic is left out of the list, and `relations()` says which epic and which open blockers a ticket has. A failed relations read keeps the known epics hidden, empties `relations()` and shows no error. */
export function createBacklog(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let cfg: TitleConfig | null = null
  let items: BacklogItem[] = []
  let readAt = -Infinity
  let busy: Promise<void> | null = null
  let again = false
  let stamp: string | null = null
  let error: string | null = null
  let relations: Relations = {}
  let epics = new Set<number>()
  // A login's answer: kept for good when it is a team role, for 5 minutes when not (a 404 and a failed call look alike).
  const trusted = new Map<string, { ok: boolean; at: number }>()

  async function isTeam(login: string, slug: string): Promise<boolean> {
    const known = trusted.get(login)
    if (known && (known.ok || now() - known.at < RETRY_MS)) return known.ok
    let ok = false
    try {
      ok = TEAM_ROLES.includes((await opts.run(['api', `repos/${slug}/collaborators/${login}/permission`, '--jq', '.role_name'])).trim())
    } catch {}
    trusted.set(login, { ok, at: now() })
    return ok
  }

  /** Epics, each child's epic and each ticket's open blockers, read with `gh api`. Throws when any call fails. */
  async function readRelations(c: TitleConfig): Promise<{ relations: Relations; epics: Set<number> }> {
    const api = (path: string, jq: string, paginate = true) => opts.run(['api', path, ...(paginate ? ['--paginate'] : []), '--jq', jq]).then(jsonLines)
    const rows = (await api(`repos/${c.slug}/issues?state=open&per_page=100`, '.[] | select(.pull_request == null) | {number, title, total: (.sub_issues_summary.total // 0), blocked: (.issue_dependencies_summary.blocked_by // 0)} | tojson')) as { number?: unknown; title?: unknown; total?: unknown; blocked?: unknown }[]
    const id = (n: number) => idForNumber(n, c.prefix, c.retired)
    const out: Relations = {}
    const epicNumbers = new Set<number>()
    for (const r of rows) if (isNum(r.number)) out[id(r.number)] = { blockedBy: [] }
    for (const r of rows) {
      if (!isNum(r.number) || !isNum(r.total)) continue
      epicNumbers.add(r.number)
      for (const child of (await api(`repos/${c.slug}/issues/${r.number}/sub_issues`, '[.[].number] | tojson')).flat()) {
        if (isNum(child) && out[id(child)]) out[id(child)].epic = { id: id(r.number), title: clean(r.title) }
      }
    }
    for (const r of rows) {
      if (!isNum(r.number) || !isNum(r.blocked)) continue
      const blockers = (await api(`repos/${c.slug}/issues/${r.number}/dependencies/blocked_by`, '.[] | {number, title, state, repository_url} | tojson', false)) as { number?: unknown; title?: unknown; state?: unknown; repository_url?: unknown }[]
      for (const b of blockers) {
        if (b.state !== 'open' || !isNum(b.number)) continue
        const repo = typeof b.repository_url === 'string' ? b.repository_url.match(/\/repos\/([^/]+\/[^/]+)$/)?.[1] : undefined
        const name = repo && repo.toLowerCase() !== c.slug.toLowerCase() ? `${repo}#${b.number}` : id(b.number)
        out[id(r.number)].blockedBy.push({ id: clean(name), title: clean(b.title) })
      }
    }
    return { relations: out, epics: epicNumbers }
  }

  async function read(c: TitleConfig) {
    try {
      const list: unknown = JSON.parse(await opts.run(['issue', 'list', '--repo', c.slug, '--state', 'open', '--limit', LIMIT, '--json', 'number,title,labels,author,createdAt']))
      if (!Array.isArray(list)) throw new Error('gh did not return a list')
      const next: { number: number; item: BacklogItem }[] = []
      for (const raw of list) {
        const { number, title, labels, author, createdAt } = (raw ?? {}) as { number?: unknown; title?: unknown; labels?: unknown; author?: { login?: unknown } | null; createdAt?: unknown }
        if (typeof number !== 'number' || !Number.isInteger(number) || number < 1 || !Array.isArray(labels)) continue
        const statuses = labels.map((l) => (l as { name?: unknown } | null)?.name).filter((n): n is string => typeof n === 'string' && n.startsWith('status:'))
        // No status label is Backlog; a Todo only when it is the sole status; any other state is not listed.
        const state = !statuses.length ? 'Backlog' : statuses.every((n) => n === 'status:todo') ? 'Todo' : null
        // The highest known `priority:` label wins; unknown values are ignored.
        const priority = PRIORITIES.find((p) => labels.some((l) => (l as { name?: unknown } | null)?.name === `priority:${p}`)) ?? null
        const created = typeof createdAt === 'string' ? Date.parse(createdAt) : NaN
        const login = author?.login
        if (!state || typeof login !== 'string' || !LOGIN.test(login) || !(await isTeam(login, c.slug))) continue
        const owner = loginOf(login)
        next.push({ number, item: { id: idForNumber(number, c.prefix, c.retired), title: clean(title), state, priority, createdAt: Number.isNaN(created) ? null : created, ...(owner ? { owner } : {}) } })
      }
      try {
        ;({ relations, epics } = await readRelations(c))
      } catch {
        relations = {}
      }
      items = next.filter((n) => !epics.has(n.number)).map((n) => n.item)
      error = null
    } catch (e) {
      error = failure(e)
    }
  }

  function start(c: TitleConfig) {
    readAt = now()
    busy = read(c).finally(() => {
      busy = null
      // The read that just ended may have started before the label changed.
      if (again && cfg) {
        again = false
        start(cfg)
      }
    })
  }

  return {
    /** `changed` is the Chief of Staff's change stamp. A stamp different from the last one seen reads at once. */
    want(c: TitleConfig | null, changed: string | null = null) {
      cfg = c
      const fresh = changed !== null && changed !== stamp
      if (changed !== null) stamp = changed
      if (!c) {
        again = false
        return
      }
      if (fresh && busy) again = true
      if (busy || (!fresh && now() - readAt < REFRESH_MS)) return
      start(c)
    },
    get: (): BacklogItem[] => (cfg ? items : []),
    relations: (): Relations => (cfg ? relations : {}),
    error: (): string | null => (cfg ? error : null),
    idle: async () => {
      while (busy) await busy
    },
  }
}

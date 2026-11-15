import { execFile } from 'node:child_process'
import { join } from 'node:path'

/** A prefix the project used before, and the issue number where it stopped: issues numbered below `below` keep it. Oldest first. */
export type Retired = { prefix: string; below: number }[]
export type TitleConfig = { prefix: string; slug: string; retired?: Retired }
type Run = (args: string[]) => Promise<string>

const RETRY_MS = 5 * 60 * 1000
const REFRESH_MS = 60_000
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g

const LOGIN_RULE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/

/** A GitHub login, or undefined for anything else (a missing author, a bot shown as `app/name`). */
export function loginOf(x: unknown): string | undefined {
  return typeof x === 'string' && LOGIN_RULE.test(x) ? x : undefined
}

export function prefixFromProject(markdown: string): string | null {
  const m = markdown.match(/^\|\s*Issue identifier prefix\b[^|]*\|\s*`([A-Za-z][A-Za-z0-9]*)`/m)
  return m ? m[1] : null
}

/** The `Retired issue prefixes` row as project_config.retired_prefixes reads it: one backticked `PREFIX<N,...` token, oldest first. Missing, `none` or empty gives none. A row that does not parse gives none too (the scripts stop on it; the dashboard must not), and so does one naming `current`. */
export function retiredFromProject(markdown: string, current: string | null = prefixFromProject(markdown)): Retired {
  const token = markdown.match(/^\|\s*Retired issue prefixes\b[^|]*\|[^`|]*`([^`]*)`/m)?.[1]?.trim() ?? ''
  if (token === '' || token.toLowerCase() === 'none') return []
  const out: Retired = []
  for (const part of token.split(',')) {
    const m = part.trim().match(/^([A-Z][A-Z0-9]*)<([0-9]+)$/)
    const below = m ? Number(m[2]) : NaN
    if (!m || !Number.isSafeInteger(below) || m[1] === current || out.some((r) => r.prefix === m[1]) || (out.length && below <= out[out.length - 1].below)) return []
    out.push({ prefix: m[1], below })
  }
  return out
}

/** The id of issue `number`, as project_config.ticket_id: the first retired pair whose `below` is above it gives its prefix, else the current one. */
export function idForNumber(number: number, prefix: string, retired: Retired = []): string {
  return `${retired.find((r) => number < r.below)?.prefix ?? prefix}-${number}`
}

/** The current prefix and the retired ones as one escaped alternation, longest first, for a regex. `lower` for branch names. */
export function prefixesPattern(prefix: string, retired: Retired = [], lower = false): string {
  const names = [prefix, ...retired.map((r) => r.prefix)].map((p) => (lower ? p.toLowerCase() : p)).sort((a, b) => b.length - a.length)
  return `(?:${names.join('|')})`
}

/** The ticket branch heads of the Branch pattern row, as project_config.branch_heads reads it: `{feat,infra}/<prefix>-N` gives feat/ and infra/. `feat/` alone when the row is missing or does not parse. */
export function headsFromProject(markdown: string): string[] {
  const pattern = markdown.match(/^\|\s*Branch pattern\b[^|]*\|\s*`([^`]*)`/m)?.[1] ?? ''
  const head = pattern.includes('<prefix>') ? pattern.split('<prefix>')[0] : ''
  const list = head.match(/^\{([a-z0-9-]+(?:,[a-z0-9-]+)*)\}\/$/)
  if (list) return list[1].split(',').map((name) => `${name}/`)
  return head && !/[{},]/.test(head) ? [head] : ['feat/']
}

/** The heads as one escaped regex group, e.g. `(?:feat/|infra/)`. */
export function headsPattern(heads: string[]): string {
  return `(?:${heads.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`
}

export function slugFromUrl(url: string): string | null {
  const m = url.match(/^https:\/\/github\.com\/([\w.-]+\/[\w.-]+)$/)
  return m ? m[1] : null
}

/** gh.sh sits next to the dashboard folder; cwd is the root checkout so it picks the repo's account. */
export function ghRunner(root: string): Run {
  const script = join(import.meta.dirname, '..', 'gh.sh')
  return (args) =>
    new Promise((resolve, reject) => {
      execFile(script, args, { cwd: root, timeout: 10_000, maxBuffer: 1 << 20 }, (err, out) => (err ? reject(err) : resolve(out)))
    })
}

/** Titles and issue authors read from the tracker for open tickets, read again once a minute. A failed read keeps the last good title and author. Reads run one at a time in the background. */
export function createTitles(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  const titles = new Map<string, string>()
  const owners = new Map<string, string>()
  const readAt = new Map<string, number>()
  const failedAt = new Map<string, number>()
  const queue: { id: string; cfg: TitleConfig }[] = []
  const queued = new Set<string>()
  let draining: Promise<void> | null = null

  async function drain() {
    for (let job = queue.shift(); job; job = queue.shift()) {
      try {
        const n = job.id.slice(job.id.indexOf('-') + 1)
        const issue = JSON.parse(await opts.run(['issue', 'view', n, '--repo', job.cfg.slug, '--json', 'title,author'])) as { title?: unknown; author?: { login?: unknown } | null }
        const title = (typeof issue.title === 'string' ? issue.title : '').replace(BAD, ' ').trim().slice(0, 200)
        if (title) {
          titles.set(job.id, title)
          const owner = loginOf(issue.author?.login)
          if (owner) owners.set(job.id, owner)
          else owners.delete(job.id)
          readAt.set(job.id, now())
          failedAt.delete(job.id)
        } else failedAt.set(job.id, now())
      } catch {
        failedAt.set(job.id, now())
      }
      queued.delete(job.id)
    }
    draining = null
  }

  return {
    want(ids: string[], cfg: TitleConfig | null) {
      if (!cfg) return
      const shape = new RegExp(`^${prefixesPattern(cfg.prefix, cfg.retired)}-\\d+$`)
      for (const id of ids) {
        const failed = failedAt.get(id)
        const read = readAt.get(id)
        if (!shape.test(id) || queued.has(id) || (failed !== undefined && now() - failed < RETRY_MS) || (read !== undefined && now() - read < REFRESH_MS)) continue
        queued.add(id)
        queue.push({ id, cfg })
      }
      if (queue.length && !draining) draining = drain()
    },
    get: (): Record<string, string> => Object.fromEntries(titles),
    owners: (): Record<string, string> => Object.fromEntries(owners),
    idle: async () => {
      while (draining) await draining
    },
  }
}

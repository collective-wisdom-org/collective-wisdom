import type { TitleConfig } from './titles.ts'

type Run = (args: string[]) => Promise<string>
const PRIORITIES = ['urgent', 'high', 'medium', 'low'] as const
export type Priority = (typeof PRIORITIES)[number]
export type BacklogItem = { id: string; title: string; state: 'Todo' | 'Backlog'; priority: Priority | null; createdAt: number | null }

const REFRESH_MS = 60_000
const RETRY_MS = 5 * 60 * 1000
const LIMIT = '200'
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g
const LOGIN = /^[A-Za-z0-9_.-]+$/
const TEAM_ROLES = ['triage', 'write', 'maintain', 'admin']

/** The open Todo and Backlog tickets of a GitHub repo, in the tracker's order with their priority label and creation time, read once a minute in the background. Only issues by authors with triage or higher permission count; the last good list stays when a read fails. */
export function createBacklog(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let cfg: TitleConfig | null = null
  let items: BacklogItem[] = []
  let readAt = -Infinity
  let busy: Promise<void> | null = null
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

  async function read(c: TitleConfig) {
    try {
      const list: unknown = JSON.parse(await opts.run(['issue', 'list', '--repo', c.slug, '--state', 'open', '--limit', LIMIT, '--json', 'number,title,labels,author,createdAt']))
      if (!Array.isArray(list)) return
      const next: BacklogItem[] = []
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
        next.push({ id: `${c.prefix}-${number}`, title: (typeof title === 'string' ? title : '').replace(BAD, ' ').trim().slice(0, 200), state, priority, createdAt: Number.isNaN(created) ? null : created })
      }
      items = next
    } catch {}
  }

  return {
    want(c: TitleConfig | null) {
      cfg = c
      if (!c || busy || now() - readAt < REFRESH_MS) return
      readAt = now()
      busy = read(c).finally(() => (busy = null))
    },
    get: (): BacklogItem[] => (cfg ? items : []),
    idle: async () => {
      while (busy) await busy
    },
  }
}

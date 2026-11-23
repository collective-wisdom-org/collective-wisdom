import type { Session } from './api.ts'
import type { Detail } from './details.ts'
import type { Spend } from './spend.ts'
import { headsPattern, idForNumber, loginOf, prefixesPattern } from './titles.ts'
import type { TitleConfig } from './titles.ts'

export type MergedConfig = TitleConfig & { issueUrls: boolean; issueUrl?: (id: string) => string | undefined; heads?: string[] }
/** `number` is the PR number, kept for the server's detail reads and left out of the api. */
export type MergedEntry = { id: string; title: string; prUrl: string; issueUrl?: string; mergedAt: number; owner?: string; number?: number; specUrl?: string; detail?: Detail; spend?: Spend; gantt?: Session[]; ci?: [number, number | null][] }
type Run = (args: string[]) => Promise<string>

const REFRESH_MS = 60_000
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g

/** Turns `gh pr list --json number,title,headRefName,mergedAt,url,author` output into entries (with their PR numbers), newest merge first. PRs with no ticket id are left out. */
export function parseMerged(json: string, cfg: MergedConfig): MergedEntry[] | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(data)) return null
  const { prefix, retired = [], slug, heads = ['feat/'] } = cfg
  const byBranch = new RegExp(`^${headsPattern(heads)}${prefixesPattern(prefix, retired, true)}-(\\d+)(?:-|$)`)
  const bySuffix = new RegExp(`\\s*\\(${prefixesPattern(prefix, retired)}-(\\d+)\\)$`)
  const out: MergedEntry[] = []
  for (const p of data) {
    if (typeof p !== 'object' || p === null) continue
    const { number, title, headRefName, mergedAt, url, author } = p as Record<string, unknown>
    const time = typeof mergedAt === 'string' ? Date.parse(mergedAt) : NaN
    if (!Number.isInteger(number) || !Number.isFinite(time)) continue
    const clean = (typeof title === 'string' ? title : '').replace(BAD, ' ').trim()
    const n = (typeof headRefName === 'string' ? headRefName.match(byBranch)?.[1] : undefined) ?? clean.match(bySuffix)?.[1]
    if (!n) continue
    const prUrl = typeof url === 'string' && url.startsWith(`https://github.com/${slug}/pull/`) ? url : `https://github.com/${slug}/pull/${number}`
    const entry: MergedEntry = { id: idForNumber(Number(n), prefix, retired), title: clean.replace(bySuffix, '').slice(0, 200), prUrl, mergedAt: time, number: number as number }
    const issueUrl = cfg.issueUrl ? cfg.issueUrl(entry.id) : cfg.issueUrls ? `https://github.com/${slug}/issues/${n}` : undefined
    if (issueUrl) entry.issueUrl = issueUrl
    const owner = loginOf((author as { login?: unknown } | null | undefined)?.login)
    if (owner) entry.owner = owner
    out.push(entry)
  }
  out.sort((a, b) => b.mergedAt - a.mergedAt || b.number! - a.number!)
  return out
}

/** Merged PRs read from GitHub in the background, at most once a minute. A failed read keeps the last good list. */
export function createMerged(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let list: MergedEntry[] = []
  let startedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read(cfg: MergedConfig) {
    try {
      const out = await opts.run(['pr', 'list', '--repo', cfg.slug, '--state', 'merged', '--limit', '200', '--json', 'number,title,headRefName,mergedAt,url,author'])
      list = parseMerged(out, cfg) ?? list
    } catch {}
    reading = null
  }

  return {
    want(cfg: MergedConfig | null) {
      if (!cfg || reading || now() - startedAt < REFRESH_MS) return
      startedAt = now()
      reading = read(cfg)
    },
    get: (): MergedEntry[] => list,
    idle: async () => {
      while (reading) await reading
    },
  }
}

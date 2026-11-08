import type { Session } from './api.ts'
import type { TitleConfig } from './titles.ts'

export type MergedConfig = TitleConfig & { issueUrls: boolean }
export type MergedEntry = { id: string; title: string; prUrl: string; issueUrl?: string; mergedAt: number; spend?: { cost: number | null; tokens: number }; gantt?: Session[] }
type Run = (args: string[]) => Promise<string>

const REFRESH_MS = 60_000
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g

/** Turns `gh pr list --json number,title,headRefName,mergedAt,url` output into entries, newest merge first. PRs with no ticket id are left out. */
export function parseMerged(json: string, cfg: MergedConfig): MergedEntry[] | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(data)) return null
  const { prefix, slug } = cfg
  const byBranch = new RegExp(`^feat/${prefix.toLowerCase()}-(\\d+)(?:-|$)`)
  const bySuffix = new RegExp(`\\s*\\(${prefix}-(\\d+)\\)$`)
  const out: (MergedEntry & { number: number })[] = []
  for (const p of data) {
    if (typeof p !== 'object' || p === null) continue
    const { number, title, headRefName, mergedAt, url } = p as Record<string, unknown>
    const time = typeof mergedAt === 'string' ? Date.parse(mergedAt) : NaN
    if (!Number.isInteger(number) || !Number.isFinite(time)) continue
    const clean = (typeof title === 'string' ? title : '').replace(BAD, ' ').trim()
    const n = (typeof headRefName === 'string' ? headRefName.match(byBranch)?.[1] : undefined) ?? clean.match(bySuffix)?.[1]
    if (!n) continue
    const prUrl = typeof url === 'string' && url.startsWith(`https://github.com/${slug}/pull/`) ? url : `https://github.com/${slug}/pull/${number}`
    const entry: MergedEntry & { number: number } = { id: `${prefix}-${n}`, title: clean.replace(bySuffix, '').slice(0, 200), prUrl, mergedAt: time, number: number as number }
    if (cfg.issueUrls) entry.issueUrl = `https://github.com/${slug}/issues/${n}`
    out.push(entry)
  }
  out.sort((a, b) => b.mergedAt - a.mergedAt || b.number - a.number)
  return out.map(({ number: _, ...e }) => e)
}

/** Merged PRs read from GitHub in the background, at most once a minute. A failed read keeps the last good list. */
export function createMerged(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let list: MergedEntry[] = []
  let startedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read(cfg: MergedConfig) {
    try {
      const out = await opts.run(['pr', 'list', '--repo', cfg.slug, '--state', 'merged', '--limit', '200', '--json', 'number,title,headRefName,mergedAt,url'])
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

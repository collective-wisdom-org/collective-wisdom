import { headsPattern } from './titles.ts'
import type { MergedConfig } from './merged.ts'

type Run = (args: string[]) => Promise<string>

const REFRESH_MS = 60_000

/** Turns `gh pr list --json number,headRefName` output into the open PR number by ticket id. Two PRs for one ticket: the higher number wins. */
export function parseOpen(json: string, cfg: Pick<MergedConfig, 'prefix' | 'heads'>): Record<string, number> | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(data)) return null
  const { prefix, heads = ['feat/'] } = cfg
  const byBranch = new RegExp(`^${headsPattern(heads)}${prefix.toLowerCase()}-(\\d+)(?:-|$)`)
  const out: Record<string, number> = {}
  for (const p of data) {
    if (typeof p !== 'object' || p === null) continue
    const { number, headRefName } = p as Record<string, unknown>
    const n = typeof headRefName === 'string' ? headRefName.match(byBranch)?.[1] : undefined
    if (!n || !Number.isInteger(number) || (number as number) < 1) continue
    const id = `${prefix}-${n}`
    if (!(id in out) || (number as number) > out[id]) out[id] = number as number
  }
  return out
}

/** Open PRs read from GitHub in the background, at most once a minute. A failed read keeps the last good map. */
export function createOpenPrs(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let map: Record<string, number> = {}
  let startedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read(cfg: MergedConfig) {
    try {
      const out = await opts.run(['pr', 'list', '--repo', cfg.slug, '--state', 'open', '--limit', '100', '--json', 'number,headRefName'])
      map = parseOpen(out, cfg) ?? map
    } catch {}
    reading = null
  }

  return {
    want(cfg: MergedConfig | null) {
      if (!cfg || reading || now() - startedAt < REFRESH_MS) return
      startedAt = now()
      reading = read(cfg)
    },
    get: (): Record<string, number> => map,
    idle: async () => {
      while (reading) await reading
    },
  }
}

import type { TitleConfig } from './titles.ts'

type Run = (args: string[]) => Promise<string>

const REFRESH_MS = 60_000

/** Turns `gh issue list --json number,updatedAt` output into `<prefix>-<number>` to epoch ms. Bad entries are dropped; bad JSON gives `{}`. */
export function parseUpdated(out: string, prefix: string): Record<string, number> {
  let data: unknown
  try {
    data = JSON.parse(out)
  } catch {
    return {}
  }
  const map: Record<string, number> = {}
  if (!Array.isArray(data)) return map
  for (const e of data) {
    if (typeof e !== 'object' || e === null) continue
    const { number, updatedAt } = e as Record<string, unknown>
    const time = typeof updatedAt === 'string' ? Date.parse(updatedAt) : NaN
    if (Number.isInteger(number) && Number.isFinite(time)) map[`${prefix}-${number}`] = time
  }
  return map
}

/** Issue update times read from GitHub in the background, at most once a minute. A failed read keeps the last good map. */
export function createUpdated(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let map: Record<string, number> = {}
  let startedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read(cfg: TitleConfig) {
    try {
      const out = await opts.run(['issue', 'list', '--repo', cfg.slug, '--state', 'all', '--limit', '100', '--search', 'sort:updated-desc', '--json', 'number,updatedAt'])
      const data: unknown = JSON.parse(out)
      if (Array.isArray(data)) map = parseUpdated(out, cfg.prefix)
    } catch {}
    reading = null
  }

  return {
    want(cfg: TitleConfig | null) {
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

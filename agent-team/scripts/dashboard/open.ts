import { headsPattern, idForNumber, loginOf, prefixesPattern } from './titles.ts'
import type { MergedConfig } from './merged.ts'

type Run = (args: string[]) => Promise<string>
export type OpenPr = { number: number; owner?: string }

const REFRESH_MS = 60_000

/** Turns `gh pr list --json number,headRefName,author` output into the open PR (number and author login) by ticket id. Two PRs for one ticket: the higher number wins, with its author. */
export function parseOpen(json: string, cfg: Pick<MergedConfig, 'prefix' | 'retired' | 'heads'>): Record<string, OpenPr> | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(data)) return null
  const { prefix, retired = [], heads = ['feat/'] } = cfg
  const byBranch = new RegExp(`^${headsPattern(heads)}${prefixesPattern(prefix, retired, true)}-(\\d+)(?:-|$)`)
  const out: Record<string, OpenPr> = {}
  for (const p of data) {
    if (typeof p !== 'object' || p === null) continue
    const { number, headRefName, author } = p as Record<string, unknown>
    const n = typeof headRefName === 'string' ? headRefName.match(byBranch)?.[1] : undefined
    if (!n || !Number.isInteger(number) || (number as number) < 1) continue
    const id = idForNumber(Number(n), prefix, retired)
    if (!(id in out) || (number as number) > out[id].number) {
      const owner = loginOf((author as { login?: unknown } | null | undefined)?.login)
      out[id] = owner ? { number: number as number, owner } : { number: number as number }
    }
  }
  return out
}

/** Open PRs read from GitHub in the background, at most once a minute. A failed read keeps the last good map. */
export function createOpenPrs(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let map: Record<string, OpenPr> = {}
  let startedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read(cfg: MergedConfig) {
    try {
      const out = await opts.run(['pr', 'list', '--repo', cfg.slug, '--state', 'open', '--limit', '100', '--json', 'number,headRefName,author'])
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
    get: (): Record<string, number> => Object.fromEntries(Object.entries(map).map(([id, p]) => [id, p.number])),
    owners: (): Record<string, string> => Object.fromEntries(Object.entries(map).flatMap(([id, p]) => (p.owner ? [[id, p.owner]] : []))),
    idle: async () => {
      while (reading) await reading
    },
  }
}

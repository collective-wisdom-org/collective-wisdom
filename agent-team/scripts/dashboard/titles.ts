import { execFile } from 'node:child_process'
import { join } from 'node:path'

export type TitleConfig = { prefix: string; slug: string }
type Run = (args: string[]) => Promise<string>

const RETRY_MS = 5 * 60 * 1000
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g

export function prefixFromProject(markdown: string): string | null {
  const m = markdown.match(/^\|\s*Issue identifier prefix\b[^|]*\|\s*`([A-Za-z][A-Za-z0-9]*)`/m)
  return m ? m[1] : null
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

/** Titles read from the tracker for rows whose state title is empty. Reads run one at a time in the background. */
export function createTitles(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  const titles = new Map<string, string>()
  const failedAt = new Map<string, number>()
  const queue: { id: string; cfg: TitleConfig }[] = []
  const queued = new Set<string>()
  let draining: Promise<void> | null = null

  async function drain() {
    for (let job = queue.shift(); job; job = queue.shift()) {
      try {
        const n = job.id.slice(job.cfg.prefix.length + 1)
        const out = await opts.run(['issue', 'view', n, '--repo', job.cfg.slug, '--json', 'title', '--jq', '.title'])
        const title = out.replace(BAD, ' ').trim().slice(0, 200)
        if (title) titles.set(job.id, title)
        else failedAt.set(job.id, now())
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
      const shape = new RegExp(`^${cfg.prefix}-\\d+$`)
      for (const id of ids) {
        const failed = failedAt.get(id)
        if (!shape.test(id) || titles.has(id) || queued.has(id) || (failed !== undefined && now() - failed < RETRY_MS)) continue
        queued.add(id)
        queue.push({ id, cfg })
      }
      if (queue.length && !draining) draining = drain()
    },
    get: (): Record<string, string> => Object.fromEntries(titles),
    idle: async () => {
      while (draining) await draining
    },
  }
}

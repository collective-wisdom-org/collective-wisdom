import { createServer } from 'node:http'
import type { Server } from 'node:http'
import { lstatSync, readFileSync, readdirSync, realpathSync } from 'node:fs'
import { execFile } from 'node:child_process'
import { join } from 'node:path'
import { buildApi, parseWorktrees, repoUrlFromProject } from './api.ts'
import type { Worktree } from './api.ts'
import { createTitles, ghRunner, prefixFromProject, slugFromUrl } from './titles.ts'
import type { TitleConfig } from './titles.ts'
import { createMerged } from './merged.ts'
import type { MergedConfig } from './merged.ts'

const PAGES: Record<string, [string, string]> = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/app.js': ['app.js', 'text/javascript; charset=utf-8'],
}

/** Reads a file only when it is a regular file and every folder in `dirs` is a real folder (no links). */
export function readRegular(file: string, dirs: string[]): string | undefined {
  try {
    for (const d of dirs) if (!lstatSync(d).isDirectory()) return undefined
    if (!lstatSync(file).isFile()) return undefined
    return readFileSync(file, 'utf8')
  } catch {
    return undefined
  }
}

function readJson(file: string, dirs: string[]): unknown {
  try {
    const text = readRegular(file, dirs)
    return text === undefined ? undefined : JSON.parse(text)
  } catch {
    return undefined
  }
}

export async function startServer(opts: { root: string; port: number }): Promise<{ port: number; close(): Promise<void> }> {
  const { root } = opts
  const agentDir = join(root, '.agent-team')
  let lastState: unknown = null
  const trackerTitles = createTitles({ run: ghRunner(root) })
  const merged = createMerged({ run: ghRunner(root) })

  // Worktree list for matching sessions to tickets: read once at start, then refreshed in the background, cached 30s, last good list kept.
  let worktrees: Worktree[] = []
  let worktreesAt = 0
  let worktreesBusy = false
  const refreshWorktrees = (): Promise<void> => {
    if (worktreesBusy || Date.now() - worktreesAt < 30_000) return Promise.resolve()
    worktreesBusy = true
    worktreesAt = Date.now()
    return new Promise((resolve) => {
      const done = (out?: string) => {
        worktreesBusy = false
        if (out !== undefined) worktrees = parseWorktrees(out)
        resolve()
      }
      try {
        execFile('git', ['-C', root, 'worktree', 'list', '--porcelain'], { timeout: 5000 }, (err, out) => done(err ? undefined : out))
      } catch {
        done()
      }
    })
  }

  // The first read finishes before the server answers, so the first /api already has the list.
  await refreshWorktrees()

  const api = () => {
    const state = readJson(join(agentDir, 'state.json'), [agentDir])
    if (state !== undefined) lastState = state
    const snapshots: unknown[] = []
    try {
      const dir = join(agentDir, 'gantt')
      if (lstatSync(agentDir).isDirectory() && lstatSync(dir).isDirectory()) {
        for (const f of readdirSync(dir)) {
          if (!f.endsWith('.json')) continue
          const s = readJson(join(dir, f), [agentDir, dir])
          if (s !== undefined) snapshots.push(s)
        }
      }
    } catch {}
    const dash = readJson(join(agentDir, 'dashboard.json'), [agentDir])
    const envId = (dash as { environmentId?: unknown } | undefined)?.environmentId
    let repo = null
    let titleCfg: TitleConfig | null = null
    let mergedCfg: MergedConfig | null = null
    let prefix: string | null = null
    try {
      const text = readRegular(join(root, 'docs/agents/project.md'), [join(root, 'docs'), join(root, 'docs/agents')])
      if (text !== undefined) {
        repo = repoUrlFromProject(text)
        prefix = prefixFromProject(text)
        const slug = repo ? slugFromUrl(repo.url) : null
        if (prefix && slug && repo) {
          mergedCfg = { prefix, slug, issueUrls: repo.isGithubIssues }
          if (repo.isGithubIssues) titleCfg = { prefix, slug }
        }
      }
    } catch {}
    const tickets = (lastState as { tickets?: unknown } | null)?.tickets
    if (typeof tickets === 'object' && tickets !== null && !Array.isArray(tickets)) {
      const blank = Object.entries(tickets).filter(([, t]) => {
        const title = (t as { title?: unknown } | null)?.title
        return !(typeof title === 'string' && title)
      }).map(([id]) => id)
      trackerTitles.want(blank, titleCfg)
    }
    merged.want(mergedCfg)
    void refreshWorktrees()
    return buildApi({ state: lastState, snapshots, repo, titles: trackerTitles.get(), environmentId: typeof envId === 'string' ? envId : null, now: Date.now(), worktrees, prefix, merged: merged.get() })
  }

  const server: Server = createServer({ requireHostHeader: false }, (req, res) => {
    const send = (status: number, body: string, type = 'text/plain; charset=utf-8') => {
      const headers: Record<string, string> = { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }
      if (path === '/') headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
      res.writeHead(status, headers)
      res.end(body)
    }
    const path = (req.url ?? '/').split('?')[0]
    const port = (server.address() as { port: number }).port
    const host = req.headers.host
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return send(403, 'forbidden')
    if (req.method !== 'GET') return send(405, 'method not allowed')
    try {
      if (path === '/health') return send(200, JSON.stringify({ ok: true, root }), 'application/json')
      if (path === '/api') return send(200, JSON.stringify(api()), 'application/json')
      const page = Object.hasOwn(PAGES, path) ? PAGES[path] : undefined
      if (page) {
        try {
          return send(200, readFileSync(join(import.meta.dirname, 'page', page[0]), 'utf8'), page[1])
        } catch {
          return send(404, 'not found')
        }
      }
      return send(404, 'not found')
    } catch {
      return send(500, 'error')
    }
  })

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(opts.port, '127.0.0.1', resolve)
  })
  const bound = (server.address() as { port: number }).port
  return {
    port: bound,
    close: () =>
      new Promise<void>((resolve) => {
        server.close(() => resolve())
        server.closeAllConnections()
      }),
  }
}

const isMain = (() => {
  try {
    return !!process.argv[1] && realpathSync(process.argv[1]) === import.meta.filename
  } catch {
    return false
  }
})()

if (isMain) {
  const arg = (n: string) => {
    const i = process.argv.indexOf(n)
    return i >= 0 ? process.argv[i + 1] : undefined
  }
  const root = arg('--root')
  const port = Number(arg('--port') ?? 0)
  if (!root || !Number.isInteger(port)) {
    console.error('usage: node server.ts --root <dir> --port <n>')
    process.exit(2)
  }
  const s = await startServer({ root, port })
  console.log(`dashboard listening on 127.0.0.1:${s.port}`)
}

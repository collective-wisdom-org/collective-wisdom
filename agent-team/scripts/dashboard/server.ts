import { createHash } from 'node:crypto'
import { createServer } from 'node:http'
import type { Server } from 'node:http'
import { lstatSync, readFileSync, readdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { execFile } from 'node:child_process'
import { join } from 'node:path'
import { buildApi, ledgerSessions, parseWorktrees, repoUrlFromProject } from './api.ts'
import type { Worktree } from './api.ts'
import { createTitles, ghRunner, prefixFromProject, slugFromUrl } from './titles.ts'
import type { TitleConfig } from './titles.ts'
import { createUpdated } from './updated.ts'
import { createMerged } from './merged.ts'
import { createDetails, gitRunner } from './details.ts'
import type { DetailWant } from './details.ts'
import type { MergedConfig } from './merged.ts'
import { backup } from './backup.ts'
import { parseLedger, recordSpend, spendByTicket } from './spend.ts'
import { historyByTicket, parseHistory, recordHistory } from './history.ts'

const PAGES: Record<string, [string, string]> = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/app.js': ['app.js', 'text/javascript; charset=utf-8'],
}

/** A short hash of the page files, in `PAGES` order, so an open page can tell its files changed. `null` when any file can't be read. */
export function pageVersion(dir: string): string | null {
  try {
    const hash = createHash('sha256')
    for (const [file] of Object.values(PAGES)) hash.update(readFileSync(join(dir, file))).update('\0')
    return hash.digest('hex').slice(0, 16)
  } catch {
    return null
  }
}

/** True when a dashboard for `root` answers on `port`. */
export async function healthy(port: number, root: string): Promise<boolean> {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(500) })
    if (!res.ok) return false
    const body = (await res.json()) as { ok?: unknown; root?: unknown }
    return body.ok === true && body.root === root
  } catch {
    return false
  }
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

/** Writes a file of `.agent-team` through a temp file and a rename. Nothing is written unless `.agent-team` is a real folder and the file is absent or a regular file. */
function writeJson(agentDir: string, name: string, text: string): boolean {
  const file = join(agentDir, name)
  const tmp = join(agentDir, `${name}.${process.pid}.tmp`)
  try {
    if (!lstatSync(agentDir).isDirectory()) return false
    try {
      if (!lstatSync(file).isFile()) return false
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') return false
    }
    writeFileSync(tmp, text, { flag: 'wx' })
    renameSync(tmp, file)
    return true
  } catch {
    try {
      unlinkSync(tmp)
    } catch {}
    return false
  }
}

export async function startServer(opts: { root: string; port: number }): Promise<{ port: number; close(): Promise<void> }> {
  const { root } = opts
  const agentDir = join(root, '.agent-team')
  let lastState: unknown = null
  const trackerTitles = createTitles({ run: ghRunner(root) })
  const merged = createMerged({ run: ghRunner(root) })
  const updated = createUpdated({ run: ghRunner(root) })
  const details = createDetails({ run: ghRunner(root), git: gitRunner(root) })

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

  const projectText = () => readRegular(join(root, 'docs/agents/project.md'), [join(root, 'docs'), join(root, 'docs/agents')])

  const readState = (): unknown => {
    const state = readJson(join(agentDir, 'state.json'), [agentDir])
    if (state !== undefined) lastState = state
    return lastState
  }

  const readSnapshots = (): unknown[] => {
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
    return snapshots
  }

  // The spend ledger and the gantt history: loaded at start, updated every 30 seconds whether or not the page polls, each rewritten only when it changed.
  let ledger = parseLedger(readRegular(join(agentDir, 'spend.json'), [agentDir]) ?? '')
  let history = parseHistory(readRegular(join(agentDir, 'gantt-history.json'), [agentDir]) ?? '')
  const written: Record<string, string> = { 'spend.json': JSON.stringify(ledger), 'gantt-history.json': JSON.stringify(history) }
  const save = (name: string, value: unknown) => {
    try {
      const next = JSON.stringify(value)
      if (next !== written[name] && writeJson(agentDir, name, next)) written[name] = next
    } catch {}
  }
  const recordRound = () => {
    let matched: ReturnType<typeof ledgerSessions> = []
    try {
      const text = projectText()
      void refreshWorktrees()
      matched = ledgerSessions({ snapshots: readSnapshots(), worktrees, state: readState(), prefix: text === undefined ? null : prefixFromProject(text), now: Date.now() })
    } catch {}
    try {
      ledger = recordSpend(ledger, matched)
    } catch {}
    try {
      history = recordHistory(history, matched)
    } catch {}
    save('spend.json', ledger)
    save('gantt-history.json', history)
  }
  recordRound()
  const spendTimer = setInterval(recordRound, 30_000)
  spendTimer.unref()

  // A backup of the ledger, the history and the state once a day, for a dashboard that runs for days; a failure is ignored.
  const backupTimer = setInterval(() => {
    try {
      backup({ root, now: new Date() })
    } catch {}
  }, 24 * 3600 * 1000)
  backupTimer.unref()

  const api = () => {
    readState()
    const snapshots = readSnapshots()
    const dash = readJson(join(agentDir, 'dashboard.json'), [agentDir])
    const envId = (dash as { environmentId?: unknown } | undefined)?.environmentId
    let repo = null
    let titleCfg: TitleConfig | null = null
    let mergedCfg: MergedConfig | null = null
    let prefix: string | null = null
    try {
      const text = projectText()
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
    const wants: DetailWant[] = []
    if (typeof tickets === 'object' && tickets !== null && !Array.isArray(tickets)) {
      const blank = Object.entries(tickets).filter(([, t]) => {
        const title = (t as { title?: unknown } | null)?.title
        return !(typeof title === 'string' && title)
      }).map(([id]) => id)
      trackerTitles.want(blank, titleCfg)
      for (const [id, t] of Object.entries(tickets)) {
        const { stage, specPath, specSha, pr } = (t ?? {}) as Record<string, unknown>
        if (stage === 'awaiting-build' || stage === 'awaiting-merge') wants.push({ id, stage, specPath, specSha, pr })
      }
    }
    details.want(wants, mergedCfg)
    merged.want(mergedCfg)
    updated.want(titleCfg)
    void refreshWorktrees()
    return buildApi({ state: lastState, snapshots, repo, titles: trackerTitles.get(), environmentId: typeof envId === 'string' ? envId : null, now: Date.now(), worktrees, prefix, merged: merged.get(), updated: updated.get(), spend: spendByTicket(ledger), history: historyByTicket(history), details: details.get() })
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
      if (path === '/api') return send(200, JSON.stringify({ ...api(), version: pageVersion(join(import.meta.dirname, 'page')) }), 'application/json')
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
        clearInterval(spendTimer)
        clearInterval(backupTimer)
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

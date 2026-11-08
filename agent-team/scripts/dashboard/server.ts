import { createServer } from 'node:http'
import type { Server } from 'node:http'
import { lstatSync, readFileSync, readdirSync, realpathSync } from 'node:fs'
import { join } from 'node:path'
import { buildApi, repoUrlFromProject } from './api.ts'

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
    try {
      const text = readRegular(join(root, 'docs/agents/project.md'), [join(root, 'docs'), join(root, 'docs/agents')])
      if (text !== undefined) repo = repoUrlFromProject(text)
    } catch {}
    return buildApi({ state: lastState, snapshots, repo, environmentId: typeof envId === 'string' ? envId : null, now: Date.now() })
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

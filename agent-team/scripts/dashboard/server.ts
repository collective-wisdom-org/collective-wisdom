import { createServer } from 'node:http'
import type { Server } from 'node:http'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { buildApi, repoUrlFromProject } from './api.ts'

const PAGES: Record<string, [string, string]> = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/app.js': ['app.js', 'text/javascript; charset=utf-8'],
}

function readJson(file: string): unknown {
  try {
    return JSON.parse(readFileSync(file, 'utf8'))
  } catch {
    return undefined
  }
}

export async function startServer(opts: { root: string; port: number }): Promise<{ port: number; close(): Promise<void> }> {
  const { root } = opts
  const agentDir = join(root, '.agent-team')
  let lastState: unknown = null

  const api = () => {
    const state = readJson(join(agentDir, 'state.json'))
    if (state !== undefined) lastState = state
    const snapshots: unknown[] = []
    try {
      for (const f of readdirSync(join(agentDir, 'gantt'))) {
        if (!f.endsWith('.json')) continue
        const s = readJson(join(agentDir, 'gantt', f))
        if (s !== undefined) snapshots.push(s)
      }
    } catch {}
    const dash = readJson(join(agentDir, 'dashboard.json'))
    const envId = (dash as { environmentId?: unknown } | undefined)?.environmentId
    let repo = null
    try {
      repo = repoUrlFromProject(readFileSync(join(root, 'docs/agents/project.md'), 'utf8'))
    } catch {}
    return buildApi({ state: lastState, snapshots, repo, environmentId: typeof envId === 'string' ? envId : null, now: Date.now() })
  }

  const server: Server = createServer({ requireHostHeader: false }, (req, res) => {
    const send = (status: number, body: string, type = 'text/plain; charset=utf-8') => {
      res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' })
      res.end(body)
    }
    const port = (server.address() as { port: number }).port
    const host = req.headers.host
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return send(403, 'forbidden')
    if (req.method !== 'GET') return send(405, 'method not allowed')
    const path = (req.url ?? '/').split('?')[0]
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

if (process.argv[1] === import.meta.filename) {
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

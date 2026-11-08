import { test } from 'node:test'
import assert from 'node:assert/strict'
import { request } from 'node:http'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'
import { startServer } from './server.ts'

function tmpRoot(): string {
  return mkdtempSync(join(tmpdir(), 'dash-'))
}

function call(port: number, method: string, path: string, host?: string): Promise<{ status: number; body: string; headers: Record<string, unknown> }> {
  return new Promise((resolve, reject) => {
    const headers: Record<string, string> = host === undefined ? {} : { Host: host }
    const req = request({ host: '127.0.0.1', port, method, path, headers, setHost: host !== undefined }, (res) => {
      let body = ''
      res.on('data', (c) => (body += c))
      res.on('end', () => resolve({ status: res.statusCode ?? 0, body, headers: res.headers }))
    })
    req.on('error', reject)
    req.end()
  })
}

const goodSnap = { sessionId: 'good', cwd: '/x', updatedAt: Date.now(), total: null, rows: [] }
const outsideDirs: string[] = []
const goodState = { tickets: { 'CW-1': { title: 'one', stage: 'build', status: 'coding' } } }

test('host check', async () => {
  const root = tmpRoot()
  const srv = await startServer({ root, port: 0 })
  try {
    const p = srv.port
    const cases: [string | undefined, number][] = [
      [`127.0.0.1:${p}`, 200],
      [`localhost:${p}`, 200],
      ['evil.example', 403],
      ['127.0.0.1:1', 403],
      [undefined, 403],
    ]
    for (const route of ['/api', '/health']) {
      for (const [host, want] of cases) {
        const r = await call(p, 'GET', route, host)
        assert.equal(r.status, want, `${route} Host=${host}`)
      }
    }
  } finally {
    await srv.close()
    rmSync(root, { recursive: true, force: true })
  }
})

test('method and routes', async () => {
  const root = tmpRoot()
  const srv = await startServer({ root, port: 0 })
  try {
    const host = `127.0.0.1:${srv.port}`
    assert.equal((await call(srv.port, 'POST', '/api', host)).status, 405)
    assert.equal((await call(srv.port, 'GET', '/nope', host)).status, 404)
    const h = await call(srv.port, 'GET', '/health', host)
    assert.deepEqual(JSON.parse(h.body), { ok: true, root })
    assert.equal(h.headers['x-content-type-options'], 'nosniff')
    assert.match(String((await call(srv.port, 'GET', '/', host)).headers['content-security-policy']), /default-src 'self'/)
  } finally {
    await srv.close()
    rmSync(root, { recursive: true, force: true })
  }
})

test('degraded inputs still answer', async () => {
  const cases: { name: string; setup: (root: string) => void; sessions: string[]; status?: number }[] = [
    { name: 'no .agent-team', setup: () => {}, sessions: [] },
    {
      name: 'half-written state',
      setup: (r) => {
        mkdirSync(join(r, '.agent-team'))
        writeFileSync(join(r, '.agent-team/state.json'), '{"tickets":')
      },
      sessions: [],
    },
    {
      name: 'bad and good snapshots',
      setup: (r) => {
        mkdirSync(join(r, '.agent-team/gantt'), { recursive: true })
        writeFileSync(join(r, '.agent-team/gantt/bad.json'), '{"rows":')
        writeFileSync(join(r, '.agent-team/gantt/good.json'), JSON.stringify(goodSnap))
      },
      sessions: ['good'],
    },
    {
      name: 'symlinked gantt folder',
      setup: (r) => {
        const outside = tmpRoot()
        outsideDirs.push(outside)
        writeFileSync(join(outside, 'good.json'), JSON.stringify(goodSnap))
        mkdirSync(join(r, '.agent-team'))
        symlinkSync(outside, join(r, '.agent-team/gantt'))
      },
      sessions: [],
    },
    {
      name: 'symlinked state.json',
      setup: (r) => {
        const outside = tmpRoot()
        outsideDirs.push(outside)
        writeFileSync(join(outside, 'state.json'), JSON.stringify(goodState))
        mkdirSync(join(r, '.agent-team'))
        symlinkSync(join(outside, 'state.json'), join(r, '.agent-team/state.json'))
      },
      sessions: [],
      status: 0,
    },
  ]
  for (const c of cases) {
    const root = tmpRoot()
    c.setup(root)
    const srv = await startServer({ root, port: 0 })
    try {
      const r = await call(srv.port, 'GET', '/api', `127.0.0.1:${srv.port}`)
      assert.equal(r.status, 200, c.name)
      const api = JSON.parse(r.body)
      assert.deepEqual(api.gantt.map((g: { sessionId: string }) => g.sessionId), c.sessions, c.name)
      if (c.status !== undefined) assert.equal(api.status.length, c.status, c.name)
    } finally {
      await srv.close()
      rmSync(root, { recursive: true, force: true })
      for (const d of outsideDirs.splice(0)) rmSync(d, { recursive: true, force: true })
    }
  }
})

test('keeps last good state when state.json is half-written', async () => {
  const root = tmpRoot()
  mkdirSync(join(root, '.agent-team'))
  writeFileSync(join(root, '.agent-team/state.json'), JSON.stringify(goodState))
  const srv = await startServer({ root, port: 0 })
  try {
    const host = `127.0.0.1:${srv.port}`
    const first = JSON.parse((await call(srv.port, 'GET', '/api', host)).body)
    assert.ok(first.status.length > 0)
    writeFileSync(join(root, '.agent-team/state.json'), '{"tickets":')
    const second = JSON.parse((await call(srv.port, 'GET', '/api', host)).body)
    assert.deepEqual(second.status, first.status)
  } finally {
    await srv.close()
    rmSync(root, { recursive: true, force: true })
  }
})

test('CLI starts through a symlinked directory', async () => {
  const root = tmpRoot()
  const link = join(tmpRoot(), 'dashboard-link')
  symlinkSync(import.meta.dirname, link)
  const port = await new Promise<number>((resolve, reject) => {
    const s = createServer()
    s.once('error', reject)
    s.listen(0, '127.0.0.1', () => {
      const p = (s.address() as { port: number }).port
      s.close(() => resolve(p))
    })
  })
  const child = spawn(process.execPath, [join(link, 'server.ts'), '--root', root, '--port', String(port)], { stdio: 'ignore' })
  try {
    let body = ''
    for (let i = 0; i < 30 && !body; i++) {
      await sleep(100)
      try {
        const r = await call(port, 'GET', '/health', `127.0.0.1:${port}`)
        if (r.status === 200) body = r.body
      } catch {}
    }
    assert.deepEqual(JSON.parse(body || 'null'), { ok: true, root })
  } finally {
    child.kill()
    rmSync(root, { recursive: true, force: true })
  }
})

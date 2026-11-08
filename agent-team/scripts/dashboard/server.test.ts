import { test } from 'node:test'
import assert from 'node:assert/strict'
import { request } from 'node:http'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync, realpathSync, readFileSync, readdirSync, existsSync } from 'node:fs'
import { execFileSync, spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'
import { codeFiles, codeVersion, mergedPageOf, pageVersion, restartWatch, startServer } from './server.ts'

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

/** A git repo under a `.worktrees` folder, so snapshots at its root count as a worktree session and match a card on branch main. */
function wtRoot(): string {
  const root = join(realpathSync(mkdtempSync(join(tmpdir(), 'dash-'))), '.worktrees', 'dash')
  mkdirSync(root, { recursive: true })
  execFileSync('git', ['init', '-q', '-b', 'main', root])
  return root
}

const sessionIds = (api: any): string[] =>
  api.status.flatMap((g: any) => g.rows).flatMap((row: any) => row.gantt ?? []).map((s: { sessionId: string }) => s.sessionId)

const goodSnap = { sessionId: 'good', cwd: '', updatedAt: Date.now(), total: null, rows: [] }
const outsideDirs: string[] = []
const goodState = { tickets: { 'CW-1': { title: 'one', stage: 'build', status: 'coding', branch: 'main' } } }

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

test('page version changes with either page file and is null when one is missing', () => {
  const dir = tmpRoot()
  try {
    writeFileSync(join(dir, 'index.html'), 'a')
    writeFileSync(join(dir, 'app.js'), 'b')
    const base = pageVersion(dir)
    assert.match(String(base), /^[0-9a-f]{16}$/)
    assert.equal(pageVersion(dir), base)
    writeFileSync(join(dir, 'app.js'), 'c')
    const js = pageVersion(dir)
    writeFileSync(join(dir, 'index.html'), 'd')
    const html = pageVersion(dir)
    assert.equal(new Set([base, js, html]).size, 3)
    rmSync(join(dir, 'app.js'))
    assert.equal(pageVersion(dir), null)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test('/api carries the version of the served page files', async () => {
  const root = tmpRoot()
  const srv = await startServer({ root, port: 0 })
  try {
    const body = JSON.parse((await call(srv.port, 'GET', '/api', `127.0.0.1:${srv.port}`)).body)
    assert.equal(body.version, pageVersion(join(import.meta.dirname, 'page')))
    assert.ok(body.version)
  } finally {
    await srv.close()
    rmSync(root, { recursive: true, force: true })
  }
})

test('mergedPage: an integer from 0 to 19, anything else reads as 0', () => {
  const cases: [string, number][] = [['/api', 0], ['/api?mergedPage=2', 2], ['/api?mergedPage=19', 19], ['/api?mergedPage=20', 0], ['/api?mergedPage=99', 0], ['/api?mergedPage=-1', 0], ['/api?mergedPage=abc', 0], ['/api?mergedPage=1.5', 0], ['/api?mergedPage=', 0], ['/api?mergedPage=3&mergedPage=4', 3]]
  for (const [url, want] of cases) assert.equal(mergedPageOf(url), want, url)
})

test('method and routes', async () => {
  const root = tmpRoot()
  const srv = await startServer({ root, port: 0 })
  try {
    const host = `127.0.0.1:${srv.port}`
    assert.equal((await call(srv.port, 'POST', '/api', host)).status, 405)
    assert.equal((await call(srv.port, 'GET', '/nope', host)).status, 404)
    const h = await call(srv.port, 'GET', '/health', host)
    assert.deepEqual(JSON.parse(h.body), { ok: true, root, code: codeVersion(codeFiles(join(import.meta.dirname, 'server.ts'))), pid: process.pid })
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
        writeFileSync(join(r, '.agent-team/state.json'), JSON.stringify(goodState))
        writeFileSync(join(r, '.agent-team/gantt/good.json'), JSON.stringify({ ...goodSnap, cwd: r }))
      },
      sessions: ['good'],
    },
    {
      name: 'symlinked gantt folder',
      setup: (r) => {
        const outside = tmpRoot()
        outsideDirs.push(outside)
        writeFileSync(join(outside, 'good.json'), JSON.stringify({ ...goodSnap, cwd: r }))
        mkdirSync(join(r, '.agent-team'))
        writeFileSync(join(r, '.agent-team/state.json'), JSON.stringify(goodState))
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
    const root = wtRoot()
    c.setup(root)
    const srv = await startServer({ root, port: 0 })
    try {
      const r = await call(srv.port, 'GET', '/api', `127.0.0.1:${srv.port}`)
      assert.equal(r.status, 200, c.name)
      const api = JSON.parse(r.body)
      const got = sessionIds(api)
      assert.deepEqual(got, c.sessions, c.name)
      assert.ok(!('gantt' in api), c.name)
      assert.deepEqual(api.merged, [], c.name)
      if (c.status !== undefined) assert.equal(api.status.length, c.status, c.name)
    } finally {
      await srv.close()
      rmSync(join(root, '..', '..'), { recursive: true, force: true })
      for (const d of outsideDirs.splice(0)) rmSync(d, { recursive: true, force: true })
    }
  }
})

test('records spend in the background and writes nothing through a link', async () => {
  const cases: { name: string; link: boolean }[] = [{ name: 'real folder', link: false }, { name: '.agent-team is a link', link: true }]
  for (const c of cases) {
    const root = wtRoot()
    const outside = tmpRoot()
    const agent = join(root, '.agent-team')
    if (c.link) symlinkSync(outside, agent)
    else mkdirSync(agent)
    mkdirSync(join(agent, 'gantt'))
    writeFileSync(join(agent, 'state.json'), JSON.stringify(goodState))
    const rows = [{ id: 'main', depth: 0, name: 'm', repo: 'r', start: 1, end: 2, tokens: 40, cost: 0.5, kind: 'session' }, { id: 't', depth: 1, name: 't', repo: 'r', start: 1, end: 2, tokens: 99, cost: 0.1, kind: 'task' }]
    writeFileSync(join(agent, 'gantt/a.json'), JSON.stringify({ ...goodSnap, sessionId: 'a', cwd: root, total: 0.5, rows }))
    let srv = await startServer({ root, port: 0 })
    try {
      const file = join(outside, 'spend.json')
      if (c.link) {
        assert.ok(!existsSync(file), c.name)
        assert.deepEqual(readdirSync(outside).sort(), ['gantt', 'state.json'], c.name)
        assert.ok(!existsSync(join(outside, 'gantt-history.json')), c.name)
      } else {
        const ledger = JSON.parse(readFileSync(join(agent, 'spend.json'), 'utf8'))
        assert.deepEqual(ledger.sessions.a, { ticket: 'CW-1', cost: 0.5, tokens: 40, updatedAt: goodSnap.updatedAt })
        assert.deepEqual(readdirSync(agent).sort(), ['gantt', 'gantt-history.json', 'spend.json', 'state.json'], c.name)
        const history = JSON.parse(readFileSync(join(agent, 'gantt-history.json'), 'utf8'))
        assert.equal(history.sessions.a.ticket, 'CW-1')
        assert.equal(history.sessions.a.session.rows[0].tokens, 40)
        await srv.close()
        rmSync(join(agent, 'gantt/a.json'))
        writeFileSync(join(agent, 'gantt/b.json'), JSON.stringify({ ...goodSnap, sessionId: 'b', cwd: root, total: 0.5, rows }))
        srv = await startServer({ root, port: 0 })
        assert.deepEqual(Object.keys(JSON.parse(readFileSync(join(agent, 'gantt-history.json'), 'utf8')).sessions).sort(), ['a', 'b'])
      }
    } finally {
      await srv.close()
      rmSync(join(root, '..', '..'), { recursive: true, force: true })
      rmSync(outside, { recursive: true, force: true })
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
    const health = JSON.parse(body || 'null')
    assert.deepEqual({ ...health, code: typeof health.code, pid: typeof health.pid }, { ok: true, root, code: 'string', pid: 'number' })
  } finally {
    child.kill()
    rmSync(root, { recursive: true, force: true })
  }
})

test('codeFiles follows relative imports once, skips bare and missing ones', () => {
  const dir = tmpRoot()
  try {
    mkdirSync(join(dir, 'x'))
    mkdirSync(join(dir, 'b'))
    writeFileSync(join(dir, 'x', 'entry.ts'), "import fs from 'node:fs'\nimport { a } from './a.ts'\nimport type { C } from '../b/c.ts'\nimport './gone.ts'\nimport { g } from './gone.ts'\n")
    writeFileSync(join(dir, 'x', 'a.ts'), "import { e } from './entry.ts'\n")
    writeFileSync(join(dir, 'b', 'c.ts'), '')
    const real = realpathSync(dir)
    assert.deepEqual(codeFiles(join(dir, 'x', 'entry.ts')), [join(real, 'b', 'c.ts'), join(real, 'x', 'a.ts'), join(real, 'x', 'entry.ts')])
    assert.deepEqual(codeFiles(join(dir, 'nope.ts')), [])
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
  const real = codeFiles(import.meta.dirname + '/server.ts').map((f) => f.split('/').pop())
  for (const f of ['server.ts', 'api.ts', 'groups.ts', 'rows.ts']) assert.ok(real.includes(f), f)
})

test('codeVersion changes with any file and is null when one is missing', () => {
  const dir = tmpRoot()
  try {
    const [a, b] = [join(dir, 'a.ts'), join(dir, 'b.ts')]
    writeFileSync(a, '1')
    writeFileSync(b, '2')
    const v = codeVersion([a, b])
    assert.match(v ?? '', /^[0-9a-f]{16}$/)
    assert.equal(codeVersion([a, b]), v)
    writeFileSync(b, '3')
    assert.notEqual(codeVersion([a, b]), v)
    assert.equal(codeVersion([a, join(dir, 'gone.ts')]), null)
    assert.equal(codeVersion([]), null)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})

test('restartWatch asks for a restart only for a new version seen twice, never a failed one', () => {
  // 'F:x' marks x failed before the next check.
  const cases: { running: string; steps: string[]; want: boolean[] }[] = [
    { running: 'r', steps: ['r', 'x', 'x'], want: [false, false, true] },
    { running: 'r', steps: ['x', 'y', 'y'], want: [false, false, true] },
    { running: 'r', steps: ['x', 'r', 'x'], want: [false, false, false] },
    { running: 'r', steps: ['null', 'null', 'null'], want: [false, false, false] },
    { running: 'r', steps: ['x', 'x', 'F:x', 'x', 'x', 'y', 'y'], want: [false, true, false, false, false, true] },
  ]
  for (const c of cases) {
    const w = restartWatch(c.running)
    const got: boolean[] = []
    for (const step of c.steps) {
      if (step.startsWith('F:')) w.failed(step.slice(2))
      else got.push(w.check(step === 'null' ? null : step))
    }
    assert.deepEqual(got, c.want, c.steps.join(','))
  }
})

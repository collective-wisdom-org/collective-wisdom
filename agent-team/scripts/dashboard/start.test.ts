import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, utimesSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { portFor, startDashboard } from './start.ts'

function tmpRoot(): string {
  return mkdtempSync(join(tmpdir(), 'dash-start-'))
}

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const s = createServer()
    s.once('error', reject)
    s.listen(0, '127.0.0.1', () => {
      const p = (s.address() as { port: number }).port
      s.close(() => resolve(p))
    })
  })
}

const readDash = (root: string) => JSON.parse(readFileSync(join(root, '.agent-team', 'dashboard.json'), 'utf8'))

function kill(root: string) {
  try {
    process.kill(readDash(root).pid)
  } catch {}
}

test('portFor is stable and stays in 47000-47999', () => {
  assert.equal(portFor('/some/repo'), portFor('/some/repo'))
  for (let i = 0; i < 10; i++) {
    const p = portFor(`/repo/number/${i}`)
    assert.ok(p >= 47000 && p <= 47999, String(p))
  }
})

test('starts once, then reuses; a new environmentId is rewritten', async () => {
  const root = tmpRoot()
  const basePort = await freePort()
  try {
    const a = await startDashboard({ root, basePort })
    assert.equal(a.started, true)
    const b = await startDashboard({ root, basePort })
    assert.equal(b.started, false)
    assert.equal(b.url, a.url)
    assert.equal((await fetch(a.url + 'health')).status, 200)
    const c = await startDashboard({ root, basePort, environmentId: 'env-2' })
    assert.equal(c.started, false)
    assert.equal(readDash(root).environmentId, 'env-2')
  } finally {
    kill(root)
    rmSync(root, { recursive: true, force: true })
  }
})

test('a dead pid with a silent port is replaced', async () => {
  const root = tmpRoot()
  const basePort = await freePort()
  mkdirSync(join(root, '.agent-team'))
  writeFileSync(join(root, '.agent-team', 'dashboard.json'), JSON.stringify({ pid: 2147483646, port: await freePort() }))
  try {
    const r = await startDashboard({ root, basePort })
    assert.equal(r.started, true)
    assert.equal(readDash(root).port, basePort)
  } finally {
    kill(root)
    rmSync(root, { recursive: true, force: true })
  }
})

test('a taken base port moves the dashboard above it', async () => {
  const root = tmpRoot()
  const basePort = await freePort()
  const blocker = createServer((_, res) => res.end('nope'))
  await new Promise<void>((r) => blocker.listen(basePort, '127.0.0.1', r))
  try {
    const r = await startDashboard({ root, basePort })
    assert.equal(r.started, true)
    assert.ok(readDash(root).port > basePort)
  } finally {
    kill(root)
    blocker.closeAllConnections()
    blocker.close()
    rmSync(root, { recursive: true, force: true })
  }
})

test('start prunes snapshots older than 24 hours only', async () => {
  const root = tmpRoot()
  const basePort = await freePort()
  const dir = join(root, '.agent-team', 'gantt')
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, 'old.json'), '{}')
  writeFileSync(join(dir, 'new.json'), '{}')
  const old = new Date(Date.now() - 25 * 3600 * 1000)
  utimesSync(join(dir, 'old.json'), old, old)
  try {
    await startDashboard({ root, basePort })
    assert.equal(existsSync(join(dir, 'old.json')), false)
    assert.equal(existsSync(join(dir, 'new.json')), true)
  } finally {
    kill(root)
    rmSync(root, { recursive: true, force: true })
  }
})

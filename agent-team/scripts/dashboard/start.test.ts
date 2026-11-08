import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { mkdtempSync, mkdirSync, readdirSync, readFileSync, writeFileSync, existsSync, utimesSync, rmSync, symlinkSync, lstatSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { portFor, startDashboard } from './start.ts'
import { backupDir } from './backup.ts'

// start takes a backup into the home folder; point that at a temp folder so no test touches the real one.
const home = mkdtempSync(join(tmpdir(), 'dash-home-'))
process.env.HOME = home

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

test('start prunes only old regular .json files inside real folders', async () => {
  const old = new Date(Date.now() - 25 * 3600 * 1000)
  const aged = (f: string) => {
    writeFileSync(f, '{}')
    utimesSync(f, old, old)
  }
  const cases: { name: string; setup: (root: string, outside: string) => string[]; gone: string[] }[] = [
    {
      name: 'symlinked gantt folder',
      setup: (root, outside) => {
        mkdirSync(join(root, '.agent-team'))
        symlinkSync(outside, join(root, '.agent-team', 'gantt'))
        aged(join(outside, 'old.json'))
        aged(join(outside, 'old.txt'))
        return [join(outside, 'old.json'), join(outside, 'old.txt')]
      },
      gone: [],
    },
    {
      name: 'symlinked .agent-team folder',
      setup: (root, outside) => {
        mkdirSync(join(outside, 'gantt'))
        symlinkSync(outside, join(root, '.agent-team'))
        aged(join(outside, 'gantt', 'old.json'))
        return [join(outside, 'gantt', 'old.json')]
      },
      gone: [],
    },
    {
      name: 'non-json old file in a real gantt folder',
      setup: (root) => {
        mkdirSync(join(root, '.agent-team', 'gantt'), { recursive: true })
        aged(join(root, '.agent-team', 'gantt', 'old.txt'))
        aged(join(root, '.agent-team', 'gantt', 'old.json'))
        return [join(root, '.agent-team', 'gantt', 'old.txt')]
      },
      gone: ['old.json'],
    },
    {
      name: 'old symlink entry in a real gantt folder',
      setup: (root, outside) => {
        mkdirSync(join(root, '.agent-team', 'gantt'), { recursive: true })
        aged(join(outside, 'target.json'))
        symlinkSync(join(outside, 'target.json'), join(root, '.agent-team', 'gantt', 'link.json'))
        return [join(outside, 'target.json'), join(root, '.agent-team', 'gantt', 'link.json')]
      },
      gone: [],
    },
  ]
  for (const c of cases) {
    const root = tmpRoot()
    const outside = tmpRoot()
    const basePort = await freePort()
    const survivors = c.setup(root, outside)
    try {
      await startDashboard({ root, basePort }).catch(() => {})
      for (const f of survivors) assert.ok(lstatSync(f, { throwIfNoEntry: false }), `${c.name}: ${f} survives`)
      for (const f of c.gone) assert.equal(existsSync(join(root, '.agent-team', 'gantt', f)), false, `${c.name}: ${f} pruned`)
    } finally {
      kill(root)
      rmSync(root, { recursive: true, force: true })
      rmSync(outside, { recursive: true, force: true })
    }
  }
})

test('dashboard.json is never written through a link', async () => {
  for (const reuse of [false, true]) {
    const root = tmpRoot()
    const outside = tmpRoot()
    const basePort = await freePort()
    const target = join(outside, 'precious.txt')
    const dash = join(root, '.agent-team', 'dashboard.json')
    try {
      if (reuse) {
        await startDashboard({ root, basePort })
        writeFileSync(target, readFileSync(dash, 'utf8'))
        rmSync(dash)
      } else {
        mkdirSync(join(root, '.agent-team'))
        writeFileSync(target, 'PRECIOUS')
      }
      symlinkSync(target, dash)
      const before = readFileSync(target, 'utf8')
      await startDashboard({ root, basePort, environmentId: 'env-x' }).catch(() => {})
      assert.equal(readFileSync(target, 'utf8'), before, `reuse=${reuse}`)
    } finally {
      kill(root)
      rmSync(root, { recursive: true, force: true })
      rmSync(outside, { recursive: true, force: true })
    }
  }
})

test('a linked .agent-team gets no dashboard.json and no server', async () => {
  const root = tmpRoot()
  const outside = tmpRoot()
  const basePort = await freePort()
  symlinkSync(outside, join(root, '.agent-team'))
  try {
    await assert.rejects(startDashboard({ root, basePort }), /\.agent-team/)
    assert.equal(existsSync(join(outside, 'dashboard.json')), false)
    assert.equal(await fetch(`http://127.0.0.1:${basePort}/health`).then(() => true, () => false), false)
  } finally {
    rmSync(root, { recursive: true, force: true })
    rmSync(outside, { recursive: true, force: true })
  }
})

test('start takes a backup, and still starts when the backup folder is refused', async () => {
  const basePort = await freePort()
  const roots = [tmpRoot(), tmpRoot()]
  try {
    for (const root of roots) {
      mkdirSync(join(root, '.agent-team'))
      writeFileSync(join(root, '.agent-team', 'spend.json'), '{"v":1}')
    }
    const ok = await startDashboard({ root: roots[0], basePort })
    assert.equal(ok.started, true)
    const sets = readdirSync(backupDir(roots[0]))
    assert.equal(sets.length, 1)
    assert.equal(readFileSync(join(backupDir(roots[0]), sets[0], 'spend.json'), 'utf8'), '{"v":1}')
    rmSync(join(home, '.agent-team-backups'), { recursive: true })
    writeFileSync(join(home, '.agent-team-backups'), 'a file, not a folder')
    const refused = await startDashboard({ root: roots[1], basePort: basePort + 1 })
    assert.equal(refused.started, true)
  } finally {
    for (const root of roots) {
      kill(root)
      rmSync(root, { recursive: true, force: true })
    }
    rmSync(join(home, '.agent-team-backups'), { recursive: true, force: true })
  }
})

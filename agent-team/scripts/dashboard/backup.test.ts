import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// Every test works in temp folders; the home folder is a temp one too, so the default location can't touch the real one.
const home = mkdtempSync(join(tmpdir(), 'backup-home-'))
process.env.HOME = home
const { backup, backupDir, restore } = await import('./backup.ts')

const tmp = () => mkdtempSync(join(tmpdir(), 'backup-test-'))
const T0 = Date.UTC(2026, 10, 8, 12, 0, 0)
const at = (i: number) => new Date(T0 + i * 1000)
const FILES = ['gantt-history.json', 'spend.json', 'state.json']
const j = (v: string) => JSON.stringify({ v })

type Write = Record<string, string | null | 'link'>

/** Sets `.agent-team` files: text writes the file, null removes it, 'link' replaces it with a link to a file outside. */
function apply(root: string, outside: string, write: Write) {
  const dir = join(root, '.agent-team')
  mkdirSync(join(dir, 'gantt'), { recursive: true })
  writeFileSync(join(dir, 'dashboard.json'), '{}')
  writeFileSync(join(dir, 'state.lock'), 'lock')
  writeFileSync(join(dir, 'gantt', 's.json'), '{}')
  for (const [name, v] of Object.entries(write)) {
    rmSync(join(dir, name), { force: true })
    if (v === 'link') symlinkSync(join(outside, 'target.json'), join(dir, name))
    else if (v !== null) writeFileSync(join(dir, name), v)
  }
}

const sets = (dest: string) => readdirSync(dest).sort()
const all = { 'spend.json': j('s1'), 'gantt-history.json': j('g1'), 'state.json': j('t1') }

test('backup: which files land in a set, and which sets stay', () => {
  const rows: { name: string; steps: { write: Write; keep?: number }[]; sets: string[][]; newestSpend?: string }[] = [
    { name: 'all present', steps: [{ write: all }], sets: [FILES] },
    { name: 'one missing', steps: [{ write: { ...all, 'state.json': null } }], sets: [['gantt-history.json', 'spend.json']] },
    { name: 'one invalid JSON', steps: [{ write: { ...all, 'spend.json': '{oops' } }], sets: [['gantt-history.json', 'state.json']] },
    { name: 'one a link', steps: [{ write: { ...all, 'state.json': 'link' } }], sets: [['gantt-history.json', 'spend.json']] },
    { name: 'none usable makes no set', steps: [{ write: { 'spend.json': '{oops' } }], sets: [] },
    { name: 'nothing changed since the last set', steps: [{ write: all }, { write: all }], sets: [FILES] },
    { name: 'a change makes a second set', steps: [{ write: all }, { write: { 'spend.json': j('s2') } }], sets: [FILES, FILES], newestSpend: j('s2') },
    {
      name: 'keep exceeded drops the oldest',
      steps: [1, 2, 3, 4].map((n) => ({ write: { ...all, 'spend.json': j(`s${n}`) }, keep: 2 })),
      sets: [FILES, FILES],
      newestSpend: j('s4'),
    },
    {
      name: 'a broken file keeps its last good copy through pruning',
      steps: [{ write: all, keep: 2 }, ...[2, 3, 4].map((n) => ({ write: { 'spend.json': j(`s${n}`), 'state.json': '{oops' as Write[string] }, keep: 2 }))],
      sets: [FILES, FILES],
      newestSpend: j('s4'),
    },
  ]
  for (const row of rows) {
    const root = tmp()
    const dest = tmp()
    const outside = tmp()
    try {
      // Things in the backup folder that are not sets: never counted, deleted or followed.
      mkdirSync(join(dest, 'notes'))
      symlinkSync(outside, join(dest, '20200101T000000Z'))
      writeFileSync(join(outside, 'keepme'), 'x')
      row.steps.forEach((s, i) => {
        apply(root, outside, s.write)
        const r = backup({ root, dest, keep: s.keep, now: at(i) })
        assert.equal(r.error, undefined, row.name)
      })
      const real = sets(dest).filter((s) => s !== 'notes' && s !== '20200101T000000Z')
      assert.deepEqual(
        real.map((s) => readdirSync(join(dest, s)).sort()),
        row.sets,
        row.name,
      )
      if (row.newestSpend) assert.equal(readFileSync(join(dest, real[real.length - 1], 'spend.json'), 'utf8'), row.newestSpend, row.name)
      assert.ok(sets(dest).includes('notes') && lstatSync(join(dest, '20200101T000000Z')).isSymbolicLink(), row.name)
      assert.equal(readFileSync(join(outside, 'keepme'), 'utf8'), 'x', row.name)
      for (const s of real) {
        assert.equal(lstatSync(join(dest, s)).mode & 0o077, 0, `${row.name}: set is private`)
        for (const f of readdirSync(join(dest, s))) assert.equal(lstatSync(join(dest, s, f)).mode & 0o077, 0, `${row.name}: ${f} is private`)
      }
    } finally {
      for (const d of [root, dest, outside]) rmSync(d, { recursive: true, force: true })
    }
  }
})

test('backup and restore refuse a link where a folder belongs, and write nothing', async () => {
  const rows: { name: string; setup: (root: string, outside: string, dest: string) => void; useDest: boolean }[] = [
    { name: '.agent-team a link', useDest: true, setup: (root, outside) => (rmSync(join(root, '.agent-team'), { recursive: true }), symlinkSync(outside, join(root, '.agent-team'))) },
    { name: 'dest a link', useDest: true, setup: (root, outside, dest) => (rmSync(dest, { recursive: true }), symlinkSync(outside, dest)) },
    { name: 'dest a file', useDest: true, setup: (root, outside, dest) => (rmSync(dest, { recursive: true }), writeFileSync(dest, 'x')) },
    { name: '~/.agent-team-backups a link', useDest: false, setup: (root, outside) => symlinkSync(outside, join(home, '.agent-team-backups')) },
    {
      name: 'repo folder a link',
      useDest: false,
      setup: (root, outside) => (mkdirSync(join(home, '.agent-team-backups')), symlinkSync(outside, backupDir(root))),
    },
  ]
  for (const row of rows) {
    const root = tmp()
    const dest = tmp()
    const outside = tmp()
    try {
      apply(root, outside, all)
      row.setup(root, outside, dest)
      if (lstatSync(join(root, '.agent-team')).isDirectory()) writeFileSync(join(root, '.agent-team', 'spend.json'), j('mine'))
      const args = row.useDest ? { root, dest } : { root }
      assert.match(backup({ ...args, now: at(0) }).error ?? '', /not a real folder/, row.name)
      assert.match((await restore({ ...args, force: true })).error ?? '', /not a real folder/, row.name)
      assert.deepEqual(readdirSync(outside), [], row.name)
      if (!row.useDest) assert.deepEqual(readdirSync(home).filter((n) => n !== '.agent-team-backups'), [], row.name)
    } finally {
      for (const d of [root, dest, outside]) rmSync(d, { recursive: true, force: true })
      rmSync(join(home, '.agent-team-backups'), { recursive: true, force: true })
    }
  }
})

test('restore: which copy comes back, and what an existing file does', async () => {
  type Row = {
    name: string
    /** Edits the newest set after both backups were taken. */
    damage?: (dest: string, setNames: string[], outside: string) => void
    /** What `.agent-team` holds when restore runs. */
    now: Write
    force?: boolean
    status: Record<string, string>
    /** The content each file ends with. */
    end: Record<string, string | null>
    setCount: number
    /** After --force, the newest set holds this spend.json. */
    forceSaved?: string
  }
  const v1 = { 'spend.json': j('s1'), 'gantt-history.json': j('g1'), 'state.json': j('t1') }
  const v2 = { 'spend.json': j('s2'), 'gantt-history.json': j('g2'), 'state.json': j('t2') }
  const restored = { 'spend.json': 'restored', 'gantt-history.json': 'restored', 'state.json': 'restored' }
  const gone: Write = { 'spend.json': null, 'gantt-history.json': null, 'state.json': null }
  const rows: Row[] = [
    { name: 'all missing: newest copies return', now: gone, status: restored, end: v2, setCount: 2 },
    { name: 'an existing file is kept', now: { ...gone, 'spend.json': j('mine') }, status: { ...restored, 'spend.json': 'kept' }, end: { ...v2, 'spend.json': j('mine') }, setCount: 2 },
    {
      name: 'force replaces it after a new set holds the old one',
      now: { ...gone, 'spend.json': j('mine') },
      force: true,
      status: restored,
      end: v2,
      setCount: 3,
      forceSaved: j('mine'),
    },
    {
      name: 'a broken newest copy falls back to the older set',
      damage: (dest, [, newest]) => writeFileSync(join(dest, newest, 'spend.json'), '{oops'),
      now: gone,
      status: restored,
      end: { ...v2, 'spend.json': j('s1') },
      setCount: 2,
    },
    {
      name: 'a link in a set is not followed',
      damage: (dest, [, newest], outside) => (rmSync(join(dest, newest, 'spend.json')), writeFileSync(join(outside, 'target.json'), j('LINK')), symlinkSync(join(outside, 'target.json'), join(dest, newest, 'spend.json'))),
      now: gone,
      status: restored,
      end: { ...v2, 'spend.json': j('s1') },
      setCount: 2,
    },
    {
      name: 'a file missing from the newest set comes from the older one',
      damage: (dest, [, newest]) => rmSync(join(dest, newest, 'state.json')),
      now: gone,
      status: restored,
      end: { ...v2, 'state.json': j('t1') },
      setCount: 2,
    },
    {
      name: 'a file in no set is reported',
      damage: (dest, names) => names.forEach((n) => rmSync(join(dest, n, 'state.json'))),
      now: gone,
      status: { ...restored, 'state.json': 'missing' },
      end: { ...v2, 'state.json': null },
      setCount: 2,
    },
    {
      name: 'a link at the target is refused, not followed',
      now: { ...gone, 'spend.json': 'link' },
      force: true,
      status: { ...restored, 'spend.json': 'refused' },
      end: { ...v2, 'spend.json': j('LINKED') },
      setCount: 2,
    },
  ]
  for (const row of rows) {
    const root = tmp()
    const dest = tmp()
    const outside = tmp()
    try {
      apply(root, outside, v1)
      backup({ root, dest, now: at(0) })
      apply(root, outside, v2)
      backup({ root, dest, now: at(1) })
      row.damage?.(dest, sets(dest), outside)
      writeFileSync(join(outside, 'target.json'), j('LINKED'))
      apply(root, outside, row.now)
      const r = await restore({ root, dest, force: row.force, now: at(2) })
      assert.deepEqual(Object.fromEntries(r.files.map((f) => [f.name, f.status])), row.status, row.name)
      for (const [name, text] of Object.entries(row.end)) {
        const file = join(root, '.agent-team', name)
        assert.equal(text === null ? lstatSync(file, { throwIfNoEntry: false }) : readFileSync(file, 'utf8'), text ?? undefined, `${row.name}: ${name}`)
      }
      assert.equal(sets(dest).length, row.setCount, row.name)
      assert.equal(readFileSync(join(outside, 'target.json'), 'utf8'), j('LINKED'), `${row.name}: link target untouched`)
      if (row.forceSaved) assert.equal(readFileSync(join(dest, sets(dest)[2], 'spend.json'), 'utf8'), row.forceSaved, row.name)
    } finally {
      for (const d of [root, dest, outside]) rmSync(d, { recursive: true, force: true })
    }
  }
})

test('restore refuses while the dashboard answers for this root', async () => {
  const root = tmp()
  const dest = tmp()
  const outside = tmp()
  const server = createServer((req, res) => res.end(JSON.stringify({ ok: true, root })))
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', r))
  try {
    apply(root, outside, all)
    backup({ root, dest, now: at(0) })
    writeFileSync(join(root, '.agent-team', 'dashboard.json'), JSON.stringify({ port: (server.address() as { port: number }).port }))
    rmSync(join(root, '.agent-team', 'spend.json'))
    assert.match((await restore({ root, dest })).error ?? '', /stop it first/)
    assert.equal(lstatSync(join(root, '.agent-team', 'spend.json'), { throwIfNoEntry: false }), undefined)
  } finally {
    server.close()
    for (const d of [root, dest, outside]) rmSync(d, { recursive: true, force: true })
  }
})

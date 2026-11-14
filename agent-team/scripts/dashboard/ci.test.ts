import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ciWait, createCi, requiredFromProject } from './ci.ts'

const at = (min: number) => new Date(Date.UTC(2026, 0, 1, 0, min)).toISOString()
const ms = (min: number) => Date.parse(at(min))
type Run = { name?: string; start?: number; end?: number | null }
const run = ({ name = 'checks', start = 0, end = 1 }: Run) => ({ name, startedAt: at(start), completedAt: end === null ? null : at(end) })
const pr = (...commits: Run[][]) => JSON.stringify({ data: { repository: { pullRequest: { commits: { nodes: commits.map((runs) => ({ commit: { checkSuites: { nodes: [{ checkRuns: { nodes: runs.map(run) } }] } } })) } } } } })

test('ciWait: one span per commit that ran a required check', () => {
  const cases: [string, string, string[], [number, number | null][] | null][] = [
    ['one green run', pr([{ start: 1, end: 4 }]), ['checks'], [[ms(1), ms(4)]]],
    ['a push cancels a run: both spans stay', pr([{ start: 0, end: 3 }], [{ start: 2, end: 6 }]), ['checks'], [[ms(0), ms(3)], [ms(2), ms(6)]]],
    ['a required run still going', pr([{ start: 1, end: 4 }, { name: 'lint', start: 2, end: null }]), ['checks', 'lint'], [[ms(1), null]]],
    ['no checks', pr([], []), ['checks'], []],
    ['runs not required are ignored for the end, not the start', pr([{ name: 'other', start: 0, end: 9 }, { start: 1, end: 4 }]), ['checks'], [[ms(0), ms(4)]]],
    ['a commit with only other runs gives no span', pr([{ name: 'other' }]), ['checks'], []],
    ['no required names: every run counts', pr([{ name: 'a', start: 1, end: 3 }, { name: 'b', start: 2, end: 5 }]), [], [[ms(1), ms(5)]]],
    ['bad json', 'nope', [], null],
    ['no pull request', JSON.stringify({ data: { repository: { pullRequest: null } } }), [], null],
  ]
  for (const [name, json, required, want] of cases) assert.deepEqual(ciWait(json, required), want, name)
})

test('requiredFromProject: names from the row, none for no CI, no names when unset', () => {
  const row = (cell: string) => `| Repo | <https://x> |\n| Required CI checks | ${cell} |\n`
  assert.deepEqual(requiredFromProject(row('`checks`. CI runs on pull requests only.')), { none: false, names: ['checks'] })
  assert.deepEqual(requiredFromProject(row('`a`, `b, c`')), { none: false, names: ['a', 'b', 'c'] })
  assert.deepEqual(requiredFromProject(row('none (no CI yet)')), { none: true, names: [] })
  assert.deepEqual(requiredFromProject(row('TODO(owner)')), { none: false, names: [] })
  assert.deepEqual(requiredFromProject('| Repo | x |\n'), { none: false, names: [] })
})

test('ci reader: an open PR is re-read after a minute (5 minutes once its spans are closed), a merged PR once, a failed read keeps the spans', async () => {
  let clock = 1_000_000
  const calls: string[][] = []
  let reply: string | Error = pr([{ start: 1, end: null }])
  const ci = createCi({ now: () => clock, run: async (args) => { calls.push(args); if (reply instanceof Error) throw reply; return reply } })
  const cfg = { slug: 'o/r', required: ['checks'] }
  const wants = [{ id: 'CW-1', pr: 7 }, { id: 'CW-2', pr: 8, merged: true }, { id: 'CW-3', pr: null }]
  const tick = async (by: number, w = wants) => { clock += by; ci.want(w, cfg); await ci.idle() }

  await tick(0)
  assert.equal(calls.length, 2)
  assert.deepEqual(calls[0].slice(-6), ['-f', 'o=o', '-f', 'r=r', '-F', 'n=7'])
  assert.deepEqual(Object.keys(ci.get()), ['CW-1#7', 'CW-2#8'])
  await tick(59_000)
  assert.equal(calls.length, 2)
  reply = new Error('gh down')
  await tick(2_000)
  assert.equal(calls.length, 3)
  assert.deepEqual(Object.keys(ci.get()), ['CW-1#7', 'CW-2#8'])
  await tick(0, [])
  assert.deepEqual(ci.get(), {})
  await tick(60_000, [])
  ci.want(wants, cfg)
  await ci.idle()
  assert.equal(calls.length, 5)
  reply =pr([{ start: 1, end: 4 }])
  await tick(60_000)
  assert.equal(calls.length, 7)
  for (const [by, n] of [[60_000, 7], [239_000, 7], [1_000, 8]]) {
    await tick(by)
    assert.equal(calls.length, n, `closed spans, ${by}`)
  }
})

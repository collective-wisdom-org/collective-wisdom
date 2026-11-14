import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createMerged, parseMerged } from './merged.ts'

const CFG = { prefix: 'CW', slug: 'o/r', issueUrls: true }
const pr = (o: Record<string, unknown>) => ({ number: 1, title: 'feat: x (CW-1)', headRefName: 'feat/cw-1-x', mergedAt: '2026-01-01T00:00:00Z', url: 'https://github.com/o/r/pull/1', ...o })

test('parseMerged: newest first, id from branch or title, junk left out, urls checked', () => {
  const list = [
    pr({ number: 2, mergedAt: '2026-01-02T00:00:00Z', headRefName: 'feat/cw-2', title: 'fix: two (CW-2)' }),
    pr({ number: 1 }),
    pr({ number: 3, mergedAt: '2026-01-03T00:00:00Z', headRefName: 'odd', title: 'docs: three\x1b (CW-3)' }),
    pr({ number: 4, headRefName: 'release', title: 'chore: no id' }),
    pr({ number: 5, mergedAt: 'nope' }),
    pr({ number: 6, mergedAt: '2026-01-02T00:00:00Z', headRefName: 'feat/cw-6-y', title: 'tie', url: 'https://evil.test/pull/6' }),
    null,
  ]
  const got = parseMerged(JSON.stringify(list), CFG)!
  assert.deepEqual(got.map((e) => e.id), ['CW-3', 'CW-6', 'CW-2', 'CW-1'])
  assert.equal(got[0].title, 'docs: three')
  assert.equal(got[1].prUrl, 'https://github.com/o/r/pull/6')
  assert.equal(got[3].mergedAt, Date.parse('2026-01-01T00:00:00Z'))
  assert.equal(got[3].issueUrl, 'https://github.com/o/r/issues/1')
  assert.equal(parseMerged(JSON.stringify([pr({})]), { ...CFG, issueUrls: false })![0].issueUrl, undefined)
  assert.equal(parseMerged('not json', CFG), null)
  assert.equal(parseMerged('{}', CFG), null)
})

test('parseMerged: infra/ branches count only when the heads list them, and cw-7 is not cw-70', () => {
  const heads = { ...CFG, heads: ['feat/', 'infra/'] }
  const ids = (cfg: typeof CFG, branch: string) => parseMerged(JSON.stringify([pr({ headRefName: branch, title: 'no id' })]), cfg)!.map((e) => e.id)
  assert.deepEqual(ids(heads, 'infra/cw-7-z'), ['CW-7'])
  assert.deepEqual(ids(heads, 'feat/cw-7-z'), ['CW-7'])
  assert.deepEqual(ids(CFG, 'infra/cw-7-z'), [])
  assert.deepEqual(ids(heads, 'fix/cw-7-z'), [])
  assert.deepEqual(ids(heads, 'infra/cw-70-z'), ['CW-70'])
})

test('merged reader: a failed read keeps the list; reads are 60 seconds apart', async () => {
  let clock = 1_000_000
  const calls: string[][] = []
  let reply: string | Error = JSON.stringify([pr({})])
  const m = createMerged({ now: () => clock, run: async (args) => { calls.push(args); if (reply instanceof Error) throw reply; return reply } })

  m.want(null)
  m.want(CFG)
  await m.idle()
  assert.deepEqual(m.get().map((e) => e.id), ['CW-1'])
  assert.deepEqual(calls[0].slice(0, 6), ['pr', 'list', '--repo', 'o/r', '--state', 'merged'])

  reply = new Error('gh down')
  clock += 59_000
  m.want(CFG)
  await m.idle()
  assert.equal(calls.length, 1)
  clock += 2_000
  m.want(CFG)
  await m.idle()
  assert.equal(calls.length, 2)
  assert.deepEqual(m.get().map((e) => e.id), ['CW-1'])

  reply = 'garbage'
  clock += 60_000
  m.want(CFG)
  await m.idle()
  assert.equal(calls.length, 3)
  assert.deepEqual(m.get().map((e) => e.id), ['CW-1'])
})

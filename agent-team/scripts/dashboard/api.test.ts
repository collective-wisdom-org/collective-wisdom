import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { buildApi, repoUrlFromProject } from './api.ts'

const NOW = 1_800_000_000_000
const GH = { url: 'https://github.com/o/r', isGithubIssues: true }
const stateOf = (id: string, extra: Record<string, unknown> = {}) => ({
  tickets: { [id]: { title: 't', stage: 'build', status: 'going. Risk: low', ...extra } },
})
const build = (o: Partial<Parameters<typeof buildApi>[0]> = {}) =>
  buildApi({ state: null, snapshots: [], repo: GH, titles: {}, environmentId: 'env', now: NOW, ...o })
const firstRow = (o: Partial<Parameters<typeof buildApi>[0]>) => build(o).status[0].rows[0] as any

test('whitelist: free text and relay never reach the api', () => {
  const state = stateOf('CW-1', { pendingRelay: 'my words', note: 'free text' })
  const json = JSON.stringify(build({ state }))
  assert.ok(!json.includes('my words'))
  assert.ok(!json.includes('free text'))
})

test('links', () => {
  const full = { pr: 172, childThreadId: 't1' }
  const cases: [string, string, Record<string, unknown>, Partial<Parameters<typeof buildApi>[0]>, Record<string, string | undefined>][] = [
    ['all', 'CW-171', full, {}, { issueUrl: 'https://github.com/o/r/issues/171', prUrl: 'https://github.com/o/r/pull/172', threadLink: '<t3-thread://v2/env/t1>' }],
    ['no number', 'ABC', full, {}, { issueUrl: undefined, prUrl: 'https://github.com/o/r/pull/172', threadLink: '<t3-thread://v2/env/t1>' }],
    ['string pr', 'CW-171', { ...full, pr: '172' }, {}, { issueUrl: 'https://github.com/o/r/issues/171', prUrl: undefined, threadLink: '<t3-thread://v2/env/t1>' }],
    ['null pr', 'CW-171', { ...full, pr: null }, {}, { issueUrl: 'https://github.com/o/r/issues/171', prUrl: undefined, threadLink: '<t3-thread://v2/env/t1>' }],
    ['no env', 'CW-171', full, { environmentId: null }, { issueUrl: 'https://github.com/o/r/issues/171', prUrl: 'https://github.com/o/r/pull/172', threadLink: undefined }],
    ['not issues', 'CW-171', full, { repo: { ...GH, isGithubIssues: false } }, { issueUrl: undefined, prUrl: 'https://github.com/o/r/pull/172', threadLink: '<t3-thread://v2/env/t1>' }],
  ]
  for (const [name, id, extra, over, want] of cases) {
    const r = firstRow({ state: stateOf(id, extra), ...over })
    for (const k of ['issueUrl', 'prUrl', 'threadLink']) assert.equal(r[k], want[k], `${name} ${k}`)
  }
})

test('row title: state wins, else tracker title, else empty', () => {
  const cases: [string, Record<string, unknown>, Record<string, string>, string][] = [
    ['state wins', { title: 'from state' }, { 'CW-1': 'from tracker' }, 'from state'],
    ['empty state', { title: '' }, { 'CW-1': 'from tracker' }, 'from tracker'],
    ['missing state', { title: undefined }, { 'CW-1': 'from tracker' }, 'from tracker'],
    ['neither', { title: '' }, {}, ''],
  ]
  for (const [name, extra, titles, want] of cases) assert.equal(firstRow({ state: stateOf('CW-1', extra), titles }).title, want, name)
})

test('snapshots', () => {
  const row = (end: number | null, name = 'n') => ({ id: 'a', depth: 0, name, repo: 'r', start: 1, end, tokens: 1, cost: null, childCount: 0 })
  const snap = (age: number, rows: unknown) => ({ sessionId: 's', cwd: '/c', updatedAt: NOW - age, total: null, rows })
  const H = 3_600_000
  const cases: [string, unknown, (g: any[]) => void][] = [
    ['23h kept', snap(23 * H, [row(2)]), (g) => assert.equal(g.length, 1)],
    ['25h dropped', snap(25 * H, [row(2)]), (g) => assert.equal(g.length, 0)],
    ['stale', snap(31_000, [row(null)]), (g) => { assert.equal(g[0].stale, true); assert.equal(g[0].rows[0].end, NOW - 31_000) }],
    ['31s all ended', snap(31_000, [row(2)]), (g) => assert.equal(g[0].stale, false)],
    ['fresh running', snap(5_000, [row(null)]), (g) => { assert.equal(g[0].stale, false); assert.equal(g[0].rows[0].end, null) }],
    ['idle main only', snap(31_000, [{ ...row(null), id: 'main' }]), (g) => { assert.equal(g[0].stale, false); assert.equal(g[0].rows[0].end, NOW - 31_000) }],
    ['main plus running subagent, 31s', snap(31_000, [{ ...row(null), id: 'main' }, row(null)]), (g) => { assert.equal(g[0].stale, true); assert.deepEqual(g[0].rows.map((r: any) => r.end), [NOW - 31_000, NOW - 31_000]) }],
    ['main plus running subagent, 5s', snap(5_000, [{ ...row(null), id: 'main' }, row(null)]), (g) => { assert.equal(g[0].stale, false); assert.deepEqual(g[0].rows.map((r: any) => r.end), [null, null]) }],
    ['bad end counts as running', snap(31_000, [{ ...row(null), end: 'x' }]), (g) => assert.equal(g[0].stale, true)],
    ['extra keys dropped', { ...snap(1, [{ ...row(2), secret: 'x' }]), prompt: 'p' }, (g) => {
      assert.deepEqual(Object.keys(g[0]).sort(), ['cwd', 'rows', 'sessionId', 'stale', 'total', 'updatedAt'])
      assert.deepEqual(Object.keys(g[0].rows[0]).sort(), ['childCount', 'cost', 'depth', 'end', 'id', 'name', 'repo', 'start', 'tokens'])
    }],
    ['string', 'x', (g) => assert.equal(g.length, 0)],
    ['no rows', { sessionId: 's', cwd: '/c', updatedAt: NOW }, (g) => assert.equal(g.length, 0)],
    ['rows not array', snap(1, 'x'), (g) => assert.equal(g.length, 0)],
    ['long name', snap(1, [row(2, 'x'.repeat(80))]), (g) => assert.equal(g[0].rows[0].name.length, 60)],
  ]
  for (const [name, s, check] of cases) {
    try { check(build({ snapshots: [s] }).gantt) } catch (e) { throw new Error(`${name}: ${(e as Error).message}`) }
  }
})

test('empty state', () => {
  for (const state of [null, {}, 'x']) assert.deepEqual(build({ state }).status, [])
})

test('repoUrlFromProject', () => {
  const md = readFileSync(join(import.meta.dirname, '../../../docs/agents/project.md'), 'utf8')
  assert.deepEqual(repoUrlFromProject(md), { url: 'https://github.com/collective-wisdom-org/collective-wisdom', isGithubIssues: true })
  assert.equal(repoUrlFromProject('# nothing here\n'), null)
})

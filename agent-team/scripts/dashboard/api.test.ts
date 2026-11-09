import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { buildApi, ledgerSessions, teamSessions, parseWorktrees, repoUrlFromProject } from './api.ts'
import { applyEvent, cursorSnapshot, emptyState } from '../../../mods/agent-gantt/hooks/cursor.ts'

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

test('rows sort newest update first; queued stages keep their places', () => {
  const t = (stage: string, queuedAt?: string) => ({ title: 't', stage, status: 'x. Risk: low', queuedAt })
  const cases: [string, Record<string, unknown>, Record<string, number>, string, string[]][] = [
    ['newest first', { 'CW-1': t('build'), 'CW-2': t('build'), 'CW-3': t('build') }, { 'CW-1': 1, 'CW-2': 3, 'CW-3': 2 }, 'Building', ['CW-2', 'CW-3', 'CW-1']],
    ['no time last, state order', { 'CW-1': t('build'), 'CW-2': t('build'), 'CW-3': t('build'), 'CW-4': t('build') }, { 'CW-3': 5 }, 'Building', ['CW-3', 'CW-1', 'CW-2', 'CW-4']],
    ['same time keeps state order', { 'CW-1': t('build'), 'CW-2': t('build') }, { 'CW-1': 4, 'CW-2': 4 }, 'Building', ['CW-1', 'CW-2']],
    ['queued to build unchanged', { 'CW-1': t('build-queued', 'a'), 'CW-2': t('build-queued', 'b') }, { 'CW-1': 1, 'CW-2': 9 }, 'Queued to build', ['CW-1', 'CW-2']],
    ['queued to merge unchanged', { 'CW-1': t('merge-queued', 'a'), 'CW-2': t('merge-queued', 'b') }, { 'CW-1': 1, 'CW-2': 9 }, 'Queued to merge', ['CW-1', 'CW-2']],
    ['Other: spec-queued stay, blocked sort', { 'CW-1': t('blocked'), 'CW-2': t('spec-queued', 'a'), 'CW-3': t('blocked'), 'CW-4': t('spec-queued', 'b') }, { 'CW-1': 1, 'CW-2': 1, 'CW-3': 2, 'CW-4': 9 }, 'Other', ['CW-2', 'CW-4', 'CW-3', 'CW-1']],
  ]
  for (const [name, tickets, updated, section, want] of cases) {
    const rows = build({ state: { tickets }, updated }).status.find((g) => g.name === section)!.rows
    assert.deepEqual(rows.map((r) => r.id), want, name)
  }
})

const WT = '/Users/me/.t3/worktrees/repo/t3-1'
/** The charts the card CW-1 gets from snapshots, when its branch lives in the worktree at `path`. */
const charts = (snapshots: unknown[], path = WT) =>
  (build({ state: stateOf('CW-1', { branch: 'b' }), snapshots, worktrees: [{ path, branch: 'b' }] }).status[0].rows[0] as any).gantt ?? []

test('snapshots', () => {
  const row = (end: number | null, name = 'n') => ({ id: 'a', depth: 0, name, repo: 'r', start: 1, end, tokens: 1, cost: null })
  const snap = (age: number, rows: unknown) => ({ sessionId: 's', cwd: WT, updatedAt: NOW - age, total: null, rows })
  const H = 3_600_000
  const cases: [string, unknown, (g: any[]) => void][] = [
    ['23h kept', snap(23 * H, [row(2)]), (g) => assert.equal(g.length, 1)],
    ['25h dropped', snap(25 * H, [row(2)]), (g) => assert.equal(g.length, 0)],
    ['stale', snap(31_000, [row(null)]), (g) => { assert.equal(g[0].stale, true); assert.equal(g[0].rows[0].end, NOW - 31_000) }],
    ['31s all ended', snap(31_000, [row(2)]), (g) => assert.equal(g[0].stale, false)],
    ['fresh running', snap(5_000, [row(null)]), (g) => { assert.equal(g[0].stale, false); assert.equal(g[0].rows[0].end, null) }],
    ['idle main only', snap(31_000, [{ ...row(null), id: 'main' }]), (g) => { assert.equal(g[0].stale, false); assert.equal(g[0].rows[0].end, NOW - 31_000) }],
    ['main-only with an open task, 31s', snap(31_000, [{ ...row(null), id: 'main' }, { ...row(null), id: 'main:task:0', kind: 'task' }]), (g) => { assert.equal(g[0].stale, false); assert.deepEqual(g[0].rows.map((r: any) => r.end), [NOW - 31_000, NOW - 31_000]) }],
    ['main plus running subagent, 31s', snap(31_000, [{ ...row(null), id: 'main' }, row(null)]), (g) => { assert.equal(g[0].stale, true); assert.deepEqual(g[0].rows.map((r: any) => r.end), [NOW - 31_000, NOW - 31_000]) }],
    ['main plus running subagent, 5s', snap(5_000, [{ ...row(null), id: 'main' }, row(null)]), (g) => { assert.equal(g[0].stale, false); assert.deepEqual(g[0].rows.map((r: any) => r.end), [null, null]) }],
    ['bad end counts as running', snap(31_000, [{ ...row(null), end: 'x' }]), (g) => assert.equal(g[0].stale, true)],
    ['extra keys dropped', { ...snap(1, [{ ...row(2), secret: 'x' }]), prompt: 'p' }, (g) => {
      assert.deepEqual(Object.keys(g[0]).sort(), ['cwd', 'pricing', 'rows', 'sessionId', 'stale', 'total', 'updatedAt'])
      assert.deepEqual(Object.keys(g[0].rows[0]).sort(), ['cost', 'depth', 'end', 'harness', 'id', 'kind', 'model', 'name', 'repo', 'segments', 'start', 'tokens'])
    }],
    ['pricing kept, else null', { ...snap(1, [row(2)]), pricing: 2 }, (g) => assert.deepEqual([g[0].pricing, charts([snap(1, [row(2)])])[0].pricing], [2, null])],
    ['string', 'x', (g) => assert.equal(g.length, 0)],
    ['no rows', { sessionId: 's', cwd: WT, updatedAt: NOW }, (g) => assert.equal(g.length, 0)],
    ['rows not array', snap(1, 'x'), (g) => assert.equal(g.length, 0)],
    ['long name', snap(1, [row(2, 'x'.repeat(80))]), (g) => assert.equal(g[0].rows[0].name.length, 60)],
  ]
  for (const [name, s, check] of cases) {
    try { check(charts([s])) } catch (e) { throw new Error(`${name}: ${(e as Error).message}`) }
  }
})

test('snapshots: row fields', () => {
  const base = { id: 'a', depth: 1, name: 'n', repo: 'r', start: 10, end: 50, tokens: 1, cost: null }
  const rowOf = (extra: Record<string, unknown>, age = 1000) =>
    charts([{ sessionId: 's', cwd: WT, updatedAt: NOW - age, total: null, rows: [{ ...base, ...extra }] }])[0].rows[0]
  const cases: [string, Record<string, unknown>, Record<string, unknown>][] = [
    ['new fields pass', { kind: 'task', model: 'opus-5-5', harness: 'T3 Code', segments: [[30, 50], [10, 20]] }, { kind: 'task', model: 'opus-5-5', harness: 'T3 Code', segments: [[10, 20], [30, 50]] }],
    ['bad kind, long label, non-string label', { kind: 'x', model: 'm'.repeat(80), harness: 7 }, { kind: 'agent', model: 'm'.repeat(40), harness: null }],
    ['bad pairs dropped', { segments: [[1, 'x'], [5, 4], ['a', 6], [Infinity, 7], [1], 'x', [12, null], [11, 13]] }, { segments: [[11, 13], [12, null]] }],
    ['no valid segments', { segments: [[5, 4], 'x'] }, { segments: [[10, 50]] }],
    ['segments capped', { segments: Array.from({ length: 600 }, (_, i) => [i, i + 1]) }, { segmentCount: 500, firstStart: 100 }],
    ['old row: childCount, no segments/model/harness', { childCount: 3 }, { kind: 'agent', segments: [[10, 50]], model: null, harness: null }],
  ]
  for (const [name, extra, want] of cases) {
    const got: any = rowOf(extra)
    assert.ok(!('childCount' in got), name)
    const { segmentCount, firstStart, ...rest } = want
    for (const [k, v] of Object.entries(rest)) assert.deepEqual(got[k], v, `${name}: ${k}`)
    if (segmentCount) assert.equal(got.segments.length, segmentCount, name)
    if (firstStart !== undefined) assert.equal(got.segments[0][0], firstStart, name)
  }
  const open = { segments: [[10, 20], [30, null]], end: null }
  assert.deepEqual(rowOf(open, 31_000).segments, [[10, 20], [30, NOW - 31_000]], 'stale closes the open segment')
  assert.deepEqual(rowOf(open, 1000).segments, [[10, 20], [30, null]], 'fresh keeps it open')
})

test('snapshots: only worktree sessions are listed', () => {
  const cases: [string, string, number][] = [
    ['T3 worktree', '/Users/me/.t3/worktrees/repo/t3-1', 1],
    ['.worktrees checkout', '/Users/me/repo/.worktrees/feat', 1],
    ['root checkout', '/Users/me/repo', 0],
  ]
  for (const [name, cwd, want] of cases) {
    const snap = { sessionId: 's', cwd, updatedAt: NOW, total: null, rows: [] }
    assert.equal(charts([snap], cwd).length, want, name)
  }
})

test('empty state', () => {
  for (const state of [null, {}, 'x']) assert.deepEqual(build({ state }).status, [])
})

test('repoUrlFromProject', () => {
  const md = readFileSync(join(import.meta.dirname, '../../../docs/agents/project.md'), 'utf8')
  assert.deepEqual(repoUrlFromProject(md), { url: 'https://github.com/collective-wisdom-org/collective-wisdom', isGithubIssues: true })
  assert.equal(repoUrlFromProject('# nothing here\n'), null)
  const repo = '| Repo | <https://github.com/o/r> |'
  const cases: [string, boolean][] = [
    ['| Tracker | `github` |', true],
    ['| Tracker (issues) | `GitHub` |', true],
    ['| Tracker | `linear` |', false],
    ['| Branch | `x` |', false],
    ['| Tracker | `linear` |\nTickets are GitHub issues', false],
  ]
  for (const [row, isGithubIssues] of cases) {
    assert.deepEqual(repoUrlFromProject(`${repo}\n${row}\n`), { url: 'https://github.com/o/r', isGithubIssues }, row)
  }
})

test('snapshots join the card of their worktree branch; the rest are dropped', () => {
  const porcelain = [
    'worktree /r\nHEAD a\nbranch refs/heads/main',
    'worktree /r/.worktrees/x\nHEAD b\nbranch refs/heads/feat/cw-7-thing',
    'worktree /h/.t3/worktrees/r/t3-1\nHEAD c\nbranch refs/heads/odd-name',
    'worktree /h/.t3/worktrees/r/t3-2\nHEAD d\nbranch refs/heads/feat/cw-9-off-board',
    'worktree /h/.t3/worktrees/r/t3-3\nHEAD e\ndetached',
  ].join('\n\n')
  const worktrees = parseWorktrees(porcelain)
  assert.deepEqual(worktrees.map((w) => w.path), ['/r', '/r/.worktrees/x', '/h/.t3/worktrees/r/t3-1', '/h/.t3/worktrees/r/t3-2'])
  const state = { tickets: { 'CW-7': { title: 't', stage: 'build', status: 'going. Risk: low' }, 'CW-8': { title: 't', stage: 'build', status: 'going. Risk: low', branch: 'odd-name' } } }
  const snap = (cwd: string, age = 0) => ({ sessionId: cwd, cwd, updatedAt: NOW - age, total: null, rows: [] })
  const cases: [string, string, string | null][] = [
    ['equal cwd, nested beats root, pattern', '/r/.worktrees/x', 'CW-7'],
    ['under worktree', '/r/.worktrees/x/src', 'CW-7'],
    ['state branch', '/h/.t3/worktrees/r/t3-1/a', 'CW-8'],
    ['not on board', '/h/.t3/worktrees/r/t3-2', null],
    ['detached skipped', '/h/.t3/worktrees/r/t3-3', null],
    ['sibling folder prefix', '/r/.worktrees/xy', null],
  ]
  for (const [name, cwd, want] of cases) {
    const api = build({ state, snapshots: [snap(cwd)], worktrees, prefix: 'CW' })
    const rows = api.status.flatMap((g) => g.rows) as any[]
    assert.equal(rows.find((r) => r.gantt)?.id ?? null, want, name)
    assert.ok(!('gantt' in api), name)
  }
  const two = build({ state, snapshots: [snap('/r/.worktrees/x', 0), snap('/r/.worktrees/x/b', 5000)], worktrees, prefix: 'CW' })
  assert.deepEqual((two.status[0].rows.find((r: any) => r.id === 'CW-7') as any).gantt.map((s: any) => s.sessionId), ['/r/.worktrees/x/b', '/r/.worktrees/x'])
})

test('a Cursor snapshot on a ticket worktree reaches the ticket gantt', () => {
  const cwd = '/h/.t3/worktrees/r/t3-1'
  const base = { conversation_id: 'c1', model: 'claude-sonnet-4', workspace_roots: [cwd] }
  const events = [{ hook_event_name: 'beforeSubmitPrompt', prompt: 'Fix it' }, { hook_event_name: 'stop' }]
  const state = events.reduce((s, e, i) => applyEvent(s, { ...base, ...e }, NOW - 5000 + i * 1000), emptyState())
  const snapshot = JSON.parse(cursorSnapshot(state, base, NOW - 4000, null))
  const gantt = (build({ state: stateOf('CW-7', { branch: 'b' }), snapshots: [snapshot], worktrees: [{ path: cwd, branch: 'b' }] }).status[0].rows[0] as any).gantt
  assert.deepEqual(gantt.map((s: any) => [s.sessionId, s.total, s.rows.map((r: any) => [r.name, r.harness, r.model, r.tokens])]), [['c1', null, [['Fix it', 'Cursor', 'sonnet-4', 0]]]])
})

test('a Cursor snapshot with open spans stays open however long since its last event; a Claude Code one is closed', () => {
  const cwd = '/h/.t3/worktrees/r/t3-1'
  const at = NOW - 5 * 60_000
  const row = (id: string, kind: string, harness: string) => ({ id, depth: 1, kind, name: id, repo: 'r', start: at - 1000, end: null, tokens: 0, cost: null, segments: [[at - 1000, null]], model: null, harness })
  // name, harness, then what the ticket's gantt shows: stale, the subagent's end, and the chief's state when the same rows sit in the root checkout
  const cases: [string, string, boolean, number | null, string][] = [
    ['Cursor', 'Cursor', false, null, 'running'],
    ['Claude Code', 'Claude Code', true, at, 'idle'],
  ]
  for (const [name, harness, stale, end, chief] of cases) {
    const rows = [row('main:task:0', 'task', harness), row('a1', 'agent', harness)]
    const snap = (dir: string) => ({ sessionId: 'c1', cwd: dir, updatedAt: at, total: null, rows })
    const gantt = (firstRow({ state: stateOf('CW-7', { branch: 'b' }), snapshots: [snap(cwd)], worktrees: [{ path: cwd, branch: 'b' }] }) as any).gantt
    assert.deepEqual([gantt[0].stale, gantt[0].rows.find((r: any) => r.id === 'a1').end, gantt[0].rows[0].end], [stale, end, end], name)
    assert.equal(build({ state: { chiefSessionId: 'c1' }, snapshots: [snap('/r')] }).chief.state, chief, name)
  }
})

test('merged entries get their ticket spend; a session off the board still matches for the ledger', () => {
  const entry = (id: string) => ({ id, title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 1 })
  const spend = { 'CW-1': { cost: null, tokens: 5 }, 'CW-2': { cost: 1.5, tokens: 9 } }
  const merged = build({ merged: [entry('CW-1'), entry('CW-2'), entry('CW-3'), entry('toString')], spend }).merged as any[]
  assert.deepEqual(merged.map((e) => e.spend ?? null), [{ cost: null, tokens: 5 }, { cost: 1.5, tokens: 9 }, null, null])
  assert.ok(!('spend' in merged[2]) && !('spend' in merged[3]))
  assert.ok(!('spend' in (build({ merged: [entry('CW-1')] }).merged[0])))

  const WT2 = '/Users/me/.t3/worktrees/repo/t3-2'
  const worktrees = [{ path: WT, branch: 'feat/cw-9-gone' }, { path: WT2, branch: 'odd' }]
  const state = { tickets: { 'CW-4': { branch: 'odd', stage: 'build' } } }
  const matchedTo = (cwd: string, prefix: string | null) =>
    ledgerSessions({ snapshots: [{ sessionId: 's', cwd, updatedAt: NOW, total: 1, rows: [] }], worktrees, state, prefix, now: NOW }).map((m) => m.ticket)
  assert.deepEqual(matchedTo(WT, 'CW'), ['CW-9'], 'off the board, by branch pattern')
  assert.deepEqual(matchedTo(WT2, null), ['CW-4'], 'by state branch')
  assert.deepEqual(matchedTo(WT, null), [], 'no prefix, no pattern')
  assert.deepEqual(matchedTo('/Users/me/repo', 'CW'), [], 'not a worktree session')
})

test('merged entries get their ticket sessions; one with none has no gantt key', () => {
  const entry = (id: string) => ({ id, title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 1 })
  const session = { sessionId: 'a', cwd: '/w', updatedAt: 1, stale: false, total: null, rows: [] }
  const merged = build({ merged: [entry('CW-1'), entry('CW-2'), entry('CW-3'), entry('toString')], history: { 'CW-1': [session], 'CW-3': [] } }).merged as any[]
  assert.deepEqual(merged.map((e) => e.gantt ?? null), [[session], null, null, null])
  for (const i of [1, 2, 3]) assert.ok(!('gantt' in merged[i]))
})

test('a row gets the detail kept for its id; the spec detail links to the spec commit, the changes detail to the PR', () => {
  const spec = { kind: 'spec' as const, sections: [{ name: 'Goal', text: 'g' }] }
  const changes = { kind: 'changes' as const, sections: [{ name: 'Summary', text: 's' }] }
  const on = { specPath: 'docs/superpowers/specs/a.md', specSha: 'a'.repeat(40), pr: 7 }
  const url = `https://github.com/o/r/blob/${'a'.repeat(40)}/docs/superpowers/specs/a.md`
  const cases: [string, Record<string, unknown>, typeof spec | typeof changes, Partial<Parameters<typeof buildApi>[0]>, string | undefined][] = [
    ['spec', on, spec, {}, url],
    ['spec, no repo', on, spec, { repo: null }, undefined],
    ['spec, no sha', { ...on, specSha: undefined }, spec, {}, undefined],
    ['changes', on, changes, {}, 'https://github.com/o/r/pull/7'],
    ['changes, no pr', { ...on, pr: null }, changes, {}, undefined],
  ]
  for (const [name, extra, detail, over, link] of cases) {
    const r = firstRow({ state: stateOf('CW-1', extra), details: { 'CW-1': detail }, ...over })
    assert.deepEqual(r.detail, link ? { ...detail, url: link } : detail, name)
  }
  assert.ok(!('detail' in firstRow({ state: stateOf('CW-1', on), details: { 'CW-2': spec, toString: spec } })))
  assert.ok(!('url' in spec), 'the shared detail is not changed')
})

test('specUrl on a row: a spec path and a 7 to 40 hex sha of the cos_handoff rules, with a repo', () => {
  const path = 'docs/superpowers/specs/a.md'
  const cases: [string, Record<string, unknown>, Partial<Parameters<typeof buildApi>[0]>, string | undefined][] = [
    ['valid', { specPath: path, specSha: 'a'.repeat(40) }, {}, `https://github.com/o/r/blob/${'a'.repeat(40)}/${path}`],
    ['short sha', { specPath: path, specSha: 'abc1234' }, {}, `https://github.com/o/r/blob/abc1234/${path}`],
    ['any stage', { stage: 'merge', specPath: path, specSha: 'abc1234' }, {}, `https://github.com/o/r/blob/abc1234/${path}`],
    ['no sha', { specPath: path }, {}, undefined],
    ['bad sha', { specPath: path, specSha: 'abc123g' }, {}, undefined],
    ['sha too short', { specPath: path, specSha: 'abc123' }, {}, undefined],
    ['bad path', { specPath: 'docs/a.md', specSha: 'abc1234' }, {}, undefined],
    ['dots in path', { specPath: 'docs/superpowers/specs/../a.md', specSha: 'abc1234' }, {}, undefined],
    ['no repo', { specPath: path, specSha: 'abc1234' }, { repo: null }, undefined],
  ]
  for (const [name, extra, over, want] of cases) assert.equal(firstRow({ state: stateOf('CW-1', extra), ...over }).specUrl, want, name)
})

test('a merged entry gets its detail and the spec link from the merge commit; the PR number stays internal', () => {
  const entry = { id: 'CW-1', title: 't', prUrl: 'https://github.com/o/r/pull/9', mergedAt: 1, number: 9 }
  const found = { kind: 'changes' as const, sections: [], spec: { path: 'docs/superpowers/specs/a.md', sha: 'b'.repeat(40) } }
  const [withIt] = build({ merged: [entry], details: { 'CW-1#9': found, 'CW-1': { kind: 'changes' as const, sections: [] } } }).merged as any[]
  assert.deepEqual(withIt, { id: 'CW-1', title: 't', prUrl: entry.prUrl, mergedAt: 1, detail: { kind: 'changes', sections: [], url: entry.prUrl }, specUrl: `https://github.com/o/r/blob/${'b'.repeat(40)}/docs/superpowers/specs/a.md` })
  const [bare] = build({ merged: [entry] }).merged as any[]
  assert.ok(!('number' in bare) && !('detail' in bare) && !('specUrl' in bare))
})

const ROOT = '/Users/me/repo'
const teamRow = (open: boolean) => ({ id: 'main:task:0', depth: 1, name: 'task', repo: 'r', start: 1, end: null, tokens: 1, cost: null, kind: 'task', segments: [[1, open ? null : 5]], model: null, harness: null })
const teamSnap = (sessionId: string, over: Record<string, unknown> = {}) => ({ sessionId, cwd: ROOT, updatedAt: NOW - 1000, total: null, rows: [teamRow(true)], threadId: null, heading: null, ...over })

test('team role rule: the chief by state, project manager children by heading, nothing else', () => {
  const state = { chiefSessionId: 'cs', chiefThreadId: 'ct' }
  const cases: [string, unknown, string | null][] = [
    ['chiefSessionId', teamSnap('cs'), 'chief'],
    ['chiefThreadId only', teamSnap('other', { threadId: 'ct' }), 'chief'],
    ['ranking heading', teamSnap('a', { heading: 'BACKLOG RANKING' }), 'ranking'],
    ['hygiene heading', teamSnap('b', { heading: 'PROJECT MANAGER HYGIENE' }), 'hygiene'],
    ['unknown heading', teamSnap('c', { heading: 'TEAM MODE' }), null],
    ['no heading', teamSnap('d'), null],
    ['worktree snapshot stays off the tab', teamSnap('e', { cwd: WT, heading: 'BACKLOG RANKING' }), null],
    ['rows not a list', teamSnap('f', { heading: 'BACKLOG RANKING', rows: {} }), null],
    ['bad thread id and heading type', teamSnap('g', { heading: 5, threadId: 'a b/../c' }), null],
    ['long heading', teamSnap('h', { heading: 'BACKLOG RANKING'.padEnd(41, 'X') }), null],
    ['not an object', 'x', null],
  ]
  for (const [name, snap, want] of cases) {
    const api = build({ state, snapshots: [snap] })
    const got = api.chief.gantt ? 'chief' : (api.pm[0]?.role ?? null)
    assert.equal(got, want, name)
    assert.equal(api.chief.gantt?.length ?? 0, want === 'chief' ? 1 : 0, name)
    assert.equal(api.pm.length, want === 'ranking' || want === 'hygiene' ? 1 : 0, name)
  }
  assert.deepEqual(teamSessions({ snapshots: cases.map((c) => c[1]), state, now: NOW }).map((t) => t.role).sort(), ['hygiene', 'ranking'])
})

test('chief state and the newest-first project manager list with live and history copies', () => {
  const chief = (state: unknown, snap: unknown) => build({ state, snapshots: [snap] }).chief
  assert.equal(chief({ paused: true, chiefSessionId: 'cs' }, teamSnap('cs')).state, 'paused')
  assert.equal(chief({ chiefSessionId: 'cs' }, teamSnap('cs')).state, 'running')
  assert.equal(chief({ chiefSessionId: 'cs' }, teamSnap('cs', { rows: [teamRow(false)] })).state, 'idle')
  assert.equal(chief({ chiefSessionId: 'cs' }, teamSnap('cs', { updatedAt: NOW - 61_000 })).state, 'idle')
  assert.deepEqual(chief({ chiefThreadId: 'ct' }, 'x'), { state: 'idle', threadLink: '<t3-thread://v2/env/ct>' })

  const hist = (sessionId: string, updatedAt: number, role: 'ranking' | 'hygiene' = 'ranking') => ({ role, session: { sessionId, cwd: ROOT, updatedAt, stale: false, total: null, pricing: null, rows: [], threadId: `th-${sessionId}` } })
  const api = build({
    snapshots: [teamSnap('live', { heading: 'BACKLOG RANKING', threadId: 'th-live', updatedAt: NOW - 1000 })],
    teamHistory: [hist('live', NOW - 40_000), hist('old', NOW - 900_000, 'hygiene'), hist('mid', NOW - 5000)],
  })
  assert.deepEqual(api.pm.map((p) => [p.sessionId, p.role, p.state, p.threadLink]), [
    ['live', 'ranking', 'running', '<t3-thread://v2/env/th-live>'],
    ['mid', 'ranking', 'finished', '<t3-thread://v2/env/th-mid>'],
    ['old', 'hygiene', 'finished', '<t3-thread://v2/env/th-old>'],
  ])
  assert.equal(api.pm[0].gantt[0].updatedAt, NOW - 1000)
})

test('a ticket whose PR is already in merged is dropped from status; its group goes when empty', () => {
  const t = (stage: string, pr: number) => ({ title: 't', stage, status: 'x. Risk: low', pr })
  const entry = (id: string, number: number) => ({ id, title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 1, number })
  const cases: [string, Record<string, unknown>, ReturnType<typeof entry>[], [string, number, string[]][]][] = [
    ['same id and PR: row and group go', { 'CW-1': t('merge', 243) }, [entry('CW-1', 243)], []],
    ['same id, other PR: stays', { 'CW-1': t('merge', 243) }, [entry('CW-1', 200)], [['Merging', 1, ['CW-1']]]],
    ['same PR, other id: stays', { 'CW-1': t('merge', 243) }, [entry('CW-2', 243)], [['Merging', 1, ['CW-1']]]],
    ['a second ticket keeps the group, count 1', { 'CW-1': t('merge', 243), 'CW-2': t('merge', 244) }, [entry('CW-1', 243)], [['Merging', 1, ['CW-2']]]],
  ]
  for (const [name, tickets, merged, want] of cases) {
    const { status } = build({ state: { tickets }, merged })
    assert.deepEqual(status.map((g) => [g.name, g.count, g.rows.map((r) => r.id)]), want, name)
  }
})

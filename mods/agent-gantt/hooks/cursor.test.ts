import assert from 'node:assert/strict'
import { test } from 'node:test'

import { applyEvent, cursorSnapshot, emptyState, hookOutput } from './cursor.ts'
import type { CursorPayload, CursorRun } from './cursor.ts'

const base = { conversation_id: 'c1', model: 'claude-sonnet-4', workspace_roots: ['/w/app'] }
const ev = (name: string, extra: Partial<CursorPayload> = {}): CursorPayload => ({ ...base, hook_event_name: name, ...extra })
const prompt = (text: string) => ev('beforeSubmitPrompt', { prompt: text })
const sub = (id: string, task: string, model = 'gpt-5') => ev('subagentStart', { subagent_id: id, subagent_type: 'explore', task, subagent_model: model })
const subStop = (task: string, duration_ms = 0) => ev('subagentStop', { subagent_type: 'explore', task, duration_ms })

type Want = [depth: number, name: string, start: number, end: number | null, segments: [number, number | null][], model: string | null]

test('cursor events become the rows the dashboard draws', () => {
  const cases: [string, [CursorPayload, number][], Want[]][] = [
    ['prompt then stop', [[prompt('Fix the build'), 10], [ev('stop'), 50]], [[1, 'Fix the build', 10, 50, [[10, 50]], 'sonnet-4']]],
    ['two prompts', [[prompt('one'), 10], [ev('stop'), 20], [prompt('two'), 30], [ev('stop'), 40]], [
      [1, 'one', 10, 20, [[10, 20]], 'sonnet-4'],
      [1, 'two', 30, 40, [[30, 40]], 'sonnet-4'],
    ]],
    ['each task keeps the model it began with', [[prompt('one'), 10], [ev('stop'), 20], [{ ...prompt('two'), model: 'gpt-5' }, 30], [{ ...ev('stop'), model: 'gpt-5' }, 40]], [
      [1, 'one', 10, 20, [[10, 20]], 'sonnet-4'],
      [1, 'two', 30, 40, [[30, 40]], 'gpt-5'],
    ]],
    ['subagent inside a task', [[prompt('go'), 10], [sub('s1', 'look around'), 20], [subStop('look around'), 30], [ev('stop'), 40]], [
      [1, 'go', 10, 40, [[10, 40]], 'sonnet-4'],
      [2, 'look around', 20, 30, [[20, 30]], 'gpt-5'],
    ]],
    ['stop with no start', [[prompt('go'), 100], [subStop('late', 40), 90], [ev('stop'), 120]], [
      [1, 'go', 100, 120, [[100, 120]], 'sonnet-4'],
      [2, 'late', 50, 90, [[50, 90]], null],
    ]],
    ['parallel subagents stop in order', [[prompt('go'), 10], [sub('a', 'same'), 20], [sub('b', 'same'), 25], [subStop('same'), 30], [subStop('same'), 35], [ev('stop'), 40]], [
      [1, 'go', 10, 40, [[10, 40]], 'sonnet-4'],
      [2, 'same', 20, 30, [[20, 30]], 'gpt-5'],
      [2, 'same', 25, 35, [[25, 35]], 'gpt-5'],
    ]],
    ['session end with a span open', [[prompt('go'), 10], [sub('a', 'work'), 20], [ev('sessionEnd'), 60]], [
      [1, 'go', 10, 60, [[10, 60]], 'sonnet-4'],
      [2, 'work', 20, 60, [[20, 60]], 'gpt-5'],
    ]],
    ['unknown event and missing id change nothing', [[prompt('go'), 10], [ev('preToolUse'), 15], [{ ...ev('stop'), conversation_id: undefined }, 20]], [
      [1, 'go', 10, null, [[10, null]], 'sonnet-4'],
    ]],
  ]
  for (const [name, events, want] of cases) {
    const state = events.reduce((s, [p, t]) => applyEvent(s, p, t), emptyState())
    const snap = JSON.parse(cursorSnapshot(state, base, 999, 'th:1'))
    const got = snap.rows.map((r: any) => [r.depth, r.name, r.start, r.end, r.segments, r.model])
    assert.deepEqual(got, want, name)
    for (const r of snap.rows) assert.deepEqual([r.harness, r.tokens, r.cost, r.repo], ['Cursor', 0, null, 'app'], name)
    assert.deepEqual([snap.sessionId, snap.cwd, snap.updatedAt, snap.total, snap.threadId], ['c1', '/w/app', 999, null, 'th:1'], name)
  }
})

const prices = { sonnet: { input: 2, output: 10, read: 0.1, write_1h: 4, write_5m: 2.5 } }
const run = (at: number, extra: Partial<CursorRun> = {}): CursorRun => ({ at, model: 'claude-sonnet-4', input: 0, output: 0, read: 0, write: 0, ...extra })
// 1M input at $2 and 100k output at $10: $3.00 over 1.1M tokens. 1M read at $0.10 and 400k written at the 5 minute $2.50: $1.10 over 1.4M tokens.
const A = { input: 1_000_000, output: 100_000 }
const B = { read: 1_000_000, write: 400_000 }

test('Cursor runs give the rows their tokens and cost, and the snapshot a total', () => {
  const two: [CursorPayload, number][] = [[prompt('one'), 10_000], [ev('stop'), 20_000], [prompt('two'), 100_000], [ev('stop'), 110_000]]
  // name, events, runs, prices, the rows as [name, tokens, cost], total, and the task (if any) to strip of its spans, as a slash command has
  const cases: [string, [CursorPayload, number][], CursorRun[] | null, typeof prices | null, [string, number, number | null][], number | null, number?][] = [
    ['each prompt gets its run', two, [run(10_000, A), run(100_000, B)], prices, [['one', 1_100_000, 3], ['two', 1_400_000, 1.1]], 4.1],
    ['a run that began 3 seconds before its prompt', two, [run(97_000, A)], prices, [['one', 0, 0], ['two', 1_100_000, 3]], 3],
    ['a run halfway between two prompts goes to the earlier', two, [run(55_000, A)], prices, [['one', 1_100_000, 3], ['two', 0, 0]], 3],
    ['a run with no task', [[ev('sessionStart'), 5]], [run(10_000, A)], prices, [['outside a task', 1_100_000, 3]], 3],
    ['an unpriced model keeps its tokens and blanks the cost', two, [run(10_000, A), run(100_000, { ...B, model: 'gpt-5' })], prices, [['one', 1_100_000, 3], ['two', 1_400_000, null]], null],
    ['no price table', two, [run(10_000, A)], null, [['one', 1_100_000, null], ['two', 0, null]], null],
    ['runs never read', two, null, prices, [['one', 0, null], ['two', 0, null]], null],
    ['a subagent has none of its own', [[prompt('go'), 10], [sub('s1', 'look'), 20], [subStop('look'), 30], [ev('stop'), 40]], [run(10, A)], prices, [['go', 1_100_000, 3], ['look', 0, 0]], 3],
    ['a task with no spans is skipped', two, [run(100_000, A)], prices, [['one', 1_100_000, 3]], 3, 1],
  ]
  for (const [name, events, runs, table, want, total, bare] of cases) {
    const full = { ...events.reduce((s, [p, t]) => applyEvent(s, p, t), emptyState()), runs }
    const state = { ...full, records: full.records.map(r => ({ ...r, tasks: r.tasks.map((k, i) => (i === bare ? { ...k, segments: [] } : k)) })) }
    const snap = JSON.parse(cursorSnapshot(state, base, 999, null, table))
    const got = snap.rows.map((r: any) => [r.name, r.tokens, r.cost === null ? null : Math.round(r.cost * 1e6) / 1e6])
    assert.deepEqual(got, want, name)
    assert.equal(snap.total === null ? null : Math.round(snap.total * 1e6) / 1e6, total, name)
  }
})

test('a state saved before runs existed reads as never read', () => {
  const { runs: _runs, ...old } = applyEvent(emptyState(), prompt('go'), 10)
  const snap = JSON.parse(cursorSnapshot(old as ReturnType<typeof emptyState>, base, 1, null, prices))
  assert.deepEqual([snap.rows[0].tokens, snap.rows[0].cost, snap.total], [0, null, null])
})

test('the heading comes from the first prompt only', () => {
  const state = [prompt('BACKLOG RANKING. Rank it.'), prompt('TEAM MODE. later')].reduce((s, p, i) => applyEvent(s, p, i * 10), emptyState())
  assert.equal(JSON.parse(cursorSnapshot(state, base, 1, null)).heading, 'BACKLOG RANKING')
})

test('hookOutput never blocks and answers only the events Cursor reads', () => {
  const cases: [string, string][] = [
    ['subagentStart', '{"permission":"allow"}'],
    ['beforeSubmitPrompt', '{"continue":true}'],
    ['sessionStart', ''],
    ['stop', ''],
    ['subagentStop', ''],
    ['sessionEnd', ''],
  ]
  for (const [event, want] of cases) assert.equal(hookOutput(event), want, event)
})

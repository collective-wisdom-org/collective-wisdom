import assert from 'node:assert/strict'
import { test } from 'node:test'

import { bars } from './format.ts'
import { buildRows } from './rows.ts'
import type { AgentRecord, Prices, Tokens } from '../types/index.d.ts'

const M = 1_000_000
const PRICES: Prices = {
  opus: { input: 4, output: 20, read: 0.2, write_1h: 8, write_5m: 5 },
}
const none: Tokens = { input: 0, output: 0, read: 0, write: 0 }

const rec = (id: string, over: Partial<AgentRecord> = {}): AgentRecord => ({
  id,
  parentId: id === 'main' ? null : 'main',
  name: id,
  type: 'general-purpose',
  cwd: '/Users/me/.t3/worktrees/app/t3-1234',
  start: 0,
  end: null,
  last: 0,
  usage: {},
  segments: [],
  tasks: [],
  taskIndex: null,
  ...over,
})

// Each case: records and the agent list in, the rows' fields out (only the ones the case is about).
const cases: {
  name: string
  records: AgentRecord[]
  agents: { id: string; parentId?: string }[]
  prices: Prices | null
  want: Record<string, unknown>[]
}[] = [
  {
    name: 'nests by depth, sorts by start, puts an orphan under main; no session row, no row has childCount',
    records: [
      rec('main'),
      rec('late', { start: 30 }),
      rec('child', { parentId: 'early', start: 25 }),
      rec('early', { start: 10 }),
      rec('orphan', { parentId: 'gone', start: 20 }),
    ],
    agents: [],
    prices: null,
    want: [
      { id: 'early', depth: 1, kind: 'agent', harness: 'T3 Code' },
      { id: 'child', depth: 2 },
      { id: 'orphan', depth: 1 },
      { id: 'late', depth: 1 },
    ],
  },
  {
    name: 'two tasks and a wait: two task rows (none for a task with no spans) and no session row, a subagent nests under its task with its own model',
    records: [
      rec('main', {
        usage: { 'claude-opus-5-5': { ...none, output: 9 } },
        segments: [[0, 10], [50, null]],
        tasks: [
          { name: 'one', start: 0, segments: [[0, 10]], usage: { 'claude-opus-5-5': { ...none, output: 4 } } },
          { name: 'two', start: 50, segments: [[50, null]], usage: { 'claude-opus-5-5': { ...none, output: 5 } } },
          { name: '/clear', start: 60, segments: [], usage: {} }, // a slash command that started no turn: no row
        ],
      }),
      rec('sub', { start: 55, end: 58, taskIndex: 1, usage: { 'claude-haiku-4-5': { ...none, output: 3 } } }),
      rec('lost', { start: 70, taskIndex: null }),
    ],
    agents: [],
    prices: null,
    want: [
      { id: 'main:task:0', depth: 1, kind: 'task', name: 'one', start: 0, end: 10, segments: [[0, 10]], tokens: 4 },
      { id: 'main:task:1', depth: 1, kind: 'task', name: 'two', start: 50, end: null, model: 'opus-5-5' },
      { id: 'sub', depth: 2, kind: 'agent', model: 'haiku-4-5', segments: [[55, 58]] },
      { id: 'lost', depth: 1, model: null, segments: [[70, null]] },
    ],
  },
  {
    name: 'one task carries main\'s work once; usage outside any task (or in a task with no spans) is one extra row',
    records: [
      rec('main', {
        usage: { 'claude-opus-5-5': { ...none, input: M, output: 7 } },
        segments: [[0, 10]],
        tasks: [{ name: 'only', start: 0, segments: [[0, 10]], usage: { 'claude-opus-5-5': { ...none, input: M, output: 4 } } }],
      }),
    ],
    agents: [],
    prices: PRICES,
    want: [
      { id: 'main:outside', depth: 1, kind: 'task', name: 'outside a task', tokens: 3, segments: [], cost: (3 * 20) / M },
      { id: 'main:task:0', name: 'only', tokens: M + 4 },
    ],
  },
  {
    name: 'no outside row when the tasks hold all of main\'s usage; its cost stays null without prices',
    records: [
      rec('main', {
        usage: { 'claude-opus-5-5': { ...none, output: 4 } },
        tasks: [{ name: 'only', start: 0, segments: [[0, 10]], usage: { 'claude-opus-5-5': { ...none, output: 4 } } }],
      }),
    ],
    agents: [],
    prices: null,
    want: [{ id: 'main:task:0', cost: null }],
  },
  {
    name: 'the model is the one with the most output tokens, not the most total',
    records: [
      rec('main', { usage: { 'claude-opus-5-5': { ...none, output: 5 }, 'claude-haiku-4-5': { ...none, input: M, output: 2 } } }),
    ],
    agents: [],
    prices: null,
    want: [{ id: 'main:outside', model: 'opus-5-5' }],
  },
  {
    name: 'a running agent keeps a null end next to a finished one; repo comes from the cwd',
    records: [
      rec('main', { cwd: '/Users/me/code/app/.worktrees/feat' }),
      rec('done', { start: 5, end: 9 }),
      rec('live', { start: 6 }),
    ],
    agents: [],
    prices: null,
    want: [
      { id: 'done', repo: 'app', start: 5, end: 9 },
      { id: 'live', repo: 'app', start: 6, end: null },
    ],
  },
  {
    name: 'cost is tokens times the family rates, with cache writes at the 1h rate',
    records: [
      rec('main', { usage: { 'claude-opus-5-5': { input: M, output: M, read: M, write: M } } }),
    ],
    agents: [],
    prices: PRICES,
    want: [{ id: 'main:outside', tokens: 4 * M, cost: 4 + 20 + 0.2 + 8 }],
  },
  {
    name: 'cost is null for an unknown model family, even beside a known one',
    records: [
      rec('main', { usage: { 'claude-opus-5-5': { ...none, input: M }, 'mystery-1': { ...none, input: M } } }),
      rec('known', { usage: { 'claude-opus-5-5': { ...none, input: M } } }),
    ],
    agents: [],
    prices: PRICES,
    want: [{ id: 'main:outside', tokens: 2 * M, cost: null }, { id: 'known', cost: 4 }],
  },
  {
    name: 'cost is null for every row without a price table',
    records: [rec('main', { usage: { 'claude-opus-5-5': { ...none, input: M } } })],
    agents: [],
    prices: null,
    want: [{ id: 'main:outside', tokens: M, cost: null }],
  },
]

for (const c of cases) {
  test(c.name, () => {
    const rows = buildRows(c.records, c.agents, c.prices, 'T3 Code')
    assert.ok(rows.every(row => !('childCount' in row)))
    assert.deepEqual(
      rows.map((row, i) => Object.fromEntries(Object.keys(c.want[i] ?? {}).map(k => [k, row[k as keyof typeof row]]))),
      c.want,
    )
  })
}

test('bars draws a run per segment and leaves the gap between them empty', () => {
  assert.equal(bars([[0, 10], [50, null]], 0, 100, 10), '█    █████')
  assert.equal(bars([[0, 0]], 0, 100, 10), '█')
})

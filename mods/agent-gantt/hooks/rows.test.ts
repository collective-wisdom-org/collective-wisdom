import assert from 'node:assert/strict'
import { test } from 'node:test'

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
    name: 'nests by depth, sorts by start, puts an orphan under main, counts children from the agent list',
    records: [
      rec('main'),
      rec('late', { start: 30 }),
      rec('child', { parentId: 'early', start: 25 }),
      rec('early', { start: 10 }),
      rec('orphan', { parentId: 'gone', start: 20 }),
    ],
    // `unrecorded` is listed under early but was never recorded.
    agents: [
      { id: 'early' }, { id: 'late' }, { id: 'orphan', parentId: 'gone' },
      { id: 'child', parentId: 'early' }, { id: 'unrecorded', parentId: 'early' },
    ],
    prices: null,
    want: [
      { id: 'main', depth: 0, childCount: 2 },
      { id: 'early', depth: 1, childCount: 2 },
      { id: 'child', depth: 2, childCount: 0 },
      { id: 'orphan', depth: 1, childCount: 0 },
      { id: 'late', depth: 1, childCount: 0 },
    ],
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
      { id: 'main', repo: 'app', end: null },
      { id: 'done', repo: 'app', start: 5, end: 9 },
      { id: 'live', repo: 'app', start: 6, end: null },
    ],
  },
  {
    name: 'cost is tokens times the family rates, with cache writes at the 5m rate',
    records: [
      rec('main', { usage: { 'claude-opus-5-5': { input: M, output: M, read: M, write: M } } }),
    ],
    agents: [],
    prices: PRICES,
    want: [{ id: 'main', tokens: 4 * M, cost: 4 + 20 + 0.2 + 5 }],
  },
  {
    name: 'cost is null for an unknown model family, even beside a known one, and without prices',
    records: [
      rec('main', { usage: { 'claude-opus-5-5': { ...none, input: M }, 'mystery-1': { ...none, input: M } } }),
      rec('known', { usage: { 'claude-opus-5-5': { ...none, input: M } } }),
    ],
    agents: [],
    prices: PRICES,
    want: [{ id: 'main', tokens: 2 * M, cost: null }, { id: 'known', cost: 4 }],
  },
  {
    name: 'cost is null for every row without a price table',
    records: [rec('main', { usage: { 'claude-opus-5-5': { ...none, input: M } } })],
    agents: [],
    prices: null,
    want: [{ id: 'main', tokens: M, cost: null }],
  },
]

for (const c of cases) {
  test(c.name, () => {
    const rows = buildRows(c.records, c.agents, c.prices)
    assert.deepEqual(
      rows.map((row, i) => Object.fromEntries(Object.keys(c.want[i] ?? {}).map(k => [k, row[k as keyof typeof row]]))),
      c.want,
    )
  })
}

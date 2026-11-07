import assert from 'node:assert/strict'
import { test } from 'node:test'

import { buildSnapshot, snapshotName } from './snapshot.ts'
import type { Row } from './rows.ts'

test('snapshotName accepts only safe session ids', () => {
  const cases: [string, string | null][] = [
    ['abc-123_X', 'abc-123_X.json'],
    ['a'.repeat(80), `${'a'.repeat(80)}.json`],
    ['', null],
    ['../x', null],
    ['a/b', null],
    ['a.b', null],
    ['a'.repeat(81), null],
    ['x\u0000', null],
    ['x\n', null],
  ]
  for (const [id, want] of cases) assert.equal(snapshotName(id), want, JSON.stringify(id))
})

test('buildSnapshot writes the session fields and the nine row fields', () => {
  const row: Row = { id: 'main', depth: 0, name: 'main', repo: 'app', start: 1, end: null, tokens: 5, cost: null, childCount: 0 }
  const got = JSON.parse(buildSnapshot({ sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, rows: [row] }))
  assert.deepEqual(got, { sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, rows: [row] })
  assert.deepEqual(Object.keys(got.rows[0]).sort(), ['childCount', 'cost', 'depth', 'end', 'id', 'name', 'repo', 'start', 'tokens'])
})

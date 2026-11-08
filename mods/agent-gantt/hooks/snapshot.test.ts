import assert from 'node:assert/strict'
import { test } from 'node:test'

import { buildSnapshot, pickHeading, snapshotName } from './snapshot.ts'
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

test('pickHeading takes a capital-letter heading from the first five lines only', () => {
  const t3 = 'Act as the research sub-agent for this task.\n\n'
  const cases: [string, string, string | null][] = [
    ['delegated ranking task', `${t3}BACKLOG RANKING. One-shot, read only.\nRank it.`, 'BACKLOG RANKING'],
    ['team mode', 'TEAM MODE. CONTINUE. Run /ship-loop for CW-1', 'TEAM MODE'],
    ['no heading', 'Please fix the build.\nThanks.', null],
    ['heading on line 6', 'a\nb\nc\nd\ne\nTEAM MODE. go', null],
    ['heading on line 5', 'a\nb\nc\nd\nTEAM MODE. go', 'TEAM MODE'],
  ]
  for (const [name, text, want] of cases) assert.equal(pickHeading(text), want, name)
})

test('buildSnapshot writes the session fields and the row fields', () => {
  const row: Row = { id: 'main', depth: 0, kind: 'session', name: 'main', repo: 'app', start: 1, end: null, tokens: 5, cost: null, segments: [[1, null]], model: null, harness: null }
  const got = JSON.parse(buildSnapshot({ sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, rows: [row], threadId: 'th:1', heading: null }))
  assert.deepEqual(got, { sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, pricing: 2, threadId: 'th:1', heading: null, rows: [row] })
  assert.deepEqual(Object.keys(got.rows[0]).sort(), ['cost', 'depth', 'end', 'harness', 'id', 'kind', 'model', 'name', 'repo', 'segments', 'start', 'tokens'])
})

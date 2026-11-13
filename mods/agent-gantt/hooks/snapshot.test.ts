import assert from 'node:assert/strict'
import { test } from 'node:test'

import { buildSnapshot, pickFiledTicket, pickHeading, pickRequest, snapshotName } from './snapshot.ts'
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

test('pickFiledTicket takes the first ticket id under Tickets in a TICKET HELPER DONE block', () => {
  const block = (tickets: string) => `TICKET HELPER DONE\nTickets: ${tickets}\nPlaced: no epic: none fits\nLinks: none\nLabels: bug\nAssumed: nothing\nNeeds the user: nothing`
  const cases: [string, string, string | null][] = [
    ['one ticket', block('CW-12: Fix the thing, https://example.test/12'), 'CW-12'],
    ['several tickets', block('\nCW-12: First, https://example.test/12\nCW-13: Second, https://example.test/13'), 'CW-12'],
    ['ticket on the next line', block('\n- CW-14: Bulleted, https://example.test/14'), 'CW-14'],
    ['none', block('none'), null],
    ['no block', 'Filed CW-12 for you.\nTickets: CW-12: Fix', null],
    ['text before the block', `Done.\n\n${block('CW-15: After text, https://example.test/15')}\n\nThe user's request, verbatim:\nCW-99 is slow`, 'CW-15'],
    ['id after the next key line', 'TICKET HELPER DONE\nTickets: none\nPlaced: CW-3: epic\nLinks: none', null],
  ]
  for (const [name, answer, want] of cases) assert.equal(pickFiledTicket(answer), want, name)
})

test('pickRequest takes the first non-empty line after the request marker', () => {
  const head = 'TICKET HELPER. Chief of Staff thread: t1\n\nRules.\n\n'
  const cases: [string, string, string | null][] = [
    ['user request', `${head}The user's request, verbatim:\n\n  Add   a dark\tmode\nMore detail`, 'Add a dark mode'],
    ['observation', `${head}The Chief of Staff's observation:\nA notice was lost`, 'A notice was lost'],
    ['cut to 80', `${head}The user's request, verbatim:\n${'x'.repeat(100)}`, 'x'.repeat(80)],
    ['no marker', `${head}Please do it.`, null],
    ['marker with nothing after', `${head}The user's request, verbatim:\n  \n`, null],
  ]
  for (const [name, text, want] of cases) assert.equal(pickRequest(text), want, name)
})

test('buildSnapshot writes the session fields and the row fields', () => {
  const row: Row = { id: 'main', depth: 0, kind: 'session', name: 'main', repo: 'app', start: 1, end: null, tokens: 5, cost: null, segments: [[1, null]], model: null, harness: null }
  const got = JSON.parse(buildSnapshot({ sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, rows: [row], threadId: 'th:1', heading: null, ticket: 'CW-9', request: null }))
  assert.deepEqual(got, { sessionId: 's1', cwd: '/a', updatedAt: 9, total: null, pricing: 2, threadId: 'th:1', heading: null, ticket: 'CW-9', request: null, rows: [row] })
  assert.deepEqual(Object.keys(got.rows[0]).sort(), ['cost', 'depth', 'end', 'harness', 'id', 'kind', 'model', 'name', 'repo', 'segments', 'start', 'tokens'])
})

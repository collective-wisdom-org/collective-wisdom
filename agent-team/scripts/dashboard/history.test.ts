import { test } from 'node:test'
import assert from 'node:assert/strict'
import { historyByTicket, parseHistory, recordHistory, recordTeamHistory, teamHistory } from './history.ts'
import type { History } from './history.ts'
import type { Session } from './api.ts'

const row = (end: number | null, segments: [number, number | null][] = [[1, end]]) => ({ id: 'r', depth: 0, name: 'n', repo: 'r', start: 1, end, tokens: 1, cost: null, kind: 'agent', segments, model: null, harness: null }) as Session['rows'][number]
const sess = (sessionId: string, updatedAt: number, rows = [row(2)], stale = false): Session => ({ sessionId, cwd: '/w', updatedAt, stale, total: 1, rows })

test('gantt history rules', () => {
  const cases: [string, History, [string, Session][], (h: History) => void][] = [
    ['seen twice is stored once', { sessions: {} }, [['CW-1', sess('a', 1)], ['CW-1', sess('a', 2)]], (h) => { assert.equal(Object.keys(h.sessions).length, 1); assert.equal(h.sessions.a.session.updatedAt, 2) }],
    ['older snapshot keeps the newer entry', { sessions: { a: { ticket: 'CW-1', session: sess('a', 9) } } }, [['CW-1', sess('a', 8)]], (h) => assert.equal(h.sessions.a.session.updatedAt, 9)],
    ['equal updatedAt replaces', { sessions: { a: { ticket: 'CW-1', session: sess('a', 9) } } }, [['CW-1', sess('a', 9, [row(3)])]], (h) => assert.equal(h.sessions.a.session.rows[0].end, 3)],
    ['newest 500 kept', { sessions: {} }, Array.from({ length: 501 }, (_, i): [string, Session] => ['CW-1', sess(`s${i}`, i)]), (h) => { assert.equal(Object.keys(h.sessions).length, 500); assert.ok(!('s0' in h.sessions)) }],
    ['per ticket oldest first, closed and not stale', { sessions: {} }, [['CW-1', sess('late', 9, [row(null, [[1, null]])], true)], ['CW-2', sess('other', 5)], ['CW-1', sess('early', 4)]], (h) => {
      const by = historyByTicket(h)
      assert.deepEqual(by['CW-1'].map((s) => s.sessionId), ['early', 'late'])
      assert.deepEqual(by['CW-2'].map((s) => s.sessionId), ['other'])
      const late = by['CW-1'][1]
      assert.equal(late.stale, false)
      assert.equal(late.rows[0].end, 9)
      assert.deepEqual(late.rows[0].segments, [[1, 9]])
    }],
    ['a ticket id that names an Object property does not throw', { sessions: {} }, [['__proto__', sess('p', 1)], ['toString', sess('q', 2)]], (h) => assert.deepEqual(Object.keys(historyByTicket(h)).sort(), ['__proto__', 'toString'])],
  ]
  for (const [name, history, matched, check] of cases) {
    try { check(recordHistory(history, matched.map(([ticket, session]) => ({ ticket, session })))) } catch (e) { throw new Error(`${name}: ${(e as Error).message}`) }
  }
})

test('parseHistory drops bad entries, cleans rows and gives empty for bad files', () => {
  const good = (id: string, over: Record<string, unknown> = {}) => ({ ticket: 'CW-1', session: { sessionId: id, cwd: '/w', updatedAt: 3, total: 1, rows: [], ...over } })
  const long = 'x'.repeat(200)
  const file = JSON.stringify({ sessions: { ok: good('ok'), ticket: { ...good('ticket'), ticket: 'x' }, id: good('other'), cwd: good('cwd', { cwd: 1 }), time: good('time', { updatedAt: -1 }), nan: good('nan', { updatedAt: 'x' }), rows: good('rows', { rows: {} }), str: 'x', clean: good('clean', { rows: [{ name: long, kind: 'bogus' }, 5] }) } })
  const got = parseHistory(file)
  assert.deepEqual(Object.keys(got.sessions).sort(), ['clean', 'ok'])
  assert.equal(got.sessions.clean.session.rows.length, 1)
  assert.equal(got.sessions.clean.session.rows[0].name.length, 60)
  assert.equal(got.sessions.clean.session.rows[0].kind, 'agent')
  // A stored pricing version survives a reload; a missing or bad one reads as null, so only older entries get the page note.
  const priced = parseHistory(JSON.stringify({ sessions: { a: good('a', { pricing: 2 }), b: good('b'), c: good('c', { pricing: 'x' }) } }))
  assert.deepEqual(['a', 'b', 'c'].map((id) => priced.sessions[id].session.pricing), [2, null, null])
  for (const text of ['', '{"sessions":', 'null', '[]', '{"sessions":[]}', '{"sessions":5}']) assert.deepEqual(parseHistory(text), { sessions: {} }, text)
})

test('project manager entries parse next to ticket entries, keep their own cap and never push ticket sessions out', () => {
  const body = (id: string, over: Record<string, unknown> = {}) => ({ sessionId: id, cwd: '/r', updatedAt: 3, total: 1, rows: [], ...over })
  const file = JSON.stringify({ sessions: {
    t: { ticket: 'CW-1', session: body('t') },
    r: { role: 'ranking', session: body('r', { threadId: 'thread:x%3Ay' }) },
    h: { role: 'hygiene', session: body('h', { threadId: 'bad id' }) },
    k: { role: 'helper', session: body('k') },
    bad: { role: 'chief', session: body('bad') },
    both: { ticket: 'x', role: 'ranking', session: body('both') },
    none: { session: body('none') },
  } })
  const parsed = parseHistory(file)
  assert.deepEqual(Object.keys(parsed.sessions).sort(), ['h', 'k', 'r', 't'])
  assert.equal(parsed.sessions.r.session.threadId, 'thread:x%3Ay')
  assert.equal(parsed.sessions.h.session.threadId, undefined)
  assert.deepEqual(Object.keys(historyByTicket(parsed)), ['CW-1'])

  let history: History = recordHistory({ sessions: {} }, Array.from({ length: 500 }, (_, i) => ({ ticket: 'CW-1', session: sess(`t${i}`, 1000 + i) })))
  history = recordTeamHistory(history, Array.from({ length: 51 }, (_, i) => ({ role: 'ranking' as const, session: sess(`p${i}`, i, [row(null)]) })))
  assert.equal(Object.keys(history.sessions).length, 550)
  assert.ok(!('p0' in history.sessions) && 'p1' in history.sessions && 't0' in history.sessions)
  assert.equal(teamHistory(history).length, 50)
  assert.equal(teamHistory(history)[0].session.rows[0].end, teamHistory(history)[0].session.updatedAt)
  history = recordTeamHistory(history, Array.from({ length: 51 }, (_, i) => ({ role: 'helper' as const, session: sess(`k${i}`, i) })))
  assert.equal(Object.keys(history.sessions).length, 600)
  assert.ok(!('k0' in history.sessions) && 'k1' in history.sessions && 'p1' in history.sessions && 't0' in history.sessions)
})

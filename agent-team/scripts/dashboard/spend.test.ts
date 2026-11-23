import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseLedger, recordSpend, spendByTicket } from './spend.ts'
import type { Ledger } from './spend.ts'
import type { Session } from './api.ts'

const row = (kind: 'session' | 'task' | 'agent', tokens: number) => ({ id: 'r', depth: 0, name: 'n', repo: 'r', start: 0, end: 1, tokens, cost: null, kind, segments: [], model: null, harness: null }) as Session['rows'][number]
const sess = (sessionId: string, updatedAt: number, total: number | null, rows = [row('session', 100)]): Session => ({ sessionId, cwd: '/w', updatedAt, stale: false, total, rows })
const entry = (ticket: string, cost: number | null, tokens: number, updatedAt: number, claude = cost) => ({ ticket, cost, claude, tokens, updatedAt })
const cursorRow = () => ({ ...row('session', 100), harness: 'Cursor' }) as Session['rows'][number]

test('spend ledger rules', () => {
  const cases: [string, Ledger, [string, Session][], (l: Ledger) => void][] = [
    ['seen twice counts once', { sessions: {} }, [['CW-1', sess('a', 1, 1)], ['CW-1', sess('a', 2, 2)]], (l) => assert.deepEqual(spendByTicket(l), { 'CW-1': { cost: 2, claude: 2, tokens: 100 } })],
    ['older snapshot keeps the newer entry', { sessions: { a: entry('CW-1', 5, 500, 9) } }, [['CW-1', sess('a', 8, 1)]], (l) => assert.deepEqual(l.sessions.a, entry('CW-1', 5, 500, 9))],
    ['equal updatedAt replaces', { sessions: { a: entry('CW-1', 5, 500, 9) } }, [['CW-1', sess('a', 9, 6)]], (l) => assert.equal(l.sessions.a.cost, 6)],
    ['task rows are the main loop work when there is no session row', { sessions: {} }, [['CW-1', sess('a', 1, 1, [row('task', 10), row('task', 4), row('agent', 5)])]], (l) => assert.equal(l.sessions.a.tokens, 19)],
    ['task rows left out of tokens beside a session row', { sessions: {} }, [['CW-1', sess('a', 1, 1, [row('session', 10), row('task', 99), row('agent', 5)])]], (l) => assert.equal(l.sessions.a.tokens, 15)],
    ['ticket total sums its sessions only', { sessions: {} }, [['CW-1', sess('a', 1, 1.5)], ['CW-1', sess('b', 1, 2)], ['CW-2', sess('c', 1, 7)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: 3.5, claude: 3.5, tokens: 200 })],
    ['null cost among known costs', { sessions: {} }, [['CW-1', sess('a', 1, null)], ['CW-1', sess('b', 1, 2)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: 2, claude: 2, tokens: 200 })],
    ['all costs null', { sessions: {} }, [['CW-1', sess('a', 1, null)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: null, claude: null, tokens: 100 })],
    ['a Cursor session counts none of its cost as Claude Code', { sessions: {} }, [['CW-1', sess('a', 1, 4, [cursorRow()])]], (l) => assert.deepEqual(l.sessions.a, entry('CW-1', 4, 100, 1, 0))],
    ['a mixed ticket sums the Claude Code part only', { sessions: {} }, [['CW-1', sess('a', 1, 10)], ['CW-1', sess('b', 1, 5, [cursorRow()])]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: 15, claude: 10, tokens: 200 })],
    ['a null cost has a null claude part', { sessions: {} }, [['CW-1', sess('a', 1, null, [cursorRow()])]], (l) => assert.equal(l.sessions.a.claude, null)],
    ['newest 2000 kept', { sessions: {} }, Array.from({ length: 2001 }, (_, i): [string, Session] => ['CW-1', sess(`s${i}`, i, 1)]), (l) => { assert.equal(Object.keys(l.sessions).length, 2000); assert.ok(!('s0' in l.sessions)) }],
  ]
  for (const [name, ledger, matched, check] of cases) {
    try { check(recordSpend(ledger, matched.map(([ticket, session]) => ({ ticket, session })))) } catch (e) { throw new Error(`${name}: ${(e as Error).message}`) }
  }
})

test('parseLedger drops bad entries and bad files', () => {
  const good = entry('CW-1', 1, 2, 3)
  const file = JSON.stringify({ sessions: { ok: good, nullcost: { ...good, cost: null }, ticket: { ...good, ticket: 'x' }, neg: { ...good, tokens: -1 }, time: { ...good, updatedAt: 'x' }, cost: { ...good, cost: '1' }, str: 'x' } })
  assert.deepEqual(Object.keys(parseLedger(file).sessions).sort(), ['nullcost', 'ok'])
  const { claude: _, ...old } = good
  const split = JSON.stringify({ sessions: { old, cursor: { ...good, claude: 0 }, nullclaude: { ...good, claude: null }, bad: { ...good, claude: '1' }, neg: { ...good, claude: -1 } } })
  const read = parseLedger(split).sessions
  assert.deepEqual(Object.keys(read).sort(), ['cursor', 'nullclaude', 'old'])
  assert.deepEqual([read.old.claude, read.cursor.claude, read.nullclaude.claude], [1, 0, null])
  for (const text of ['', '{"sessions":', 'null', '[]', '{"sessions":[]}', '{"sessions":5}']) assert.deepEqual(parseLedger(text), { sessions: {} }, text)
})

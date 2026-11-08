import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseLedger, recordSpend, spendByTicket } from './spend.ts'
import type { Ledger } from './spend.ts'
import type { Session } from './api.ts'

const row = (kind: 'session' | 'task' | 'agent', tokens: number) => ({ id: 'r', depth: 0, name: 'n', repo: 'r', start: 0, end: 1, tokens, cost: null, kind, segments: [], model: null, harness: null }) as Session['rows'][number]
const sess = (sessionId: string, updatedAt: number, total: number | null, rows = [row('session', 100)]): Session => ({ sessionId, cwd: '/w', updatedAt, stale: false, total, rows })
const entry = (ticket: string, cost: number | null, tokens: number, updatedAt: number) => ({ ticket, cost, tokens, updatedAt })

test('spend ledger rules', () => {
  const cases: [string, Ledger, [string, Session][], (l: Ledger) => void][] = [
    ['seen twice counts once', { sessions: {} }, [['CW-1', sess('a', 1, 1)], ['CW-1', sess('a', 2, 2)]], (l) => assert.deepEqual(spendByTicket(l), { 'CW-1': { cost: 2, tokens: 100 } })],
    ['older snapshot keeps the newer entry', { sessions: { a: entry('CW-1', 5, 500, 9) } }, [['CW-1', sess('a', 8, 1)]], (l) => assert.deepEqual(l.sessions.a, entry('CW-1', 5, 500, 9))],
    ['equal updatedAt replaces', { sessions: { a: entry('CW-1', 5, 500, 9) } }, [['CW-1', sess('a', 9, 6)]], (l) => assert.equal(l.sessions.a.cost, 6)],
    ['task rows left out of tokens', { sessions: {} }, [['CW-1', sess('a', 1, 1, [row('session', 10), row('task', 99), row('agent', 5)])]], (l) => assert.equal(l.sessions.a.tokens, 15)],
    ['ticket total sums its sessions only', { sessions: {} }, [['CW-1', sess('a', 1, 1.5)], ['CW-1', sess('b', 1, 2)], ['CW-2', sess('c', 1, 7)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: 3.5, tokens: 200 })],
    ['null cost among known costs', { sessions: {} }, [['CW-1', sess('a', 1, null)], ['CW-1', sess('b', 1, 2)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: 2, tokens: 200 })],
    ['all costs null', { sessions: {} }, [['CW-1', sess('a', 1, null)]], (l) => assert.deepEqual(spendByTicket(l)['CW-1'], { cost: null, tokens: 100 })],
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
  for (const text of ['', '{"sessions":', 'null', '[]', '{"sessions":[]}', '{"sessions":5}']) assert.deepEqual(parseLedger(text), { sessions: {} }, text)
})

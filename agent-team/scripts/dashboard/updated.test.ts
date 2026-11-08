import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createUpdated } from './updated.ts'

const CFG = { prefix: 'CW', slug: 'o/r' }
const T = '2026-11-08T10:00:00Z'

test('issue update times: bad entries dropped, failed read keeps the map, one read a minute', async () => {
  let clock = 0
  const calls: string[][] = []
  let reply: string | Error = JSON.stringify([{ number: 1, updatedAt: T }, { number: 'x', updatedAt: T }, { number: 2, updatedAt: 'nope' }, { number: 3 }, null])
  const u = createUpdated({ now: () => clock, run: async (args) => { calls.push(args); if (reply instanceof Error) throw reply; return reply } })

  u.want(null)
  u.want(CFG)
  u.want(CFG)
  await u.idle()
  assert.deepEqual(calls, [['issue', 'list', '--repo', 'o/r', '--state', 'all', '--limit', '100', '--search', 'sort:updated-desc', '--json', 'number,updatedAt']])
  assert.deepEqual(u.get(), { 'CW-1': Date.parse(T) })

  for (const bad of [new Error('boom'), 'not json']) {
    reply = bad
    const before = calls.length
    clock += 59_000
    u.want(CFG)
    await u.idle()
    assert.equal(calls.length, before)
    clock += 2_000
    u.want(CFG)
    await u.idle()
    assert.equal(calls.length, before + 1)
    assert.deepEqual(u.get(), { 'CW-1': Date.parse(T) })
  }
})

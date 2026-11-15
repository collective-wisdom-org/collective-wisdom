import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createOpenPrs, parseOpen } from './open.ts'

const CFG = { prefix: 'CW', slug: 'o/r', issueUrls: true }
const pr = (number: unknown, headRefName: unknown, login?: unknown) => ({ number, headRefName, author: login === undefined ? null : { login } })

test('parseOpen: ticket id from the head branch, junk skipped, higher number wins', () => {
  const list = [pr(5, 'feat/cw-1-x'), pr(9, 'feat/cw-1-y'), pr(7, 'fix/cw-2-x'), pr(8, 'feat/ab-3-x'), pr(10, 'feat/other'), pr(0, 'feat/cw-4-x'), pr('11', 'feat/cw-5-x'), pr(12, 'feat/cw-60-x'), null]
  assert.deepEqual(parseOpen(JSON.stringify(list), CFG), { 'CW-1': { number: 9 }, 'CW-60': { number: 12 } })
  assert.deepEqual(parseOpen(JSON.stringify([pr(7, 'fix/cw-2-x')]), { ...CFG, heads: ['feat/', 'fix/'] }), { 'CW-2': { number: 7 } })
  assert.equal(parseOpen('not json', CFG), null)
  assert.equal(parseOpen('{}', CFG), null)
})

test('parseOpen owners: the author of the higher PR, none for a bot or a missing author', () => {
  const list = [pr(5, 'feat/cw-1-x', 'old'), pr(9, 'feat/cw-1-y', 'noah'), pr(2, 'feat/cw-2-x', 'app/dependabot'), pr(3, 'feat/cw-3-x'), pr(4, 'feat/cw-4-x', 'a;b')]
  assert.deepEqual(parseOpen(JSON.stringify(list), CFG), { 'CW-1': { number: 9, owner: 'noah' }, 'CW-2': { number: 2 }, 'CW-3': { number: 3 }, 'CW-4': { number: 4 } })
})

test('open reader: a failed read keeps the map; a second want inside a minute does not read', async () => {
  let clock = 1_000_000
  let calls = 0
  let reply: string | Error = JSON.stringify([pr(3, 'feat/cw-3-x', 'noah')])
  const o = createOpenPrs({ now: () => clock, run: async () => { calls++; if (reply instanceof Error) throw reply; return reply } })
  o.want(null)
  o.want(CFG)
  await o.idle()
  o.want(CFG)
  await o.idle()
  assert.equal(calls, 1)
  assert.deepEqual(o.get(), { 'CW-3': 3 })
  assert.deepEqual(o.owners(), { 'CW-3': 'noah' })
  reply = new Error('gh down')
  clock += 61_000
  o.want(CFG)
  await o.idle()
  assert.equal(calls, 2)
  assert.deepEqual(o.get(), { 'CW-3': 3 })
})

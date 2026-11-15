import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createViewer } from './viewer.ts'

test('viewer: read once and kept; a failure or a non-login is retried after 5 minutes', async () => {
  let clock = 0
  let reply: string | Error = new Error('gh down')
  let calls = 0
  const v = createViewer({ now: () => clock, run: async () => { calls++; if (reply instanceof Error) throw reply; return reply } })
  const step = async (at: number, next: string | Error, wantCalls: number, want: string | null) => {
    clock = at
    reply = next
    v.want()
    await v.idle()
    assert.deepEqual([calls, v.get()], [wantCalls, want], `at ${at}`)
  }
  await step(1, new Error('gh down'), 1, null)
  await step(200_000, 'Noah\n', 1, null)
  await step(301_001, 'app/x', 2, null)
  await step(400_000, 'Noah\n', 2, null)
  await step(601_002, 'Noah\n', 3, 'Noah')
  await step(900_000, 'Other', 3, 'Noah')
})

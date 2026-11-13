import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createBacklog } from './backlog.ts'

const CFG = { prefix: 'CW', slug: 'o/r' }
const issue = (number: number, login: string | null, labels: string[] = [], title = `t${number}`) => ({ number, title, labels: labels.map((name) => ({ name })), author: login === null ? null : { login } })

test('backlog: Todo and Backlog from the issue list, team authors only, last good list kept on a failed read', async () => {
  let clock = 0
  const calls: string[][] = []
  let list: unknown = [
    issue(1, 'ann', ['status:todo']),
    issue(2, 'ann', ['type:bug'], 'Fix\x1b]8;;x\x07 it\n'),
    issue(3, 'ann', ['status:in-progress']),
    issue(4, 'ann', ['status:todo', 'status:in-review']),
    issue(5, 'eve'),
    issue(6, 'bob'),
    issue(7, null),
    issue(8, '../x'),
    issue(9, 'ann', [], 'last'),
  ]
  const roles: Record<string, string | Error> = { ann: 'write\n', eve: 'read', bob: new Error('404') }
  const b = createBacklog({ now: () => clock, run: async (args) => {
    calls.push(args)
    if (args[0] === 'issue') { if (list instanceof Error) throw list; return JSON.stringify(list) }
    const r = roles[args[1].split('/')[4]]
    if (r instanceof Error) throw r
    return r
  } })

  assert.deepEqual(b.get(), [])
  b.want(null)
  await b.idle()
  assert.equal(calls.length, 0)

  b.want(CFG)
  await b.idle()
  assert.deepEqual(calls[0], ['issue', 'list', '--repo', 'o/r', '--state', 'open', '--limit', '200', '--json', 'number,title,labels,author'])
  assert.deepEqual(calls.filter((c) => c[0] === 'api'), [['api', 'repos/o/r/collaborators/ann/permission', '--jq', '.role_name'], ['api', 'repos/o/r/collaborators/eve/permission', '--jq', '.role_name'], ['api', 'repos/o/r/collaborators/bob/permission', '--jq', '.role_name']])
  assert.deepEqual(b.get(), [{ id: 'CW-1', title: 't1', state: 'Todo' }, { id: 'CW-2', title: 'Fix ]8;;x  it', state: 'Backlog' }, { id: 'CW-9', title: 'last', state: 'Backlog' }])

  // At most once a minute; a failed read keeps the list; a team login's answer is cached for good, a refusal for 5 minutes.
  const n = calls.length
  clock = 59_000
  b.want(CFG)
  await b.idle()
  assert.equal(calls.length, n)
  clock = 61_000
  list = new Error('boom')
  b.want(CFG)
  await b.idle()
  assert.equal(calls.length, n + 1)
  assert.equal(b.get().length, 3)
  list = 'not json'
  clock = 122_000
  b.want(CFG)
  await b.idle()
  list = [issue(10, 'ann'), issue(11, 'eve')]
  clock = 301_000
  b.want(CFG)
  await b.idle()
  assert.deepEqual(b.get().map((i) => i.id), ['CW-10'])
  assert.equal(calls.filter((c) => c[1]?.includes('/ann/')).length, 1)
  assert.equal(calls.filter((c) => c[1]?.includes('/eve/')).length, 2)
  b.want(null)
  assert.deepEqual(b.get(), [])
})

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createBacklog } from './backlog.ts'

const CFG = { prefix: 'CW', slug: 'o/r' }
const issue = (number: number, login: string | null, labels: string[] = [], title = `t${number}`, createdAt?: unknown) => ({ number, title, labels: labels.map((name) => ({ name })), author: login === null ? null : { login }, createdAt })

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
  assert.deepEqual(calls[0], ['issue', 'list', '--repo', 'o/r', '--state', 'open', '--limit', '200', '--json', 'number,title,labels,author,createdAt'])
  assert.deepEqual(calls.filter((c) => c[1]?.includes('/collaborators/')), [['api', 'repos/o/r/collaborators/ann/permission', '--jq', '.role_name'], ['api', 'repos/o/r/collaborators/eve/permission', '--jq', '.role_name'], ['api', 'repos/o/r/collaborators/bob/permission', '--jq', '.role_name']])
  assert.deepEqual(b.get(), [{ id: 'CW-1', title: 't1', state: 'Todo', priority: null, createdAt: null, owner: 'ann' }, { id: 'CW-2', title: 'Fix ]8;;x  it', state: 'Backlog', priority: null, createdAt: null, owner: 'ann' }, { id: 'CW-9', title: 'last', state: 'Backlog', priority: null, createdAt: null, owner: 'ann' }])

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

test('backlog: priority comes from the highest known priority: label, createdAt is ms or null', async () => {
  const day = '2026-11-13T10:00:00Z'
  const cases: [string, string[], unknown, string | null, number | null][] = [
    ['urgent', ['priority:urgent'], day, 'urgent', Date.parse(day)],
    ['high', ['priority:high'], day, 'high', Date.parse(day)],
    ['medium', ['priority:medium'], day, 'medium', Date.parse(day)],
    ['low', ['priority:low'], day, 'low', Date.parse(day)],
    ['no priority label', ['type:bug'], day, null, Date.parse(day)],
    ['unknown value ignored', ['priority:whenever'], day, null, Date.parse(day)],
    ['two labels: the highest wins', ['priority:low', 'priority:high', 'priority:whatever'], day, 'high', Date.parse(day)],
    ['unparseable date', [], 'yesterday', null, null],
    ['missing date', [], undefined, null, null],
  ]
  const b = createBacklog({ run: async (args) => (args[0] === 'issue' ? JSON.stringify(cases.map(([, labels, createdAt], i) => issue(i + 1, 'ann', labels, undefined, createdAt))) : 'write') })
  b.want(CFG)
  await b.idle()
  assert.deepEqual(b.get().map((i) => [i.priority, i.createdAt]), cases.map(([, , , priority, at]) => [priority, at]))
})

test('backlog: a new change stamp reads at once, one more read after a running one, a failed read sets error() until a good one', async () => {
  let clock = 0
  let reads = 0
  let fail: unknown = null
  let gate: Promise<void> | null = null
  const b = createBacklog({ now: () => clock, run: async (args) => {
    if (args[0] !== 'issue') return 'write'
    reads++
    await gate
    if (fail) throw fail
    return JSON.stringify([issue(reads, 'ann')])
  } })

  b.want(CFG, null)
  await b.idle()
  assert.equal(reads, 1)
  b.want(CFG, 'a')
  await b.idle()
  assert.equal(reads, 2, 'the first stamp, after none, reads at once')
  for (const same of ['a', 'a', null]) { b.want(CFG, same); await b.idle() }
  assert.equal(reads, 2, 'the same stamp, or none, reads nothing inside the minute')
  b.want(CFG, 'b')
  await b.idle()
  assert.equal(reads, 3, 'a new stamp reads at once')

  let open!: () => void
  gate = new Promise((r) => (open = r))
  b.want(CFG, 'c')
  b.want(CFG, 'd')
  b.want(CFG, 'e')
  gate = null
  open()
  await b.idle()
  assert.equal(reads, 5, 'stamps during a read cost exactly one more read')
  assert.deepEqual(b.get().map((i) => i.id), ['CW-5'])

  fail = new Error('Command failed: /Users/x/gh.sh issue list --repo a/b\nHTTP 502\nsecond line')
  b.want(CFG, 'f')
  await b.idle()
  assert.equal(b.error(), 'Could not read Todo and Backlog from GitHub: HTTP 502. Showing the last list read.')
  assert.deepEqual(b.get().map((i) => i.id), ['CW-5'])
  fail = new Error(`\x1b[31m${'x'.repeat(200)}`)
  b.want(CFG, 'g')
  await b.idle()
  assert.equal(b.error(), `Could not read Todo and Backlog from GitHub: [31m${'x'.repeat(116)}. Showing the last list read.`)
  fail = null
  clock = 61_000
  b.want(CFG)
  await b.idle()
  assert.equal(b.error(), null)
  b.want(null)
  assert.equal(b.error(), null)
})

test('backlog: relations read leaves epics out, maps children to their epic, keeps open blockers, and survives a failed call', async () => {
  const calls: string[][] = []
  let list = [issue(1, 'ann', [], 'Epic\x1b one'), issue(2, 'ann'), issue(3, 'ann', ['status:todo']), issue(4, 'ann')]
  let failAt: string | null = null
  const rel = (number: number, title: string, total: number, blocked: number) => JSON.stringify({ number, title, total, blocked })
  const blockers = [{ number: 2, title: 'in repo', state: 'open', repository_url: 'https://api.github.com/repos/o/r' }, { number: 9, title: 'closed', state: 'closed', repository_url: 'https://api.github.com/repos/o/r' }, { number: 7, title: 'other\nrepo', state: 'open', repository_url: 'https://api.github.com/repos/x/y' }]
  const b = createBacklog({ run: async (args) => {
    calls.push(args)
    if (args[0] === 'issue') return JSON.stringify(list)
    const path = args[1]
    if (failAt && path.includes(failAt)) throw new Error('boom')
    if (path.includes('/collaborators/')) return 'write'
    if (path.includes('/1/sub_issues')) return '[2,3]'
    if (path.includes('/3/dependencies/blocked_by')) return blockers.map((x) => JSON.stringify(x)).join('\n')
    return [rel(1, 'Epic\x1b one', 2, 0), rel(2, 't2', 0, 0), rel(3, 't3', 0, 2), rel(4, 't4', 0, 0)].join('\n')
  } })

  b.want(CFG)
  await b.idle()
  assert.deepEqual(b.get().map((i) => i.id), ['CW-2', 'CW-3', 'CW-4'])
  assert.deepEqual(b.relations(), {
    'CW-1': { blockedBy: [] },
    'CW-2': { epic: { id: 'CW-1', title: 'Epic  one' }, blockedBy: [] },
    'CW-3': { epic: { id: 'CW-1', title: 'Epic  one' }, blockedBy: [{ id: 'CW-2', title: 'in repo' }, { id: 'x/y#7', title: 'other repo' }] },
    'CW-4': { blockedBy: [] },
  })
  const related = calls.filter((c) => c[0] === 'api' && !c[1].includes('/collaborators/')).map((c) => c[1])
  assert.deepEqual(related, ['repos/o/r/issues?state=open&per_page=100', 'repos/o/r/issues/1/sub_issues', 'repos/o/r/issues/3/dependencies/blocked_by'])

  // A failed relations call: the list still updates, the epic stays hidden, no icons, no error line.
  list = [...list, issue(5, 'ann')]
  failAt = '/sub_issues'
  b.want(CFG, 'next')
  await b.idle()
  assert.deepEqual(b.get().map((i) => i.id), ['CW-2', 'CW-3', 'CW-4', 'CW-5'])
  assert.deepEqual(b.relations(), {})
  assert.equal(b.error(), null)
  b.want(null)
  assert.deepEqual(b.relations(), {})
})

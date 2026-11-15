import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createTitles, headsFromProject } from './titles.ts'

const CFG = { prefix: 'CW', slug: 'o/r' }

test('tracker titles: cached, prefix-guarded, cleaned, failures retried after 5 minutes', async () => {
  let clock = 0
  const calls: string[][] = []
  const issue = (title: string, login: unknown = 'noah') => JSON.stringify({ title, author: login === null ? null : { login } })
  let reply: string | Error = issue('Add\x1b]8;;x\x07 thing\n')
  const t = createTitles({ now: () => clock, run: async (args) => { calls.push(args); if (reply instanceof Error) throw reply; return reply } })

  t.want(['CW-1', 'CW-1', 'ABC-2', 'CW-3x', 'CW-4; rm'], CFG)
  await t.idle()
  t.want(['CW-1'], CFG)
  await t.idle()
  assert.deepEqual(calls, [['issue', 'view', '1', '--repo', 'o/r', '--json', 'title,author']])
  assert.deepEqual(t.get(), { 'CW-1': 'Add ]8;;x  thing' })
  assert.deepEqual(t.owners(), { 'CW-1': 'noah' })

  t.want(['CW-1'], null)
  reply = new Error('boom')
  t.want(['CW-5'], CFG)
  await t.idle()
  clock = 299_000
  t.want(['CW-5'], CFG)
  await t.idle()
  assert.equal(calls.length, 2)
  clock = 301_000
  t.want(['CW-5'], CFG)
  await t.idle()
  assert.equal(calls.length, 3)

  // Refresh: a good read is read again after 60s and replaces the title; a failed re-read keeps it and waits 5 minutes.
  const steps: [number, string | Error, number, string][] = [
    [301_000, issue('old'), 4, 'old'],
    [360_000, issue('new'), 4, 'old'],
    [361_000, issue('new'), 5, 'new'],
    [421_000, new Error('boom'), 6, 'new'],
    [720_000, issue('newer'), 6, 'new'],
    [722_000, issue('newer'), 7, 'newer'],
  ]
  for (const [at, next, calledWith, title] of steps) {
    clock = at
    reply = next
    t.want(['CW-6'], CFG)
    await t.idle()
    assert.equal(calls.length, calledWith, `calls at ${at}`)
    assert.equal(t.get()['CW-6'], title, `title at ${at}`)
  }
})

test('issue owners: a login is kept with the title, a bot, a missing author or a bad title gives none', async () => {
  const cases: [string, string, string | undefined][] = [
    ['login', JSON.stringify({ title: 't', author: { login: 'Noah-1' } }), 'Noah-1'],
    ['bot', JSON.stringify({ title: 't', author: { login: 'app/dependabot' } }), undefined],
    ['no author', JSON.stringify({ title: 't', author: null }), undefined],
    ['no title', JSON.stringify({ title: '', author: { login: 'noah' } }), undefined],
    ['not json', 'oops', undefined],
  ]
  for (const [name, reply, want] of cases) {
    const t = createTitles({ run: async () => reply })
    t.want(['CW-1'], CFG)
    await t.idle()
    assert.equal(t.owners()['CW-1'], want, name)
  }
})

test('headsFromProject: a plain head, a brace list in row order, and feat/ when the row is missing or does not parse', () => {
  const row = (cell: string) => `| Branch pattern | ${cell} |\n`
  const cases: [string, string[]][] = [
    [row('`work/<prefix>-N-x`'), ['work/']],
    [row('`{infra,feat}/<prefix>-N-x` (first is the default)'), ['infra/', 'feat/']],
    [row('`{feat,Infra}/<prefix>-N-x`'), ['feat/']],
    ['', ['feat/']],
  ]
  for (const [text, want] of cases) assert.deepEqual(headsFromProject(text), want, text)
})

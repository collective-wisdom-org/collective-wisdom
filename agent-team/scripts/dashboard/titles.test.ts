import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createTitles, headsFromProject } from './titles.ts'

const CFG = { prefix: 'CW', slug: 'o/r' }

test('tracker titles: cached, prefix-guarded, cleaned, failures retried after 5 minutes', async () => {
  let clock = 0
  const calls: string[][] = []
  let reply: string | Error = 'Add\x1b]8;;x\x07 thing\n'
  const t = createTitles({ now: () => clock, run: async (args) => { calls.push(args); if (reply instanceof Error) throw reply; return reply } })

  t.want(['CW-1', 'CW-1', 'ABC-2', 'CW-3x', 'CW-4; rm'], CFG)
  await t.idle()
  t.want(['CW-1'], CFG)
  await t.idle()
  assert.deepEqual(calls, [['issue', 'view', '1', '--repo', 'o/r', '--json', 'title', '--jq', '.title']])
  assert.deepEqual(t.get(), { 'CW-1': 'Add ]8;;x  thing' })

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
})

test('headsFromProject: a plain head, a brace list in row order, and feat/ when the row is missing or does not parse', () => {
  const row = (cell: string) => `| Key | Value |\n|---|---|\n| Branch pattern | ${cell} |\n`
  const cases: [string, string[]][] = [
    [row('`work/<prefix>-N-x`'), ['work/']],
    [row('`{feat,infra}/<prefix>-N-x` (first is the default)'), ['feat/', 'infra/']],
    [row('`{infra,feat}/<prefix>-N-x`'), ['infra/', 'feat/']],
    [row('`feat/cw-N-x`'), ['feat/']],
    [row('`{feat,Infra}/<prefix>-N-x`'), ['feat/']],
    [row('`{feat,}/<prefix>-N-x`'), ['feat/']],
    [row('none'), ['feat/']],
    ['', ['feat/']],
  ]
  for (const [text, want] of cases) assert.deepEqual(headsFromProject(text), want, text)
})

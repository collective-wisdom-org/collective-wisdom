import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createTrackerLists } from './lists.ts'

const item = (id: string, title: string, state: 'Todo' | 'Backlog', priority: string | null, createdAt: number | null) => ({ id, title, state, priority, createdAt })
const at = Date.parse('2026-11-01T00:00:00Z')

function parsed(entries: unknown[], prefix = 'CW') {
  const l = createTrackerLists({ read: () => JSON.stringify({ todo: { at: 'x', list: entries } }) })
  l.want(prefix)
  return l.get()
}

test('lists: Linear and Jira entries become items; entries without an id of the prefix are dropped', () => {
  const table: [unknown, unknown][] = [
    [{ identifier: 'CW-1', title: 'a', priority: 1, createdAt: '2026-11-01T00:00:00Z' }, item('CW-1', 'a', 'Todo', 'urgent', at)],
    [{ id: 'CW-2', title: ' b\x1b\n', priority: { name: 'High', value: 2 }, createdAt: '2026-11-01T00:00:00.000Z' }, item('CW-2', 'b', 'Todo', 'high', at)],
    [{ key: 'CW-3', fields: { summary: 'c', priority: { name: 'Highest' }, created: '2026-11-01T00:00:00.000+0000' } }, item('CW-3', 'c', 'Todo', 'urgent', at)],
    [{ id: 'CW-4', title: 'd', priority: 'Lowest', labels: [{ name: 'priority:medium' }] }, item('CW-4', 'd', 'Todo', 'medium', null)],
    [{ id: 'CW-5', title: 'e', priority: 0, createdAt: 'soon' }, item('CW-5', 'e', 'Todo', null, null)],
    [{ id: 'CW-6', title: 'f', priority: 4 }, item('CW-6', 'f', 'Todo', 'low', null)],
    [{ id: 'CW-7', title: 'g'.repeat(300), labels: { nodes: [{ name: 'priority:low' }] } }, item('CW-7', 'g'.repeat(200), 'Todo', 'low', null)],
    [{ id: 'XX-8', title: 'wrong prefix' }, undefined],
    [{ id: 'CW-9x', key: 'CW-9', title: 'id from the first match' }, item('CW-9', 'id from the first match', 'Todo', null, null)],
    ['CW-10', undefined],
    [null, undefined],
  ]
  for (const [entry, want] of table) assert.deepEqual(parsed([entry]), want === undefined ? [] : [want], JSON.stringify(entry))
  assert.deepEqual(parsed([{ id: 'CW-1', title: 'first' }, { id: 'CW-1', title: 'again' }]).map((i) => i.title), ['first'])
})

test('lists: Todo before Backlog, an id in both stays in Todo, bad reads keep the last list, re-read every 10 seconds, nothing without a prefix', () => {
  let clock = 0
  let reads = 0
  let text: string | undefined = JSON.stringify({ todo: { list: [{ id: 'CW-1', title: 'one' }] }, backlog: { list: [{ id: 'CW-1', title: 'dup' }, { id: 'CW-2', title: 'two' }] } })
  const l = createTrackerLists({ now: () => clock, read: () => (reads++, text) })
  assert.deepEqual(l.get(), [])
  l.want(null)
  assert.equal(reads, 0)
  l.want('CW')
  assert.deepEqual(l.get().map((i) => [i.id, i.state]), [['CW-1', 'Todo'], ['CW-2', 'Backlog']])

  text = JSON.stringify({ todo: { list: [] } })
  clock = 9_000
  l.want('CW')
  assert.equal(reads, 1)
  clock = 10_000
  l.want('CW')
  const kept = [['CW-1', 'Backlog'], ['CW-2', 'Backlog']]
  assert.deepEqual(l.get().map((i) => [i.id, i.state]), kept, 'todo replaced; the missing backlog key keeps its last list')

  for (const bad of [undefined, 'not json', '[]', JSON.stringify({ todo: 5, backlog: { list: 'x' } })]) {
    text = bad
    clock += 10_000
    l.want('CW')
    assert.deepEqual(l.get().map((i) => [i.id, i.state]), kept, String(bad))
  }

  l.want(null)
  assert.deepEqual(l.get(), [])
})

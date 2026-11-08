import { expect, test } from 'claude-code/testing'

import { groupTickets } from './groups'

const state = {
  tickets: {
    'CW-1': { stage: 'build', title: 'Docs', status: 'PR #5, review pass 2. Risk: Low (docs only)' },
    'CW-2': { stage: 'build-queued', queuedAt: '2026-11-05T10:00:00Z', status: 'Waiting for a slot.' },
    'CW-3': { stage: 'build-queued', queuedAt: '2026-11-05T09:00:00Z', title: 'Export', status: 'Waiting. Risk: High' },
    'CW-4': { stage: 'awaiting-merge', status: 'Reply approve 4. Risk: Medium' },
    'CW-5': { stage: 'blocked', status: 'Question open' },
    'CW-6': { stage: 'spec', status: 'Spec stage' },
    'CW-7': 'junk',
  },
}

test('groupTickets', () => {
  const view = groupTickets(state).map(g => [g.name, g.count, g.rows.map(r => r.id)])
  expect(view).toEqual([
    ['Awaiting merge approval', 1, ['CW-4']],
    ['Speccing', 1, ['CW-6']],
    ['Building', 1, ['CW-1']],
    ['Queued to build', 2, ['CW-3', 'CW-2']],
    ['Other', 1, ['CW-5']],
  ])
  const row = (group: string, i: number) => groupTickets(state).find(g => g.name === group)?.rows[i]
  expect(row('Building', 0)).toEqual({
    id: 'CW-1', title: 'Docs', risk: 'Low (docs only)', next: 'PR #5, review pass 2',
  })
  expect(row('Queued to build', 0)?.title).toBe('Export')
  expect(row('Queued to build', 1)).toEqual({ id: 'CW-2', title: '', risk: 'not rated yet', next: 'Waiting for a slot' })
  expect(row('Awaiting merge approval', 0)?.risk).toBe('Medium')
  for (const bad of [null, undefined, 'x', 3, [], {}, { tickets: null }, { tickets: [1] }, { tickets: { a: null } }]) {
    expect(groupTickets(bad)).toEqual([])
  }
})

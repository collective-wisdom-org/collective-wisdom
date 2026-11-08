import assert from 'node:assert/strict'
import { test } from 'node:test'

import { beginTask, closeSegment, openSegment, startTask, taskName } from './timeline.ts'
import type { AgentRecord } from '../types/index.d.ts'

const main: AgentRecord = {
  id: 'main', parentId: null, name: 'main', type: 'main', cwd: '/a', start: 0, end: null, last: 0,
  usage: {}, segments: [], tasks: [], taskIndex: null,
}

type Op = ['open' | 'close' | 'task' | 'begin', number, string?]
// `begin` is a prompt that entered at t: the clock before it was t - 1.
const step = (r: AgentRecord, [op, t, name]: Op) =>
  op === 'open' ? openSegment(r, t) : op === 'close' ? closeSegment(r, t) : op === 'begin' ? beginTask(r, name ?? '', t - 1, t) : startTask(r, name ?? '', t)
const run = (ops: Op[]) => ops.reduce(step, main)

// Each case: the calls a session makes on `main`, then the spans of main and of each task.
const cases: { name: string; ops: Op[]; main: unknown; tasks: unknown[]; names?: string[] }[] = [
  {
    name: 'two prompts with a wait between give two tasks and no span over the wait',
    ops: [['task', 0, 'a'], ['open', 0], ['close', 10], ['task', 50, 'b'], ['open', 50], ['close', 60]],
    main: [[0, 10], [50, 60]],
    tasks: [[[0, 10]], [[50, 60]]],
  },
  {
    name: 'a foreground wait leaves a gap in the task; no pause leaves none',
    ops: [['task', 0, 'a'], ['open', 0], ['close', 10], ['open', 30], ['close', 40]],
    main: [[0, 10], [30, 40]],
    tasks: [[[0, 10], [30, 40]]],
  },
  {
    name: 'a new task closes the open span, and closing twice or opening twice changes nothing',
    ops: [['task', 0, 'a'], ['open', 0], ['open', 5], ['task', 20, 'b'], ['close', 30], ['close', 40]],
    main: [[0, 20]],
    tasks: [[[0, 20]], []],
  },
  {
    name: 'opening with no task yet starts one named task',
    ops: [['open', 7]],
    main: [[7, null]],
    tasks: [[[7, null]]],
  },
  {
    name: 'a prompt whose turn already made the placeholder task renames it; a later prompt starts a new task',
    ops: [['open', 10], ['begin', 10, 'a'], ['close', 20], ['begin', 50, 'b'], ['open', 50]],
    main: [[10, 20], [50, null]],
    tasks: [[[10, 20]], [[50, null]]],
    names: ['a', 'b'],
  },
  {
    name: 'only the last 500 spans are kept',
    ops: Array.from({ length: 600 }, (_, i): Op[] => [['open', i * 2], ['close', i * 2 + 1]]).flat(),
    main: Array.from({ length: 500 }, (_, i) => [(i + 100) * 2, (i + 100) * 2 + 1]),
    tasks: [Array.from({ length: 500 }, (_, i) => [(i + 100) * 2, (i + 100) * 2 + 1])],
  },
]

for (const c of cases) {
  test(c.name, () => {
    const r = run(c.ops)
    assert.deepEqual(r.segments, c.main)
    assert.deepEqual(r.tasks.map(k => k.segments), c.tasks)
    if (c.names) assert.deepEqual(r.tasks.map(k => k.name), c.names)
  })
}

test('taskName takes the first real line, skips the T3 preamble, collapses space and cuts to 60', () => {
  const cases: [string, string][] = [
    ['Act as the implementer agent for this task.\n\nTEAM MODE. Run /ship-loop for CW-9: fix', 'TEAM MODE. Run /ship-loop for CW-9: fix'],
    ['\n  fix   the\tbug \nmore', 'fix the bug'],
    ['x'.repeat(80), 'x'.repeat(60)],
    ['  \n\n', 'task'],
  ]
  for (const [text, want] of cases) assert.equal(taskName(text), want)
  assert.equal(run([['open', 7]]).tasks[0]?.name, 'task')
})

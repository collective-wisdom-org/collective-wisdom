import assert from 'node:assert/strict'
import { test } from 'node:test'

import { beginTask, closeSegment, createWaits, openSegment, startTask, taskName } from './timeline.ts'
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
    ['Act as the implementer agent for this task.\n\nTEAM MODE. Run /ship-loop for CW-9: fix', 'Run /ship-loop for CW-9: fix'],
    ['\n  fix   the\tbug \nmore', 'fix the bug'],
    ['x'.repeat(80), 'x'.repeat(60)],
    ['  \n\n', 'task'],
    ['Act as the implementation sub-agent for this task.\nTEAM MODE. Run /ship-loop for CW-9: fix', 'Run /ship-loop for CW-9: fix'],
    ['Act as the build subagent for this task\nfix it', 'fix it'],
    ['TEAM MODE.\nBuild CW-9', 'Build CW-9'],
    ['Act as the implementation sub-agent for this task.\n\nTEAM MODE. Run /ship-loop for CW-216: Redesign the agent gantt', 'Run /ship-loop for CW-216: Redesign the agent gantt'],
    ['Act as the implementation sub-agent for this task. TEAM MODE. CONTINUE. Run /ship-loop. Do the build stage.', 'Run /ship-loop. Do the build stage.'],
    ['TEAM MODE. CONTINUE. Run /ship-loop for CW-9: fix', 'Run /ship-loop for CW-9: fix'],
  ]
  for (const [text, want] of cases) assert.equal(taskName(text), want)
  assert.equal(run([['open', 7]]).tasks[0]?.name, 'task')
})

test('taskName names a Chief of Staff relay by the newest earlier ticket and the work asked', () => {
  const withTicket = ['Run /ship-loop for CW-1: old', 'build', 'Run /ship-loop for CW-216: Redesign the agent gantt', 'merge PR #5']
  const cases: [string, string[], string][] = [
    ['CHIEF OF STAFF: the user approved the spec: "approve 216". Continue to the build stage.', withTicket, 'CW-216 build'],
    ['CHIEF OF STAFF: auto-approved the spec at abc123.', withTicket, 'CW-216 build'],
    ['CHIEF OF STAFF: the user approved the merge of PR #218 at head abc: "merge".', withTicket, 'CW-216 merge PR #218'],
    ['CHIEF OF STAFF: auto-approved the merge of PR #218 at head abc.', withTicket, 'CW-216 merge PR #218'],
    ['CHIEF OF STAFF: a reviewer asked for changes on PR #218: fix it', withTicket, 'CW-216 changes on PR #218'],
    ['CHIEF OF STAFF: the user asked for changes: "tighten it".', withTicket, 'CW-216 changes'],
    ['CHIEF OF STAFF: continue the review stage from where the branch is.', withTicket, 'CW-216 review'],
    ['CHIEF OF STAFF: the user says: "go on". Continue the build stage.', withTicket, 'CW-216 build'],
    ['CHIEF OF STAFF: the user answered: use B', withTicket, 'CW-216 the user answered: use B'],
    ['CHIEF OF STAFF: the user asked for changes: "a"\napproved the spec', withTicket, 'CW-216 changes'],
    ['Act as the implementer agent for this task.\nCHIEF OF STAFF: the user approved the spec: "ok".', withTicket, 'CW-216 build'],
    ['CHIEF OF STAFF: the user approved the spec: "ok".', ['task', 'fix the bug'], 'build'],
    ['CHIEF OF STAFF: the user approved the spec: "ok".', [], 'build'],
    ['CHIEF OF STAFF NOTICE: child thread done', withTicket, 'CHIEF OF STAFF NOTICE: child thread done'],
  ]
  for (const [text, earlier, want] of cases) assert.equal(taskName(text, earlier), want)
})

// Each case: events on one agent in clock order. `ask` and `settle` are a wait beginning and ending (a permission ask or a plan approval); `complete` ends the agent's turn and `end` stamps its end.
type Ev = ['open' | 'ask' | 'settle' | 'complete' | 'end', number, string?]
const waitCases: { name: string; evs: Ev[]; segments: unknown }[] = [
  { name: 'a permission ask leaves no span over the wait', evs: [['open', 0], ['ask', 10], ['settle', 70]], segments: [[0, 10], [70, null]] },
  {
    name: 'overlapping waits close once at the first and reopen after the last',
    evs: [['open', 0], ['ask', 10], ['ask', 20], ['settle', 30], ['settle', 80]],
    segments: [[0, 10], [80, null]],
  },
  {
    name: 'an agent that ends during the wait stays closed',
    evs: [['open', 0], ['ask', 10], ['complete', 40], ['end', 40], ['settle', 90]],
    segments: [[0, 10]],
  },
  { name: 'a settle with no wait changes nothing', evs: [['open', 0], ['settle', 5]], segments: [[0, null]] },
]

for (const c of waitCases) {
  test(c.name, () => {
    const waits = createWaits()
    let r: AgentRecord = { ...main, tasks: [] }
    for (const [ev, t] of c.evs) {
      if (ev === 'open') r = openSegment(r, t)
      else if (ev === 'complete') r = { ...closeSegment(r, t), last: t }
      else if (ev === 'end') r = { ...r, end: t }
      else r = (ev === 'ask' ? waits.begin('main', t) : waits.end('main', t))?.(r) ?? r
    }
    assert.deepEqual(r.segments, c.segments)
  })
}

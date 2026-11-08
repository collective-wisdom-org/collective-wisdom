// Working time and tasks of the records. Pure, so the rules are testable without the engine.
import type { AgentRecord, Segment } from '../types/index.d.ts'

const NAME_MAX = 60
// A list keeps its last spans only, so a long session stays small.
const SEGMENTS_MAX = 500
// T3 Code opens a delegated task with `Act as the implementer agent for this task.` (also `sub-agent`, `subagent`), on its own line or ahead of the task.
const PREAMBLE = /^Act as the [\w -]*agent for this task\.?\s*/i
// The team's markers open a delegated prompt; the name starts after them.
const TEAM_MODE = /^TEAM MODE\.?\s*/i
const CONTINUE = /^CONTINUE\.?\s*/i
const RELAY = /^CHIEF OF STAFF:\s*/i
const TICKET = /[A-Z][A-Z0-9]*-\d+/
// What a Chief of Staff relay asks for, first match wins; the relay names no ticket.
const RELAY_WORK: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/approved the spec/i, () => 'build'],
  [/approved the merge of PR (#\d+)/i, m => `merge PR ${m[1]}`],
  [/reviewer asked for changes on PR (#\d+)/i, m => `changes on PR ${m[1]}`],
  [/asked for changes/i, () => 'changes'],
  [/continue the (\S+) stage/i, m => m[1]!],
]

/** The task's name: the prompt's first line left after T3's preamble and the team markers, whitespace collapsed, cut to 60 characters. A Chief of Staff relay is named `<ticket> <work>`, the ticket from the newest of `earlier` (main's earlier task names) that has one. */
export function taskName(text: string, earlier: string[] = []): string {
  for (const raw of text.split('\n')) {
    const line = raw.replace(/\s+/g, ' ').trim().replace(PREAMBLE, '').replace(TEAM_MODE, '').replace(CONTINUE, '')
    if (line === '') continue
    if (!RELAY.test(line)) return line.slice(0, NAME_MAX)
    const work = line.replace(RELAY, '')
    let name = work
    for (const [re, to] of RELAY_WORK) {
      const m = work.match(re)
      if (m) { name = to(m); break }
    }
    const ticket = [...earlier].reverse().map(n => n.match(TICKET)?.[0]).find(Boolean)
    return (ticket ? `${ticket} ${name}` : name).slice(0, NAME_MAX)
  }
  return 'task'
}

/** True while the record has an open span. */
export const isWorking = (record: AgentRecord) => isOpen(record.segments)

const isOpen = (segments: Segment[]) => segments.length > 0 && segments[segments.length - 1]?.[1] === null

const closed = (segments: Segment[], t: number): Segment[] =>
  isOpen(segments) ? segments.map((s, i): Segment => (i === segments.length - 1 ? [s[0], t] : s)) : segments

const opened = (segments: Segment[], t: number): Segment[] => (isOpen(segments) ? segments : [...segments, [t, null] as Segment].slice(-SEGMENTS_MAX))

/** Closes the open span of the record and, on `main`, of its current task. Closing a closed record changes nothing. */
export function closeSegment(record: AgentRecord, t: number): AgentRecord {
  const tasks = record.tasks.map((k, i) => (i === record.tasks.length - 1 ? { ...k, segments: closed(k.segments, t) } : k))
  return { ...record, segments: closed(record.segments, t), tasks }
}

/** Starts a new task on `main` at `t`, after closing the open spans. The new task has no span until the next openSegment. */
export function startTask(main: AgentRecord, name: string, t: number): AgentRecord {
  const base = closeSegment(main, t)
  return { ...base, tasks: [...base.tasks, { name, start: t, segments: [], usage: {} }] }
}

/** Opens a span on the record and, on `main`, on its current task. With no task yet, `main` first starts one named `task`. */
export function openSegment(record: AgentRecord, t: number): AgentRecord {
  const base = record.parentId === null && record.tasks.length === 0 ? startTask(record, 'task', t) : record
  const tasks = base.tasks.map((k, i) => (i === base.tasks.length - 1 ? { ...k, segments: opened(k.segments, t) } : k))
  return { ...base, segments: opened(base.segments, t), tasks }
}

/**
 * The task a submitted prompt begins on `main`. `since` is the clock before the prompt entered, `t` the clock after.
 * If main's last task began at or after `since`, the turn's own start made it: it takes the name. Else a new task starts, and a span open at `t` moves into it.
 */
export function beginTask(main: AgentRecord, name: string, since: number, t: number): AgentRecord {
  const last = main.tasks[main.tasks.length - 1]
  if (last !== undefined && last.start >= since) {
    return { ...main, tasks: main.tasks.map((k, i) => (i === main.tasks.length - 1 ? { ...k, name } : k)) }
  }
  const started = startTask(main, name, t)
  return isWorking(main) ? openSegment(started, t) : started
}

/** The clock stamps of one wait: `before` is when the first of the overlapping waits began. */
type Wait = { count: number; before: number }

/**
 * Counts waits per agent id. Waits can overlap (parallel tool calls): the span closes at the first and reopens when the last settles.
 * `begin` and `end` return the change to make to the record, or null when the span stays as it is.
 */
export function createWaits(): {
  begin: (id: string, now: number) => ((r: AgentRecord) => AgentRecord) | null
  end: (id: string, now: number) => ((r: AgentRecord) => AgentRecord) | null
} {
  const open = new Map<string, Wait>()
  return {
    begin(id, now) {
      const wait = open.get(id)
      const before = wait?.before ?? now
      open.set(id, { count: (wait?.count ?? 0) + 1, before })
      return wait === undefined ? r => closeSegment(r, before) : null
    },
    end(id, now) {
      const wait = open.get(id)
      if (wait === undefined) return null
      if (wait.count > 1) {
        open.set(id, { ...wait, count: wait.count - 1 })
        return null
      }
      open.delete(id)
      // A turn.complete or an end stamp that landed during the wait wins: no span is left open on a finished agent.
      return r => (r.end === null && r.last <= wait.before ? openSegment(r, now) : r)
    },
  }
}

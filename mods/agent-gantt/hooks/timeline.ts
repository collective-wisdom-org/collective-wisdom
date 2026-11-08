// Working time and tasks of the records. Pure, so the rules are testable without the engine.
import type { AgentRecord, Segment } from '../types/index.d.ts'

const NAME_MAX = 60
// T3 Code puts this line first in a delegated task: `Act as the implementer agent for this task.`
const PREAMBLE = /^Act as the .* agent for this task\.?$/i

/** The task's name: the prompt's first line that is not T3's preamble, whitespace collapsed, cut to 60 characters. */
export function taskName(text: string): string {
  for (const raw of text.split('\n')) {
    const line = raw.replace(/\s+/g, ' ').trim()
    if (line === '' || PREAMBLE.test(line)) continue
    return line.length > NAME_MAX ? line.slice(0, NAME_MAX) : line
  }
  return 'task'
}

/** True while the record has an open span. */
export const isWorking = (record: AgentRecord) => isOpen(record.segments)

const isOpen = (segments: Segment[]) => segments.length > 0 && segments[segments.length - 1]?.[1] === null

const closed = (segments: Segment[], t: number): Segment[] =>
  isOpen(segments) ? segments.map((s, i): Segment => (i === segments.length - 1 ? [s[0], t] : s)) : segments

const opened = (segments: Segment[], t: number): Segment[] => (isOpen(segments) ? segments : [...segments, [t, null]])

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

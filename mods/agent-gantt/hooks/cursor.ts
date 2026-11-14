// Cursor hook events mapped onto the mod's records and the dashboard's snapshot. Pure, so the rules are testable without Cursor.
import type { AgentRecord, Prices, Tokens } from '../types/index.d.ts'
import { buildRows, MAIN } from './rows.ts'
import { buildSnapshot, pickFiledTicket, pickHeading, pickRequest } from './snapshot.ts'
import { beginTask, closeSegment, openSegment, taskName } from './timeline.ts'

const NAME_MAX = 60

/** The part of a Cursor hook payload the mapping reads. */
export type CursorPayload = {
  hook_event_name?: string
  conversation_id?: string
  parent_conversation_id?: string
  model?: string
  workspace_roots?: string[]
  prompt?: string
  subagent_id?: string
  subagent_type?: string
  subagent_model?: string
  task?: string
  tool_call_id?: string
  duration_ms?: number
}

/** One Cursor run (a turn) as `agent_usage.py --cursor-agent` prints it: `at` in ms since epoch, tokens by billed kind. */
export type CursorRun = { at: number; model: string | null; input: number; output: number; read: number; write: number }

/** What the hook keeps between events of one conversation. */
export type CursorState = {
  records: AgentRecord[]
  heading: { isSet: boolean; value: string | null }
  model: string | null
  subagentModels: Record<string, string>
  /** The model each task began with, by task index. */
  taskModels: Record<string, string>
  /** The runs of the last good read of Cursor's run store; null until it was read once, and in a state saved before CW-284. */
  runs: CursorRun[] | null
  /** The ticket a TICKET HELPER filed, from its final reply in Cursor's run store; null until seen, and in a state saved before CW-288. */
  ticket: string | null
  /** A TICKET HELPER's request line, from its first prompt; null for any other conversation, and in a state saved before CW-288. */
  request: string | null
}

export const emptyState = (): CursorState => ({ records: [], heading: { isSet: false, value: null }, model: null, subagentModels: {}, taskModels: {}, runs: null, ticket: null, request: null })

const EVENTS = ['sessionStart', 'beforeSubmitPrompt', 'stop', 'subagentStart', 'subagentStop', 'sessionEnd']

/** The key of the state and snapshot an event belongs to: a subagent's event goes to its parent's conversation, since Cursor may give a subagent its own `conversation_id`. */
export const sessionKey = (p: CursorPayload): string | null => p.parent_conversation_id || p.conversation_id || null

/** The folder the conversation works in, or null. */
export const cursorCwd = (p: CursorPayload): string | null => p.workspace_roots?.[0] || null

/** A subagent's row name: its task's first line, else its type. Start and stop compute it the same way. */
const agentName = (p: CursorPayload) => ((p.task ?? '').split('\n').find(l => l.trim() !== '')?.trim().slice(0, NAME_MAX) || p.subagent_type || 'subagent')

const mapMain = (records: AgentRecord[], fn: (r: AgentRecord) => AgentRecord) => records.map(r => (r.id === MAIN ? fn(r) : r))

/** The state after one hook event at `now` (ms since epoch). An unknown event, or a payload without `conversation_id`, gives the state back. */
export function applyEvent(state: CursorState, p: CursorPayload, now: number): CursorState {
  const event = p.hook_event_name ?? ''
  if (!EVENTS.includes(event) || !sessionKey(p)) return state
  const cwd = cursorCwd(p) ?? ''
  let next: CursorState = { ...state, model: p.model || state.model }
  if (!next.records.some(r => r.id === MAIN)) {
    const main: AgentRecord = { id: MAIN, parentId: null, name: 'main', type: 'main', cwd, start: now, end: null, last: now, usage: {}, segments: [], tasks: [], taskIndex: null }
    next = { ...next, records: [main, ...next.records] }
  }
  const { records } = next
  const main = records.find(r => r.id === MAIN)!
  const taskIndex = main.tasks.length > 0 ? main.tasks.length - 1 : null
  switch (event) {
    case 'beforeSubmitPrompt': {
      const prompt = p.prompt ?? ''
      // `since` after now: a prompt always begins a new task, as no turn start made one here.
      const begun = beginTask(main, taskName(prompt, main.tasks.map(k => k.name)), now + 1, now)
      const heading = next.heading.isSet ? next.heading : { isSet: true, value: pickHeading(prompt) }
      const request = !next.heading.isSet && heading.value === 'TICKET HELPER' ? pickRequest(prompt) : next.request
      const taskModels = next.model ? { ...next.taskModels, [begun.tasks.length - 1]: next.model } : next.taskModels
      return { ...next, heading, request, taskModels, records: mapMain(records, () => openSegment(begun, now)) }
    }
    case 'stop':
      return { ...next, records: mapMain(records, r => ({ ...closeSegment(r, now), last: now })) }
    case 'subagentStart': {
      const id = p.subagent_id || p.tool_call_id || `${p.subagent_type ?? 'subagent'}-${now}`
      if (records.some(r => r.id === id)) return next
      const record: AgentRecord = { id, parentId: MAIN, name: agentName(p), type: p.subagent_type ?? '', cwd: main.cwd, start: now, end: null, last: now, usage: {}, segments: [[now, null]], tasks: [], taskIndex }
      const subagentModels = p.subagent_model ? { ...next.subagentModels, [id]: p.subagent_model } : next.subagentModels
      return { ...next, subagentModels, records: [...records, record] }
    }
    case 'subagentStop': {
      const type = p.subagent_type ?? ''
      const name = agentName(p)
      const open = records.find(r => r.id !== MAIN && r.end === null && r.type === type && r.name === name)
      if (open) return { ...next, records: records.map(r => (r === open ? { ...closeSegment(r, now), end: now, last: now } : r)) }
      // A start the hook missed still draws, as long as the stop says it ran.
      const start = typeof p.duration_ms === 'number' ? Math.max(0, now - p.duration_ms) : now
      const id = `${type || 'subagent'}-${now}`
      const missed: AgentRecord = { id, parentId: MAIN, name, type, cwd: main.cwd, start, end: now, last: now, usage: {}, segments: [[start, now]], tasks: [], taskIndex }
      return { ...next, records: [...records, missed] }
    }
    case 'sessionEnd':
      return { ...next, records: records.map(r => ({ ...closeSegment(r, now), end: r.end ?? now, last: now })) }
    default:
      return next
  }
}

/** The state with the ticket a TICKET HELPER filed: the first ticket found in `results` (the final replies of the conversation's runs, in turn order). Anything else gives the state back: results null (not read), another heading, a ticket already set, or no ticket in any reply. */
export function withFiledTicket(state: CursorState, results: string[] | null): CursorState {
  if (state.heading.value !== 'TICKET HELPER' || state.ticket !== null || results === null) return state
  for (const text of results) {
    const ticket = pickFiledTicket(text)
    if (ticket !== null) return { ...state, ticket }
  }
  return state
}

const shortModel = (m: string | null | undefined) => (m ? m.replace(/^claude-/, '') : null)

/** `usage` with one run added under its model. Cursor's cache writes are priced at the 5 minute rate, as `agent_usage.py` does. */
function plusRun(usage: Record<string, Tokens>, run: CursorRun): Record<string, Tokens> {
  const model = run.model ?? 'unknown model'
  const t = usage[model] ?? { input: 0, output: 0, read: 0, write_5m: 0, write_1h: 0 }
  return { ...usage, [model]: { ...t, input: t.input + run.input, output: t.output + run.output, read: t.read + run.read, write_5m: t.write_5m + run.write } }
}

/** The records with each run's tokens on `main` and on the task that began closest to the run (the earlier one on a tie; a task with no spans has no row and is skipped). Subagents get none: Cursor counts their work in the turn that started them. */
function withRuns(records: AgentRecord[], runs: CursorRun[]): AgentRecord[] {
  return records.map(r => {
    if (r.id !== MAIN) return r
    const tasks = r.tasks.map(k => ({ ...k }))
    let usage = r.usage
    for (const run of runs) {
      usage = plusRun(usage, run)
      let near = -1
      tasks.forEach((k, i) => {
        if (k.segments.length === 0) return
        if (near < 0 || Math.abs(k.start - run.at) < Math.abs(tasks[near]!.start - run.at)) near = i
      })
      if (near >= 0) tasks[near]!.usage = plusRun(tasks[near]!.usage, run)
    }
    return { ...r, usage, tasks }
  })
}

/** The JSON text the local dashboard reads for this conversation. With the run store read (`state.runs`) and a price table, rows carry the runs' tokens and cost and `total` is the sum of the row costs (null when a row has none); else rows have 0 tokens, no cost and the snapshot no total. */
export function cursorSnapshot(state: CursorState, p: CursorPayload, now: number, threadId: string | null, prices: Prices | null = null): string {
  const runs = state.runs ?? null
  const rows = buildRows(runs === null ? state.records : withRuns(state.records, runs), [], runs === null ? null : prices, 'Cursor').map(row => ({
    ...row,
    model: shortModel(row.kind === 'task' ? (state.taskModels[row.id.match(/^main:task:(\d+)$/)?.[1] ?? ''] ?? state.model) : state.subagentModels[row.id]),
  }))
  const total = runs === null || rows.some(r => r.cost === null) ? null : rows.reduce((sum, r) => sum + (r.cost ?? 0), 0)
  const cwd = cursorCwd(p) ?? state.records.find(r => r.id === MAIN)?.cwd ?? ''
  return buildSnapshot({ sessionId: sessionKey(p) ?? '', cwd, updatedAt: now, total, rows, threadId, heading: state.heading.value, ticket: state.ticket, request: state.request })
}

/** What the hook prints for an event. The gantt hook never blocks, never adds a follow-up and never sets `user_message`. */
export function hookOutput(event: string): string {
  if (event === 'subagentStart') return JSON.stringify({ permission: 'allow' })
  if (event === 'beforeSubmitPrompt') return JSON.stringify({ continue: true })
  return ''
}

/** Tokens of one kind of use, summed over an agent's turns. A record stored by an older mod has `write` (priced as 1h) in place of the two write fields. */
export type Tokens = { input: number; output: number; read: number; write_5m: number; write_1h: number }

/** A working span in ms since epoch. The end is null while the span is open. */
export type Segment = [number, number | null]

/** One user prompt's worth of the main loop's work. */
export type TaskRecord = {
  /** The prompt's first line, cut short. */
  name: string
  /** ms since epoch, when the prompt arrived. */
  start: number
  /** The task's working spans, oldest first. */
  segments: Segment[]
  /** Summed per model id, over the turns that ended in this task. */
  usage: Record<string, Tokens>
}

/** One agent of the session as the mod recorded it. The main loop has id `main`. */
export type AgentRecord = {
  id: string
  /** `main` for an agent the main loop spawned, null for the main record itself. */
  parentId: string | null
  name: string
  type: string
  cwd: string
  /** ms since epoch, stamped by the mod. */
  start: number
  /** Null while the agent runs. */
  end: number | null
  /** Time of the agent's last turn.complete, used as its end once it stops running. */
  last: number
  /** Summed per model id. */
  usage: Record<string, Tokens>
  /** The agent's working spans, oldest first. The last is open while the agent works. */
  segments: Segment[]
  /** The tasks of the main record, oldest first; empty on every other record. */
  tasks: TaskRecord[]
  /** For a subagent the main loop spawned: the index of the main task current at spawn. Else null. */
  taskIndex: number | null
}

/** One family's rates in dollars per million tokens, as in ~/.collective-wisdom/scripts/prices.json. */
export type Rates = { input: number; output: number; read: number; write_1h: number; write_5m: number }
export type Prices = Record<string, Rates>

/** What the mod found when it read ~/.collective-wisdom/scripts/prices.json. */
export type PriceState = { isLoaded: boolean; table: Prices | null; note: string }

declare module 'claude-code' {
  interface PluginState {
    'agent-gantt': {
      records: Shaped<AgentRecord[]>
      prices: Shaped<PriceState>
      /** `T3 Code` or `Claude Code`, read once at session.start. */
      harness: string
      /** ms since epoch, moved by every record change and by the 5 second tick. */
      now: number
    }
  }
}

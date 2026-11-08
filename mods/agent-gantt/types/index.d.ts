/** Tokens of one kind of use, summed over an agent's turns. */
export type Tokens = { input: number; output: number; read: number; write: number }

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
      /** ms since epoch, moved by every record change and by the 5 second tick. */
      now: number
    }
  }
}

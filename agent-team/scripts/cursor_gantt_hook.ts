// Cursor hook: writes this conversation's gantt rows to <root checkout>/.agent-team/gantt/<id>.json for the local dashboard.
// Run by ~/.cursor/hooks.json as `node "$HOME/.collective-wisdom/scripts/cursor_gantt_hook.ts"` for six events (CW-258).
// On stop, subagentStop and sessionEnd it also reads the conversation's tokens from Cursor's run store (agent_usage.py --cursor-agent) and prices them from prices.json beside it (CW-284).
// The same read gives the final replies (`results`); a TICKET HELPER's ticket is taken from them (CW-288), and the text itself is not kept.
// It answers Cursor first and exits 0 after any error once stdin parsed; stdin that cannot be read or parsed exits 1, which Cursor goes on from.
import { execFileSync } from 'node:child_process'
import { lstatSync, mkdirSync, readFileSync, renameSync, rmdirSync, rmSync, statSync, writeFileSync, writeSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { applyEvent, cursorCwd, cursorSnapshot, emptyState, hookOutput, sessionKey, withFiledTicket } from '../../mods/agent-gantt/hooks/cursor.ts'
import type { CursorPayload, CursorRun, CursorState } from '../../mods/agent-gantt/hooks/cursor.ts'
import { snapshotName } from '../../mods/agent-gantt/hooks/snapshot.ts'
import type { Prices } from '../../mods/agent-gantt/types/index.d.ts'

const GANTT = '.agent-team/gantt'
const LOCK_WAIT_MS = 2000
const LOCK_STALE_MS = 30_000
// The dashboard's thread id rule (api.ts cleanThreadId).
const THREAD_ID = /^[A-Za-z0-9:%._-]+$/

// The events after which Cursor's run store may hold new usage; the others do not read it.
const USAGE_EVENTS = ['stop', 'subagentStop', 'sessionEnd']
const USAGE_SCRIPT = fileURLToPath(new URL('./agent_usage.py', import.meta.url))
const PRICES_FILE = fileURLToPath(new URL('./prices.json', import.meta.url))
// agent_usage.py prints every run's full `result`; Node's 1 MiB default would throw ENOBUFS on a long conversation.
const MAX_STORE_READ_BYTES = 64 * 1024 * 1024

const sleep = (ms: number) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)

/** True when the path is a link or anything but a folder; a missing path is fine. */
function isUnsafeDir(path: string): boolean {
  try {
    const st = lstatSync(path)
    return st.isSymbolicLink() || !st.isDirectory()
  } catch {
    return false
  }
}

function isLink(path: string): boolean {
  try {
    return lstatSync(path).isSymbolicLink()
  } catch {
    return false
  }
}

const exists = (path: string) => {
  try {
    statSync(path)
    return true
  } catch {
    return false
  }
}

/** The root checkout the way register.tsx finds it: only the plain `<root>/.git` layout; else the working folder. */
function resolveRoot(cwd: string): string {
  try {
    const common = execFileSync('git', ['rev-parse', '--path-format=absolute', '--git-common-dir'], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 3000 }).trim()
    if (/^\/[^\n]*\/\.git$/.test(common)) return common.slice(0, common.lastIndexOf('/'))
  } catch {
    // not a git checkout: keep the working folder
  }
  return cwd
}

/** Writes to a temp file in the same folder, then renames it into place. */
function writeAtomic(path: string, text: string) {
  const tmp = `${path}.${process.pid}.tmp`
  try {
    writeFileSync(tmp, text, { flag: 'wx' })
    renameSync(tmp, path)
  } catch (err) {
    rmSync(tmp, { force: true })
    throw err
  }
}

/** Takes the conversation's lock folder; null when it stays taken for two seconds. A lock older than 30 seconds is removed first. */
function takeLock(lock: string): boolean {
  const until = Date.now() + LOCK_WAIT_MS
  for (;;) {
    try {
      mkdirSync(lock)
      return true
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== 'EEXIST') return false
    }
    try {
      if (Date.now() - statSync(lock).mtimeMs > LOCK_STALE_MS) rmdirSync(lock)
    } catch {
      // gone or not removable: try again
    }
    if (Date.now() > until) return false
    sleep(25)
  }
}

/** The price table next to this script, or null when it is missing or bad. */
function readPrices(): Prices | null {
  try {
    const table = JSON.parse(readFileSync(PRICES_FILE, 'utf8'))
    return table !== null && typeof table === 'object' ? table : null
  } catch {
    return null
  }
}

const isRun = (r: any): r is CursorRun =>
  r !== null && typeof r === 'object' && ['at', 'input', 'output', 'read', 'write'].every(k => Number.isFinite(r[k])) && (r.model === null || typeof r.model === 'string')

/** The conversation's runs and final replies from Cursor's run store through agent_usage.py. When the read fails in any way (the store cannot be read, no python3, a timeout, output of the wrong shape) the runs are `old` and the results null; output without a list of strings as `results` gives null results. */
function readRuns(id: string, old: CursorRun[] | null): { runs: CursorRun[] | null; results: string[] | null } {
  try {
    const out = execFileSync('python3', ['-I', USAGE_SCRIPT, '--cursor-agent', id], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 3000, maxBuffer: MAX_STORE_READ_BYTES })
    const parsed = JSON.parse(out)
    const results = Array.isArray(parsed?.results) && parsed.results.every((t: unknown) => typeof t === 'string') ? parsed.results : null
    return { runs: Array.isArray(parsed?.runs) && parsed.runs.every(isRun) ? parsed.runs : old, results }
  } catch {
    return { runs: old, results: null }
  }
}

function record(payload: CursorPayload, now: number) {
  const cwd = cursorCwd(payload)
  const id = sessionKey(payload)
  if (!cwd || !id) return
  const root = resolveRoot(cwd)
  if (!['docs/agents/project.md', '.agent-team/state.json'].some(m => exists(`${root}/${m}`))) return
  const name = snapshotName(id)
  if (name === null) return
  const dir = `${root}/${GANTT}`
  const stateDir = `${dir}/cursor`
  if ([`${root}/.agent-team`, dir, stateDir].some(isUnsafeDir)) return
  const snapshot = `${dir}/${name}`
  const stateFile = `${stateDir}/${name}`
  if (isLink(snapshot) || isLink(stateFile)) return
  mkdirSync(stateDir, { recursive: true })
  // Read before the lock so the 3 second python call does not hold it; null (a failed read) keeps the saved state's runs, and a shorter (older) read never replaces them.
  const read = USAGE_EVENTS.includes(payload.hook_event_name ?? '') ? readRuns(id, null) : null
  const fresh = read?.runs ?? null
  const results = read?.results ?? null
  const lock = `${stateDir}/${id}.lock`
  if (!takeLock(lock)) return
  try {
    let state: CursorState = emptyState()
    try {
      const saved = JSON.parse(readFileSync(stateFile, 'utf8'))
      if (Array.isArray(saved?.records)) state = { ...state, ...saved }
    } catch {
      // missing or bad: start empty
    }
    const thread = process.env.T3CODE_THREAD_ID
    const threadId = thread && thread.length <= 200 && THREAD_ID.test(thread) ? thread : null
    let text: string
    const prices = readPrices()
    const advance = (from: CursorState) => {
      const next = applyEvent(from, payload, now)
      return withFiledTicket(fresh === null || fresh.length < (next.runs?.length ?? 0) ? next : { ...next, runs: fresh }, results)
    }
    try {
      state = advance(state)
      text = cursorSnapshot(state, payload, now, threadId, prices)
    } catch {
      // a stored state of bad shape: start empty and carry on
      state = advance(emptyState())
      text = cursorSnapshot(state, payload, now, threadId, prices)
    }
    writeAtomic(stateFile, JSON.stringify(state))
    writeAtomic(snapshot, text)
  } finally {
    rmdirSync(lock)
  }
}

try {
  let payload: CursorPayload
  try {
    payload = JSON.parse(readFileSync(0, 'utf8'))
    if (payload === null || typeof payload !== 'object') throw new Error('not an object')
  } catch {
    // Cursor goes on for exit codes other than 0 and 2; with no payload there is nothing to answer or record.
    process.exit(1)
  }
  const out = hookOutput(payload.hook_event_name ?? '')
  if (out !== '') writeSync(1, out)
  if (!cursorCwd(payload) && process.env.CURSOR_PROJECT_DIR) payload = { ...payload, workspace_roots: [process.env.CURSOR_PROJECT_DIR] }
  record(payload, Date.now())
} catch {
  // the dashboard is optional: skip this write
}
process.exit(0)

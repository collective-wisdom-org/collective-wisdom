// Cursor hook: writes this conversation's gantt rows to <root checkout>/.agent-team/gantt/<id>.json for the local dashboard.
// Run by ~/.cursor/hooks.json as `node "$HOME/.collective-wisdom/scripts/cursor_gantt_hook.ts"` for six events (CW-258).
// It answers Cursor first and exits 0 after any error once stdin parsed; stdin that cannot be read or parsed exits 1, which Cursor goes on from.
import { execFileSync } from 'node:child_process'
import { lstatSync, mkdirSync, readFileSync, renameSync, rmdirSync, rmSync, statSync, writeFileSync, writeSync } from 'node:fs'

import { applyEvent, cursorCwd, cursorSnapshot, emptyState, hookOutput, sessionKey } from '../../mods/agent-gantt/hooks/cursor.ts'
import type { CursorPayload, CursorState } from '../../mods/agent-gantt/hooks/cursor.ts'
import { snapshotName } from '../../mods/agent-gantt/hooks/snapshot.ts'

const GANTT = '.agent-team/gantt'
const LOCK_WAIT_MS = 2000
const LOCK_STALE_MS = 30_000
// The dashboard's thread id rule (api.ts cleanThreadId).
const THREAD_ID = /^[A-Za-z0-9:%._-]+$/

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
    try {
      state = applyEvent(state, payload, now)
      text = cursorSnapshot(state, payload, now, threadId)
    } catch {
      // a stored state of bad shape: start empty and carry on
      state = applyEvent(emptyState(), payload, now)
      text = cursorSnapshot(state, payload, now, threadId)
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

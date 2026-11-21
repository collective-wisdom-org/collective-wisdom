import { createHash, randomBytes, timingSafeEqual } from 'node:crypto'
import { createServer } from 'node:http'
import type { IncomingMessage, Server } from 'node:http'
import { lstatSync, readFileSync, readdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { execFile, spawn } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { buildApi, cleanThreadId, ledgerSessions, parseWorktrees, repoUrlFromProject, teamSessions, trackerLinksFromProject } from './api.ts'
import type { TrackerLinks, Worktree } from './api.ts'
import { createTitles, ghRunner, headsFromProject, prefixFromProject, retiredFromProject, slugFromUrl } from './titles.ts'
import type { Retired } from './titles.ts'
import type { TitleConfig } from './titles.ts'
import { createUpdated } from './updated.ts'
import { createBacklog } from './backlog.ts'
import { createTrackerLists } from './lists.ts'
import { createMerged } from './merged.ts'
import { createOpenPrs } from './open.ts'
import { createViewer } from './viewer.ts'
import { createDetails, gitRunner } from './details.ts'
import { createCi, requiredFromProject } from './ci.ts'
import type { CiWant } from './ci.ts'
import type { DetailWant } from './details.ts'
import type { MergedConfig } from './merged.ts'
import { backup } from './backup.ts'
import { parseLedger, recordSpend, spendByTicket } from './spend.ts'
import { historyByTicket, parseHistory, recordHistory, recordTeamHistory, teamHistory } from './history.ts'

const PAGES: Record<string, [string, string]> = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/app.js': ['app.js', 'text/javascript; charset=utf-8'],
}

/** A short hash of the page files, in `PAGES` order, so an open page can tell its files changed. `null` when any file can't be read. */
export function pageVersion(dir: string): string | null {
  try {
    const hash = createHash('sha256')
    for (const [file] of Object.values(PAGES)) hash.update(readFileSync(join(dir, file))).update('\0')
    return hash.digest('hex').slice(0, 16)
  } catch {
    return null
  }
}

/** True when a dashboard for `root` answers on `port`. */
export async function healthy(port: number, root: string): Promise<boolean> {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(500) })
    if (!res.ok) return false
    const body = (await res.json()) as { ok?: unknown; root?: unknown }
    return body.ok === true && body.root === root
  } catch {
    return false
  }
}

/** The files `entry` loads: itself and every relative `.ts` or `.js` import it reaches, as real paths, sorted, each once. Bare and missing imports are skipped. */
export function codeFiles(entry: string): string[] {
  const seen = new Set<string>()
  const visit = (file: string) => {
    let real: string
    let text: string
    try {
      real = realpathSync(file)
      if (seen.has(real)) return
      text = readFileSync(real, 'utf8')
    } catch {
      return
    }
    seen.add(real)
    for (const m of text.matchAll(/\bfrom\s+['"](\.{1,2}\/[^'"]+\.(?:ts|js))['"]/g)) visit(resolve(dirname(real), m[1]))
  }
  visit(entry)
  return [...seen].sort()
}

/** A short hash of each path and its contents, `null` when there are no files or one can't be read. */
export function codeVersion(files: string[]): string | null {
  try {
    if (!files.length) return null
    const hash = createHash('sha256')
    for (const f of files) hash.update(f).update('\0').update(readFileSync(f)).update('\0')
    return hash.digest('hex').slice(0, 16)
  } catch {
    return null
  }
}

/** Decides when the server should restart: a new code version must be seen on two checks in a row, and one marked failed is skipped until a different version shows up. */
export function restartWatch(running: string | null): { check(version: string | null): boolean; failed(version: string): void } {
  let candidate: string | null = null
  let failedVersion: string | null = null
  return {
    check(version) {
      if (version === null) return false
      if (version === running) {
        candidate = failedVersion = null
        return false
      }
      if (version === failedVersion) {
        candidate = null
        return false
      }
      if (version !== candidate) {
        candidate = version
        return false
      }
      return true
    },
    failed(version) {
      failedVersion = version
      candidate = null
    },
  }
}

/** Imports `entry` in a fresh process, which loads every module and starts nothing. Resolves to the error's first line, or `null` when it loads. */
function preflight(entry: string): Promise<string | null> {
  return new Promise((done) => {
    const code = `await import(${JSON.stringify(pathToFileURL(entry).href)})`
    execFile(process.execPath, ['--input-type=module', '-e', code], { timeout: 15_000 }, (err, _out, stderr) => {
      if (!err) return done(null)
      const lines = String(stderr).split('\n').map((l) => l.trim()).filter(Boolean)
      done(lines.find((l) => /^\w*Error\b/.test(l)) ?? lines[0] ?? (err.killed ? 'the check timed out' : err.message))
    })
  })
}

/** The system light or dark setting from the result of `defaults read -g AppleInterfaceStyle`. `null` when it can't be told: another platform, or the command could not run or timed out. */
export function systemScheme(platform: string, result: { code: number | null; out: string } | null): 'dark' | 'light' | null {
  if (platform !== 'darwin' || result === null) return null
  // The key is absent in light mode, so the command exits non-zero. Exit 0 with any other text is not an answer.
  if (result.code !== 0) return 'light'
  return result.out.trim() === 'Dark' ? 'dark' : null
}

const macScheme = (): Promise<'dark' | 'light' | null> =>
  new Promise((done) => {
    if (process.platform !== 'darwin') return done(null)
    try {
      execFile('defaults', ['read', '-g', 'AppleInterfaceStyle'], { timeout: 2000 }, (err, out) => {
        // A number is the command's exit status; anything else (spawn error, timeout) means it did not run.
        const code = err === null ? 0 : typeof err.code === 'number' ? err.code : null
        done(systemScheme('darwin', code === null ? null : { code, out: String(out) }))
      })
    } catch {
      done(null)
    }
  })

/** Reads a file only when it is a regular file and every folder in `dirs` is a real folder (no links). */
export function readRegular(file: string, dirs: string[]): string | undefined {
  try {
    for (const d of dirs) if (!lstatSync(d).isDirectory()) return undefined
    if (!lstatSync(file).isFile()) return undefined
    return readFileSync(file, 'utf8')
  } catch {
    return undefined
  }
}

function readJson(file: string, dirs: string[]): unknown {
  try {
    const text = readRegular(file, dirs)
    return text === undefined ? undefined : JSON.parse(text)
  } catch {
    return undefined
  }
}

/** Writes a file of `.agent-team` through a temp file and a rename. Nothing is written unless `.agent-team` is a real folder and the file is absent or a regular file. */
function writeJson(agentDir: string, name: string, text: string): boolean {
  const file = join(agentDir, name)
  const tmp = join(agentDir, `${name}.${process.pid}.tmp`)
  try {
    if (!lstatSync(agentDir).isDirectory()) return false
    try {
      if (!lstatSync(file).isFile()) return false
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') return false
    }
    writeFileSync(tmp, text, { flag: 'wx' })
    renameSync(tmp, file)
    return true
  } catch {
    try {
      unlinkSync(tmp)
    } catch {}
    return false
  }
}

const MERGED_PAGE_SIZE = 10
const MERGED_PAGES = 20
const DETAIL_STAGES = ['awaiting-build', 'build', 'build-queued', 'awaiting-merge', 'merge', 'merge-queued']

/** The merged page the browser shows, from `?mergedPage=N` of a request url: an integer from 0 to 19, else 0. */
export function mergedPageOf(url: string): number {
  try {
    const raw = new URL(url, 'http://localhost').searchParams.get('mergedPage') ?? ''
    const n = /^\d{1,3}$/.test(raw) ? Number(raw) : 0
    return n < MERGED_PAGES ? n : 0
  } catch {
    return 0
  }
}

const PRESS_SCRIPT = `ObjC.import('ApplicationServices')
ObjC.import('AppKit')
ObjC.bindFunction('AXUIElementCopyAttributeValue', ['int', ['id', 'id', 'id*']])
ObjC.bindFunction('AXUIElementCreateApplication', ['id', ['int']])
ObjC.bindFunction('CFCopyDescription', ['id', ['id']])
ObjC.bindFunction('AXIsProcessTrusted', ['bool', []])
ObjC.bindFunction('AXUIElementCreateSystemWide', ['id', []])
ObjC.bindFunction('AXUIElementCopyElementAtPosition', ['int', ['id', 'float', 'float', 'id*']])
function attr(el, name) {
  const ref = Ref()
  return $.AXUIElementCopyAttributeValue(el, $(name), ref) === 0 ? ref[0] : null
}
function str(v) { return v === null ? '' : String(ObjC.unwrap(v)) }
function pair(v, a, b) {
  const m = ObjC.unwrap($.CFCopyDescription(v)).match(new RegExp(a + ':(-?[0-9.]+) ' + b + ':(-?[0-9.]+)'))
  return m ? [Number(m[1]), Number(m[2])] : null
}
function click(el) {
  const p = attr(el, 'AXPosition'), s = attr(el, 'AXSize')
  const at = p && pair(p, 'x', 'y'), size = s && pair(s, 'w', 'h')
  if (!at || !size || size[0] < 1 || size[1] < 1) return false
  const x = at[0] + size[0] / 2, y = at[1] + size[1] / 2
  const hit = Ref()
  if ($.AXUIElementCopyElementAtPosition($.AXUIElementCreateSystemWide(), x, y, hit) !== 0) return false
  let up = hit[0], onComposer = false
  for (let i = 0; i < 40 && up != null && !onComposer; i++) { onComposer = isComposer(up); up = attr(up, 'AXParent') }
  if (!onComposer) return false
  const pt = $.CGPointMake(x, y)
  const home = $.CGEventGetLocation($.CGEventCreate($()))
  for (const t of [$.kCGEventLeftMouseDown, $.kCGEventLeftMouseUp]) $.CGEventPost($.kCGHIDEventTap, $.CGEventCreateMouseEvent($(), t, pt, $.kCGMouseButtonLeft))
  $.CGWarpMouseCursorPosition(home)
  return true
}
function isComposer(el) {
  return el !== null && str(attr(el, 'AXRole')) === 'AXTextArea' && str(attr(el, 'AXDescription')).startsWith('Message ')
}
function frontId() {
  const f = $.NSWorkspace.sharedWorkspace.frontmostApplication
  return f ? str(f.bundleIdentifier) : ''
}
function isFront(app) {
  return ObjC.unwrap(attr(app, 'AXFrontmost')) === true
}
function run() {
  if (!$.AXIsProcessTrusted()) return 'permission'
  if (frontId() !== 'com.t3tools.t3code') return 'not-frontmost'
  const app = $.AXUIElementCreateApplication($.NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier)
  const focused = () => attr(app, 'AXFocusedUIElement')
  if (!isComposer(focused())) {
    const win = attr(app, 'AXFocusedWindow')
    let target = null
    const stack = win ? [[win, false]] : []
    for (let seen = 0; stack.length && seen < 3000 && target === null; seen++) {
      const [el, inWeb] = stack.pop()
      if (isComposer(el)) { target = el; break }
      const web = str(attr(el, 'AXRole')) === 'AXWebArea'
      if (web && inWeb) continue
      const kids = attr(el, 'AXChildren')
      if (kids) for (let i = kids.count - 1; i >= 0; i--) stack.push([kids.objectAtIndex(i), inWeb || web])
    }
    if (target === null) return 'no-focus'
    if (!click(target)) return 'no-focus'
    let ok = false
    for (let i = 0; i < 10 && !ok; i++) {
      delay(0.05)
      ok = isComposer(focused())
    }
    if (!ok) return 'no-focus'
  }
  if (!isFront(app)) return 'not-frontmost'
  Application('System Events').keyCode(36)
  return 'sent'
}`

/** Presses Return in T3 Code through a fixed JXA script (`osascript -l JavaScript`, no user text, no shell). The script checks Accessibility trust and that T3 Code is in front, clicks the message box (the mouse goes there and straight back) and re-reads the focused element, and presses Return only if the message box has focus. Resolves with the script's output (`sent`, `permission`, `not-frontmost` or `no-focus`); rejects on an osascript error or the 3 second timeout. */
export function pressReturnMac(): Promise<string> {
  if (process.platform !== 'darwin') return Promise.resolve('unsupported')
  return new Promise((resolve, reject) => {
    execFile('osascript', ['-l', 'JavaScript', '-e', PRESS_SCRIPT], { timeout: 3000 }, (err, stdout) => (err ? reject(err) : resolve(stdout)))
  })
}

/** The JSON answer for a press: `result` is the runner's output, or the error it failed with. */
export function pressResult(result: unknown): { sent: boolean; reason?: string } {
  if (typeof result === 'string') {
    const out = result.trim()
    if (out === 'sent') return { sent: true }
    return { sent: false, reason: out === 'not-frontmost' || out === 'unsupported' || out === 'no-focus' || out === 'permission' ? out : 'error' }
  }
  const e = result as { message?: unknown; stderr?: unknown } | null
  // -1743: not allowed to control System Events; 1002, -1719, -25211: no Accessibility.
  return { sent: false, reason: /\((?:-1743|1002|-1719|-25211)\)/.test(`${e?.message ?? ''} ${e?.stderr ?? ''}`) ? 'permission' : 'error' }
}

/** One run of `cos_user_check.py latest <thread> --after <after>` with `command` on stdin, the same check the Chief of Staff makes before it acts. `true` when it exits 0 (the user's message is there), `false` on exit 1 (not there yet), `'unchecked'` on any other exit, a timeout or a spawn error. */
export function checkSentPy(thread: string, command: string, after: string, db?: string): Promise<boolean | 'unchecked'> {
  return new Promise((done) => {
    // A thread id that starts with a dash would read as an option.
    if (thread.startsWith('-')) return done('unchecked')
    try {
      const child = execFile('python3', ['-I', join(import.meta.dirname, '..', 'cos_user_check.py'), ...(db === undefined ? [] : ['--db', db]), 'latest', thread, '--after', after], { timeout: 2000 }, (err) => {
        const code = (err as { code?: unknown } | null)?.code
        done(err === null ? true : code === 1 ? false : 'unchecked')
      })
      child.stdin?.on('error', () => {})
      child.stdin?.end(command)
    } catch {
      done('unchecked')
    }
  })
}

/** The body of a press request: at most 256 bytes, else `null`. Also `null` if the body has not ended after 2 seconds, so a stalled body cannot hold the press lock. Past 256 bytes it stops buffering and answers at once. */
function readBody(req: IncomingMessage): Promise<string | null> {
  return new Promise((done) => {
    const chunks: Buffer[] = []
    let size = 0
    const timer = setTimeout(() => done(null), 2000)
    const finish = (body: string | null) => {
      clearTimeout(timer)
      done(body)
    }
    req.on('data', (c: Buffer) => {
      size += c.length
      if (size <= 256) chunks.push(c)
      else finish(null)
    })
    req.on('end', () => finish(size <= 256 ? Buffer.concat(chunks).toString('utf8') : null))
    req.on('error', () => finish(null))
  })
}

const PRESS_COMMAND = /^(approve \d{1,7}|mark \d{1,7} todo)$/

/** The command in a press body (`{"command": "approve 402"}`), or `null` unless it is exactly `approve N` or `mark N todo`. */
export function pressCommand(body: string | null): string | null {
  try {
    const command = (JSON.parse(body ?? '') as { command?: unknown } | null)?.command
    return typeof command === 'string' && PRESS_COMMAND.test(command) ? command : null
  } catch {
    return null
  }
}

export async function startServer(opts: { root: string; port: number; scheme?: () => Promise<'dark' | 'light' | null>; pressReturn?: () => Promise<string>; checkSent?: (thread: string, command: string, after: string) => Promise<boolean | 'unchecked'>; viewerGh?: (args: string[]) => Promise<string> }): Promise<{ port: number; close(): Promise<void> }> {
  const { root } = opts
  const entry = import.meta.filename
  const running = codeVersion(codeFiles(entry))
  const agentDir = join(root, '.agent-team')
  let lastState: unknown = null
  const trackerTitles = createTitles({ run: ghRunner(root) })
  const merged = createMerged({ run: ghRunner(root) })
  const openPrs = createOpenPrs({ run: ghRunner(root) })
  const viewer = createViewer({ run: opts.viewerGh ?? ghRunner(root) })
  viewer.want()
  const updated = createUpdated({ run: ghRunner(root) })
  const backlog = createBacklog({ run: ghRunner(root) })
  const trackerLists = createTrackerLists({ read: () => readRegular(join(agentDir, 'tracker-lists.json'), [agentDir]) })
  const details = createDetails({ run: ghRunner(root), git: gitRunner(root) })
  const ci = createCi({ run: ghRunner(root) })

  // Worktree list for matching sessions to tickets: read once at start, then refreshed in the background, cached 30s, last good list kept.
  let worktrees: Worktree[] = []
  let worktreesAt = 0
  let worktreesBusy = false
  const refreshWorktrees = (): Promise<void> => {
    if (worktreesBusy || Date.now() - worktreesAt < 30_000) return Promise.resolve()
    worktreesBusy = true
    worktreesAt = Date.now()
    return new Promise((resolve) => {
      const done = (out?: string) => {
        worktreesBusy = false
        if (out !== undefined) worktrees = parseWorktrees(out)
        resolve()
      }
      try {
        execFile('git', ['-C', root, 'worktree', 'list', '--porcelain'], { timeout: 5000 }, (err, out) => done(err ? undefined : out))
      } catch {
        done()
      }
    })
  }

  // The first read finishes before the server answers, so the first /api already has the list.
  await refreshWorktrees()

  // The system light or dark setting, refreshed at start and every 5 seconds; requests only read the last answer.
  let theme: 'dark' | 'light' | null = null
  let themeBusy = false
  const refreshTheme = async () => {
    if (themeBusy) return
    themeBusy = true
    try {
      theme = await (opts.scheme ?? macScheme)()
    } catch {}
    themeBusy = false
  }
  await refreshTheme()

  const projectText = () => readRegular(join(root, 'docs/agents/project.md'), [join(root, 'docs'), join(root, 'docs/agents')])

  const readState = (): unknown => {
    const state = readJson(join(agentDir, 'state.json'), [agentDir])
    if (state !== undefined) lastState = state
    return lastState
  }

  const readSnapshots = (): unknown[] => {
    const snapshots: unknown[] = []
    try {
      const dir = join(agentDir, 'gantt')
      if (lstatSync(agentDir).isDirectory() && lstatSync(dir).isDirectory()) {
        for (const f of readdirSync(dir)) {
          if (!f.endsWith('.json')) continue
          const s = readJson(join(dir, f), [agentDir, dir])
          if (s !== undefined) snapshots.push(s)
        }
      }
    } catch {}
    return snapshots
  }

  // The spend ledger and the gantt history: loaded at start, updated every 30 seconds whether or not the page polls, each rewritten only when it changed.
  let ledger = parseLedger(readRegular(join(agentDir, 'spend.json'), [agentDir]) ?? '')
  let history = parseHistory(readRegular(join(agentDir, 'gantt-history.json'), [agentDir]) ?? '')
  const written: Record<string, string> = { 'spend.json': JSON.stringify(ledger), 'gantt-history.json': JSON.stringify(history) }
  const save = (name: string, value: unknown) => {
    try {
      const next = JSON.stringify(value)
      if (next !== written[name] && writeJson(agentDir, name, next)) written[name] = next
    } catch {}
  }
  const recordRound = () => {
    let matched: ReturnType<typeof ledgerSessions> = []
    let team: ReturnType<typeof teamSessions> = []
    try {
      const text = projectText()
      void refreshWorktrees()
      const snapshots = readSnapshots()
      const state = readState()
      const now = Date.now()
      matched = ledgerSessions({ snapshots, worktrees, state, prefix: text === undefined ? null : prefixFromProject(text), retired: text === undefined ? undefined : retiredFromProject(text), heads: text === undefined ? undefined : headsFromProject(text), now })
      team = teamSessions({ snapshots, state, now })
    } catch {}
    try {
      ledger = recordSpend(ledger, matched)
    } catch {}
    try {
      history = recordTeamHistory(recordHistory(history, matched), team)
    } catch {}
    save('spend.json', ledger)
    save('gantt-history.json', history)
  }
  recordRound()
  const spendTimer = setInterval(recordRound, 30_000)
  spendTimer.unref()

  // A backup of the ledger, the history and the state once a day, for a dashboard that runs for days; a failure is ignored.
  const backupTimer = setInterval(() => {
    try {
      backup({ root, now: new Date() })
    } catch {}
  }, 24 * 3600 * 1000)
  backupTimer.unref()
  let restartError: string | null = null
  let trackerError: string | null = null

  const api = (mergedPage: number) => {
    readState()
    const snapshots = readSnapshots()
    const dash = readJson(join(agentDir, 'dashboard.json'), [agentDir])
    const envId = (dash as { environmentId?: unknown } | undefined)?.environmentId
    let repo = null
    let links: TrackerLinks | null = null
    let titleCfg: TitleConfig | null = null
    let mergedCfg: MergedConfig | null = null
    let required: string[] | null = null
    let prefix: string | null = null
    let retired: Retired = []
    let heads: string[] | undefined
    try {
      const text = projectText()
      if (text !== undefined) {
        repo = repoUrlFromProject(text)
        links = trackerLinksFromProject(text)
        prefix = prefixFromProject(text)
        retired = retiredFromProject(text, prefix)
        heads = headsFromProject(text)
        const rows = requiredFromProject(text)
        required = rows.none ? null : rows.names
        const slug = repo ? slugFromUrl(repo.url) : null
        if (prefix && slug && repo) {
          mergedCfg = { prefix, retired, slug, issueUrls: repo.isGithubIssues, issueUrl: links?.issue, heads }
          if (repo.isGithubIssues) titleCfg = { prefix, retired, slug }
        }
      }
    } catch {}
    const tickets = (lastState as { tickets?: unknown } | null)?.tickets
    const wants: DetailWant[] = []
    merged.want(mergedCfg)
    openPrs.want(mergedCfg)
    viewer.want()
    const mergedAll = merged.get()
    const mergedPrs = new Set(mergedAll.map((e) => `${e.id}#${e.number}`))
    const ganttIds = historyByTicket(history)
    const ciWants: CiWant[] = []
    if (typeof tickets === 'object' && tickets !== null && !Array.isArray(tickets)) {
      trackerTitles.want(Object.keys(tickets), titleCfg)
      for (const [id, t] of Object.entries(tickets)) {
        const { stage, specPath, specSha, pr } = (t ?? {}) as Record<string, unknown>
        if (typeof stage === 'string' && DETAIL_STAGES.includes(stage)) wants.push({ id, stage, specPath, specSha, pr })
        if (!mergedPrs.has(`${id}#${pr}`)) ciWants.push({ id, pr })
      }
    }
    const shown = mergedAll.slice(mergedPage * MERGED_PAGE_SIZE, (mergedPage + 1) * MERGED_PAGE_SIZE)
    for (const e of shown) {
      wants.push({ id: e.id, stage: 'merged', pr: e.number, merged: true })
      if (ganttIds[e.id]?.length) ciWants.push({ id: e.id, pr: e.number, merged: true })
    }
    details.want(wants, mergedCfg)
    ci.want(ciWants, mergedCfg && required ? { slug: mergedCfg.slug, required } : null)
    updated.want(titleCfg)
    // Linear and Jira are not reachable from here; the Chief of Staff saves their Todo and Backlog lists in a file.
    // The file's change stamp is read on every tracker: on GitHub a new one reads the issues again now.
    const fromFile = repo !== null && !repo.isGithubIssues && prefix !== null
    trackerLists.want(prefix, fromFile, retired)
    backlog.want(titleCfg, trackerLists.changed())
    trackerError = fromFile ? trackerLists.error() : backlog.error()
    void refreshWorktrees()
    return buildApi({ state: lastState, snapshots, repo, links, titles: trackerTitles.get(), environmentId: typeof envId === 'string' ? envId : null, now: Date.now(), worktrees, prefix, retired, heads, merged: mergedAll, openPrs: openPrs.get(), openOwners: openPrs.owners(), issueOwners: trackerTitles.owners(), viewer: viewer.get(), updated: updated.get(), spend: spendByTicket(ledger), history: ganttIds, details: details.get(), ci: ci.get(), teamHistory: teamHistory(history), backlog: fromFile ? trackerLists.get() : backlog.get(), relations: fromFile ? {} : backlog.relations() })
  }

  const token = randomBytes(32).toString('hex')
  const pressReturn = opts.pressReturn ?? pressReturnMac
  const checkSent = opts.checkSent ?? checkSentPy
  let lastPress = 0
  let pressing = false
  /** After a press that answered `sent`, asks `checkSent` every 300 ms for up to 3 seconds whether T3 recorded the command as the user's message. */
  const confirm = async (command: string, after: string): Promise<{ sent: boolean; reason?: string }> => {
    const thread = cleanThreadId((readState() as { chiefThreadId?: unknown } | null)?.chiefThreadId)
    if (thread === null) return { sent: false, reason: 'unchecked' }
    const deadline = Date.now() + 3000
    for (;;) {
      const found = await checkSent(thread, command, after).catch((): 'unchecked' => 'unchecked')
      if (found === true) return { sent: true }
      if (found === 'unchecked') return { sent: false, reason: 'unchecked' }
      if (Date.now() + 300 > deadline) return { sent: false, reason: 'not-recorded' }
      await new Promise((r) => setTimeout(r, 300))
    }
  }
  const press = async (req: IncomingMessage, send: (status: number, body: string, type?: string) => void, port: number) => {
    const arrived = new Date().toISOString()
    const origin = req.headers.origin
    const site = req.headers['sec-fetch-site']
    const got = Buffer.from(String(req.headers['x-dashboard-token'] ?? ''))
    const want = Buffer.from(token)
    if ((origin !== `http://127.0.0.1:${port}` && origin !== `http://localhost:${port}`) || (site !== undefined && site !== 'same-origin') || got.length !== want.length || !timingSafeEqual(got, want)) return send(403, 'forbidden')
    const json = (answer: { sent: boolean; reason?: string }) => send(200, JSON.stringify(answer), 'application/json')
    if (pressing || Date.now() - lastPress < 3000) {
      req.resume()
      return json({ sent: false, reason: 'busy' })
    }
    pressing = true
    try {
      const command = pressCommand(await readBody(req))
      if (command === null) {
        send(400, 'bad request')
        // An oversize or stalled body may still be coming: close once the 400 is written.
        req.socket.destroySoon()
        return
      }
      lastPress = Date.now()
      await new Promise((r) => setTimeout(r, 1200))
      const answer = pressResult(await pressReturn().catch((e: unknown) => e ?? new Error('failed')))
      json(answer.sent ? await confirm(command, arrived) : answer)
    } finally {
      pressing = false
    }
  }

  const server: Server = createServer({ requireHostHeader: false }, (req, res) => {
    const send = (status: number, body: string, type = 'text/plain; charset=utf-8') => {
      const headers: Record<string, string> = { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }
      if (path === '/') {
        // No other page may frame the dashboard: a framed Approve would carry the token and press Return.
        headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https://avatars.githubusercontent.com; frame-ancestors 'none'"
        headers['X-Frame-Options'] = 'DENY'
      }
      res.writeHead(status, headers)
      res.end(body)
    }
    const path = (req.url ?? '/').split('?')[0]
    const port = (server.address() as { port: number }).port
    const host = req.headers.host
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return send(403, 'forbidden')
    if (path === '/press-return') return req.method === 'POST' ? void press(req, send, port) : send(405, 'method not allowed')
    if (req.method !== 'GET') return send(405, 'method not allowed')
    try {
      if (path === '/health') return send(200, JSON.stringify({ ok: true, root, code: running, pid: process.pid }), 'application/json')
      if (path === '/api') return send(200, JSON.stringify({ ...api(mergedPageOf(req.url ?? '/')), version: pageVersion(join(import.meta.dirname, 'page')), restartError, trackerError, theme }), 'application/json')
      const page = Object.hasOwn(PAGES, path) ? PAGES[path] : undefined
      if (page) {
        try {
          const text = readFileSync(join(import.meta.dirname, 'page', page[0]), 'utf8')
          const themed = path === '/' && theme ? text.replace('<html lang="en">', `<html lang="en" data-theme="${theme}">`) : text
          return send(200, path === '/' ? themed.replace('<meta name="dashboard-token" content="">', `<meta name="dashboard-token" content="${token}">`) : themed, page[1])
        } catch {
          return send(404, 'not found')
        }
      }
      return send(404, 'not found')
    } catch {
      return send(500, 'error')
    }
  })

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(opts.port, '127.0.0.1', resolve)
  })
  const bound = (server.address() as { port: number }).port

  // Every 5 seconds: if the code this server loaded has changed, replace this process with a new one on the same root and port.
  const watch = restartWatch(running)
  let restarting = false
  const newServerUp = async (pid: number | undefined): Promise<boolean> => {
    try {
      const res = await fetch(`http://127.0.0.1:${bound}/health`, { signal: AbortSignal.timeout(500) })
      const body = (await res.json()) as { root?: unknown; code?: unknown; pid?: unknown }
      // Only the child just spawned counts, on any code but ours, so a second change during the wait does not roll back a good server.
      return body.root === root && body.pid === pid && typeof body.code === 'string' && body.code !== running
    } catch {
      return false
    }
  }
  const swap = async (version: string) => {
    const fail = (why: string) => {
      watch.failed(version)
      restartError = `Server code changed but did not load: ${why}`
    }
    const broken = await preflight(entry)
    if (broken !== null) return fail(broken)
    await new Promise<void>((done) => {
      server.close(() => done())
      server.closeAllConnections()
    })
    const child = spawn(process.execPath, [entry, '--root', root, '--port', String(bound)], { detached: true, stdio: 'ignore' })
    let gone = false
    child.once('error', () => (gone = true))
    child.once('exit', () => (gone = true))
    child.unref()
    const deadline = Date.now() + 15_000
    while (Date.now() < deadline && !gone && !(await newServerUp(child.pid))) await new Promise((r) => setTimeout(r, 100))
    if (!gone && (await newServerUp(child.pid))) {
      const dash = readJson(join(agentDir, 'dashboard.json'), [agentDir]) as { environmentId?: unknown } | undefined
      writeJson(agentDir, 'dashboard.json', JSON.stringify({ pid: child.pid, port: bound, environmentId: dash?.environmentId }))
      process.exit(0)
    }
    try {
      if (child.pid) process.kill(child.pid)
    } catch {}
    // Let the child release the port before taking it back.
    for (let i = 0; i < 20 && !gone; i++) await new Promise((r) => setTimeout(r, 100))
    try {
      await new Promise<void>((done, reject) => {
        server.once('error', reject)
        server.listen(bound, '127.0.0.1', done)
      })
    } catch {
      process.exit(1)
    }
    fail('the new server did not start')
  }
  const codeTimer = setInterval(() => {
    void refreshTheme()
    if (restarting) return
    const version = codeVersion(codeFiles(entry))
    if (version === running) restartError = null
    if (!watch.check(version) || version === null) return
    restarting = true
    swap(version).catch(() => {}).finally(() => (restarting = false))
  }, 5000)
  codeTimer.unref()

  return {
    port: bound,
    close: () =>
      new Promise<void>((resolve) => {
        clearInterval(spendTimer)
        clearInterval(backupTimer)
        clearInterval(codeTimer)
        server.close(() => resolve())
        server.closeAllConnections()
      }),
  }
}

const isMain = (() => {
  try {
    return !!process.argv[1] && realpathSync(process.argv[1]) === import.meta.filename
  } catch {
    return false
  }
})()

if (isMain) {
  const arg = (n: string) => {
    const i = process.argv.indexOf(n)
    return i >= 0 ? process.argv[i + 1] : undefined
  }
  const root = arg('--root')
  const port = Number(arg('--port') ?? 0)
  if (!root || !Number.isInteger(port)) {
    console.error('usage: node server.ts --root <dir> --port <n>')
    process.exit(2)
  }
  const s = await startServer({ root, port })
  console.log(`dashboard listening on 127.0.0.1:${s.port}`)
}

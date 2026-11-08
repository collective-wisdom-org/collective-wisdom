import { createHash } from 'node:crypto'
import { homedir } from 'node:os'
import { lstatSync, mkdirSync, readdirSync, realpathSync, renameSync, rmSync, statSync, unlinkSync, writeFileSync } from 'node:fs'
import { basename, join } from 'node:path'
import { healthy, readRegular } from './server.ts'

const FILES = ['spend.json', 'gantt-history.json', 'state.json']
const SET_NAME = /^\d{8}T\d{6}Z(-\d+)?$/

export type BackupResult = {
  error?: string
  /** Name of the new set folder; absent when nothing was written. */
  set?: string
  unchanged?: boolean
  /** One entry per file: saved into the new set, or skipped with the reason. */
  files: { name: string; status: 'saved' | 'skipped'; reason?: string }[]
}

export type RestoreResult = {
  error?: string
  files: { name: string; status: 'restored' | 'kept' | 'missing' | 'refused'; from?: string }[]
}

/** `~/.agent-team-backups/<folder name>-<hash>/`; the hash is of the root path, as in `portFor`. */
export function backupDir(root: string, home: string = homedir()): string {
  const name = basename(root).replace(/[^A-Za-z0-9._-]/g, '-')
  const hash = createHash('sha1').update(root).digest('hex').slice(0, 8)
  return join(home, '.agent-team-backups', `${name}-${hash}`)
}

/** The folders a backup lives in, outermost first: just `dest` when it is given. */
function backupFolders(root: string, dest?: string): string[] {
  if (dest) return [dest]
  const repo = backupDir(root)
  return [join(repo, '..'), repo]
}

/** An error message when `dir` exists and is not a real folder; a missing folder is fine. */
function notAFolder(dir: string, label: string): string | undefined {
  try {
    const st = lstatSync(dir, { throwIfNoEntry: false })
    return st && !st.isDirectory() ? `${label} is not a real folder: ${dir}` : undefined
  } catch (e) {
    return `${label} can't be read: ${(e as Error).message}`
  }
}

function refusal(root: string, dest?: string): string | undefined {
  const agent = notAFolder(join(root, '.agent-team'), '.agent-team')
  if (agent) return agent
  const folders = backupFolders(root, dest)
  for (const f of folders) {
    const err = notAFolder(f, 'backup folder')
    if (err) return err
  }
  return undefined
}

const validJson = (text: string) => {
  try {
    JSON.parse(text)
    return true
  } catch {
    return false
  }
}

const order = (name: string): [string, number] => {
  const [base, n] = name.split('-')
  return [base, n ? Number(n) : 1]
}

/** Set folders in `dest`, oldest first. Only real folders with a set name count. */
function listSets(dest: string): string[] {
  try {
    return readdirSync(dest)
      .filter((n) => {
        try {
          return SET_NAME.test(n) && lstatSync(join(dest, n)).isDirectory()
        } catch {
          return false
        }
      })
      .sort((a, b) => {
        const [x, y] = [order(a), order(b)]
        return x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : x[1] - y[1]
      })
  } catch {
    return []
  }
}

const readCopy = (dest: string, set: string, name: string) => readRegular(join(dest, set, name), [dest, join(dest, set)])

export function backup(opts: { root: string; dest?: string; keep?: number; now: Date }): BackupResult {
  const { root, keep = 14, now } = opts
  const dest = opts.dest ?? backupDir(root)
  const result: BackupResult = { files: [] }
  const refused = refusal(root, opts.dest)
  if (refused) return { ...result, error: refused }

  const agentDir = join(root, '.agent-team')
  const found: Record<string, string> = {}
  for (const name of FILES) {
    const text = readRegular(join(agentDir, name), [agentDir])
    if (text === undefined) result.files.push({ name, status: 'skipped', reason: 'missing or not a regular file' })
    else if (!validJson(text)) result.files.push({ name, status: 'skipped', reason: 'not valid JSON' })
    else found[name] = text
  }
  const names = Object.keys(found)
  const sets = listSets(dest)
  const newest = sets[sets.length - 1]
  if (names.length === 0 || (newest !== undefined && names.every((n) => readCopy(dest, newest, n) === found[n]))) {
    return { ...result, unchanged: true }
  }

  const stamp = now.toISOString().replace(/\.\d+Z$/, 'Z').replace(/[-:]/g, '')
  try {
    mkdirSync(dest, { recursive: true, mode: 0o700 })
  } catch (e) {
    return { ...result, error: `can't create ${dest}: ${(e as Error).message}` }
  }
  let set = stamp
  for (let n = 2; ; n++) {
    try {
      mkdirSync(join(dest, set), { mode: 0o700 })
      break
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'EEXIST') return { ...result, error: `can't create a set in ${dest}: ${(e as Error).message}` }
      set = `${stamp}-${n}`
    }
  }
  // A skipped file keeps its newest valid copy in the new set, so pruning old sets never drops the last good one.
  const toWrite = { ...found }
  for (const name of FILES) {
    if (name in toWrite) continue
    for (const old of sets.slice().reverse()) {
      const text = readCopy(dest, old, name)
      if (text !== undefined && validJson(text)) {
        toWrite[name] = text
        break
      }
    }
  }
  try {
    for (const [name, text] of Object.entries(toWrite)) writeFileSync(join(dest, set, name), text, { flag: 'wx', mode: 0o600 })
  } catch (e) {
    rmSync(join(dest, set), { recursive: true, force: true })
    return { ...result, error: `can't write the backup: ${(e as Error).message}` }
  }
  result.set = set
  for (const name of names) result.files.push({ name, status: 'saved' })

  const all = listSets(dest)
  for (const old of all.slice(0, Math.max(0, all.length - keep))) {
    try {
      rmSync(join(dest, old), { recursive: true, force: true })
    } catch {}
  }
  return result
}

export async function restore(opts: { root: string; dest?: string; force?: boolean; now?: Date }): Promise<RestoreResult> {
  const { root, force = false } = opts
  const dest = opts.dest ?? backupDir(root)
  const result: RestoreResult = { files: [] }
  const refused = refusal(root, opts.dest)
  if (refused) return { ...result, error: refused }

  const agentDir = join(root, '.agent-team')
  if (!statSync(root, { throwIfNoEntry: false })?.isDirectory()) return { ...result, error: `root is not a folder: ${root}` }
  if (!lstatSync(agentDir, { throwIfNoEntry: false })) mkdirSync(agentDir)

  try {
    const dash = JSON.parse(readRegular(join(agentDir, 'dashboard.json'), [agentDir]) ?? 'null') as { port?: unknown } | null
    if (dash && Number.isInteger(dash.port) && (await healthy(dash.port as number, root))) {
      return { ...result, error: `the dashboard is running on port ${dash.port}; stop it first (kill the pid in .agent-team/dashboard.json)` }
    }
  } catch {}

  const sets = listSets(dest).reverse()
  const picks = FILES.map((name) => {
    for (const set of sets) {
      const text = readCopy(dest, set, name)
      if (text !== undefined && validJson(text)) return { name, set, text }
    }
    return { name }
  })
  const exists = (name: string) => lstatSync(join(agentDir, name), { throwIfNoEntry: false })

  // --force replaces files, so keep what is there in a new set first; the set pruning is off so no good copy is pushed out.
  if (force && picks.some((p) => p.set && exists(p.name)?.isFile())) {
    const saved = backup({ root, dest, keep: Infinity, now: opts.now ?? new Date() })
    if (saved.error) return { ...result, error: saved.error }
  }

  for (const p of picks) {
    const st = exists(p.name)
    if (st && !st.isFile()) result.files.push({ name: p.name, status: 'refused' })
    else if (st && (!force || !p.set)) result.files.push({ name: p.name, status: 'kept' })
    else if (!p.set) result.files.push({ name: p.name, status: 'missing' })
    else {
      const tmp = join(agentDir, `${p.name}.${process.pid}.tmp`)
      try {
        writeFileSync(tmp, p.text!, { flag: 'wx', mode: 0o600 })
        renameSync(tmp, join(agentDir, p.name))
        result.files.push({ name: p.name, status: 'restored', from: p.set })
      } catch {
        try {
          unlinkSync(tmp)
        } catch {}
        result.files.push({ name: p.name, status: 'refused' })
      }
    }
  }
  if (result.files.some((f) => f.status === 'refused')) result.error = 'some files could not be restored'
  return result
}

const isMain = (() => {
  try {
    return !!process.argv[1] && realpathSync(process.argv[1]) === import.meta.filename
  } catch {
    return false
  }
})()

if (isMain) {
  if (Number(process.versions.node.split('.')[0]) < 24) {
    console.error('backup needs Node 24 or newer')
    process.exit(1)
  }
  const usage = () => {
    console.error('usage: node backup.ts --root <dir> [--dest <dir>] [--keep <n>]\n       node backup.ts restore --root <dir> [--dest <dir>] [--force]')
    process.exit(2)
  }
  const args = process.argv.slice(2)
  const isRestore = args[0] === 'restore'
  if (isRestore) args.shift()
  const flags: Record<string, string> = {}
  let force = false
  for (let i = 0; i < args.length; i++) {
    const a = args[i]
    if (isRestore && a === '--force') force = true
    else if (['--root', '--dest', ...(isRestore ? [] : ['--keep'])].includes(a) && args[i + 1] !== undefined) flags[a] = args[++i]
    else usage()
  }
  const keep = flags['--keep'] === undefined ? undefined : Number(flags['--keep'])
  if (!flags['--root'] || (keep !== undefined && !(Number.isInteger(keep) && keep >= 1))) usage()
  const base = { root: flags['--root'], dest: flags['--dest'] }
  if (isRestore) {
    const r = await restore({ ...base, force })
    for (const f of r.files) console.log(`${f.name}: ${f.status === 'restored' ? `restored from ${f.from}` : f.status === 'missing' ? 'not in any backup' : f.status}`)
    if (r.error) console.error(r.error)
    process.exit(r.error ? 1 : 0)
  } else {
    const r = backup({ ...base, keep, now: new Date() })
    for (const f of r.files) console.log(`${f.name}: ${f.status === 'saved' ? `saved in ${r.set}` : `skipped (${f.reason})`}`)
    if (r.unchanged) console.log('unchanged: no new set')
    if (r.error) console.error(r.error)
    process.exit(r.error ? 1 : 0)
  }
}

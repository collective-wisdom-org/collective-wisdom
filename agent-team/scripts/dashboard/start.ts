import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createServer } from 'node:net'
import { lstatSync, mkdirSync, readdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { readRegular } from './server.ts'

const DAY_MS = 24 * 3600 * 1000

export function portFor(root: string): number {
  const n = createHash('sha1').update(root).digest().readUInt32BE(0)
  return 47000 + (n % 1000)
}

async function healthy(port: number, root: string): Promise<boolean> {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(500) })
    if (!res.ok) return false
    const body = (await res.json()) as { ok?: unknown; root?: unknown }
    return body.ok === true && body.root === root
  } catch {
    return false
  }
}

function portFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const s = createServer()
    s.once('error', () => resolve(false))
    s.listen(port, '127.0.0.1', () => s.close(() => resolve(true)))
  })
}

function readDashboard(file: string, agentDir: string): { pid?: number; port?: number; environmentId?: string } | undefined {
  try {
    const text = readRegular(file, [agentDir])
    return text === undefined ? undefined : JSON.parse(text)
  } catch {
    return undefined
  }
}

/** Writes through a temp file and a rename, so a link at `file` is replaced, never followed. */
function writeDashboard(agentDir: string, file: string, data: object) {
  const tmp = join(agentDir, `dashboard.json.${process.pid}.tmp`)
  try {
    writeFileSync(tmp, JSON.stringify(data), { flag: 'wx' })
    renameSync(tmp, file)
  } catch (e) {
    try {
      unlinkSync(tmp)
    } catch {}
    throw e
  }
}

function pruneSnapshots(agentDir: string) {
  try {
    const dir = join(agentDir, 'gantt')
    if (!lstatSync(agentDir).isDirectory() || !lstatSync(dir).isDirectory()) return
    for (const f of readdirSync(dir)) {
      try {
        if (!f.endsWith('.json')) continue
        const p = join(dir, f)
        const st = lstatSync(p)
        if (st.isFile() && Date.now() - st.mtimeMs > DAY_MS) unlinkSync(p)
      } catch {}
    }
  } catch {}
}

export async function startDashboard(opts: {
  root: string
  environmentId?: string
  basePort?: number
}): Promise<{ url: string; started: boolean }> {
  const { root } = opts
  const agentDir = join(root, '.agent-team')
  const file = join(agentDir, 'dashboard.json')
  const st = lstatSync(agentDir, { throwIfNoEntry: false })
  if (!st) mkdirSync(agentDir, { recursive: true })
  else if (!st.isDirectory()) throw new Error('.agent-team is not a real folder')
  pruneSnapshots(agentDir)

  const existing = readDashboard(file, agentDir)
  if (existing && Number.isInteger(existing.port) && (await healthy(existing.port!, root))) {
    const environmentId = opts.environmentId ?? existing.environmentId
    if (environmentId !== existing.environmentId) {
      writeDashboard(agentDir, file, { pid: existing.pid, port: existing.port, environmentId })
    }
    return { url: `http://127.0.0.1:${existing.port}/`, started: false }
  }

  let port = opts.basePort ?? portFor(root)
  const limit = port + 200
  while (port < limit && !(await portFree(port))) port++
  if (port >= limit) throw new Error('no free port for the dashboard')

  const serverPath = join(import.meta.dirname, 'server.ts')
  const child = spawn(process.execPath, [serverPath, '--root', root, '--port', String(port)], {
    detached: true,
    stdio: 'ignore',
  })
  let exited = false
  child.once('error', () => (exited = true))
  child.once('exit', () => (exited = true))
  child.unref()

  const deadline = Date.now() + 3000
  let up = false
  while (Date.now() < deadline && !exited) {
    if (await healthy(port, root)) {
      up = true
      break
    }
    await new Promise((r) => setTimeout(r, 50))
  }
  if (!up) {
    try {
      if (child.pid) process.kill(child.pid)
    } catch {}
    throw new Error('dashboard did not start')
  }

  writeDashboard(agentDir, file, { pid: child.pid, port, environmentId: opts.environmentId })
  return { url: `http://127.0.0.1:${port}/`, started: true }
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
    console.error('dashboard needs Node 24 or newer')
    process.exit(1)
  }
  const arg = (n: string) => {
    const i = process.argv.indexOf(n)
    return i >= 0 ? process.argv[i + 1] : undefined
  }
  const root = arg('--root')
  if (!root) {
    console.error('usage: node start.ts --root <dir> [--environment-id <id>]')
    process.exit(2)
  }
  try {
    const r = await startDashboard({ root, environmentId: arg('--environment-id') })
    console.log(r.url)
    process.exit(0)
  } catch (e) {
    console.error(`dashboard failed to start: ${(e as Error).message}`)
    process.exit(1)
  }
}

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer, TurnUsage } from 'claude-code'

import type { AgentRecord, PriceState, Prices, Tokens } from '../types/index.d.ts'
import { bar, clock, dollars, fit, tokens } from './format.ts'
import { buildRows, MAIN } from './rows.ts'
import { buildSnapshot, snapshotName } from './snapshot.ts'

const PANE = 'agent-gantt'
const TICK_MS = 5000
// Relative to the user's home folder: the machine install's copy of the price table.
const PRICES_PATH = '.collective-wisdom/scripts/prices.json'
const PRICES_NOTE = '~/.collective-wisdom/scripts/prices.json is missing or unreadable. Run ./install.sh in the collective-wisdom clone.'
// Agent states that count as still working. Anything else (completed, failed, killed, idle) is over.
const ACTIVE = new Set(['pending', 'running', 'waiting'])
// Relative to the root checkout: where the local dashboard looks for each session's rows.
const SNAPSHOT_DIR = '.agent-team/gantt'

// Change a tag when the fields of its value change: an older value is read as the initial.
const records = atom({ plugin: 'agent-gantt', key: 'records' } as const, [] as AgentRecord[], {
  shape: 'records-1',
})
const prices = atom(
  { plugin: 'agent-gantt', key: 'prices' } as const,
  { isLoaded: false, table: null, note: '' } as PriceState,
  { shape: 'prices-1' },
)
const clockAtom = atom({ plugin: 'agent-gantt', key: 'now' } as const, 0)

// The tick lives and dies with this module, like every timer.
let tick: Timer | null = null

const ZERO: Tokens = { input: 0, output: 0, read: 0, write: 0 }

function addUsage(prev: Record<string, Tokens>, u: TurnUsage): Record<string, Tokens> {
  const t = prev[u.model] ?? ZERO
  return {
    ...prev,
    [u.model]: {
      input: t.input + (u.input_tokens ?? 0),
      output: t.output + (u.output_tokens ?? 0),
      read: t.read + (u.cache_read_input_tokens ?? 0),
      write: t.write + (u.cache_creation_input_tokens ?? 0),
    },
  }
}

/** Reads ~/.collective-wisdom/scripts/prices.json, built from HOME because $.fs does not expand ~. A miss, or no HOME, leaves the cost column as a dash. */
async function loadPrices($: EngineInterface, isForced = false) {
  if (!isForced && (await read($, prices)).isLoaded) return
  let state: PriceState
  try {
    const home = await $.env.get('HOME')
    if (!home) throw new Error('HOME is not set')
    const table = JSON.parse(await $.fs.read(`${home}/${PRICES_PATH}`)) as Prices
    state = { isLoaded: true, table, note: '' }
  } catch {
    state = { isLoaded: true, table: null, note: PRICES_NOTE }
  }
  await update($, prices, () => state)
}

/** The main loop's own record, made once. It starts when the mod first sees the session. */
async function ensureMain($: EngineInterface, t: number) {
  const cwd = await $.session.cwd()
  await update($, records, list =>
    list.some(r => r.id === MAIN)
      ? list
      : [{ id: MAIN, parentId: null, name: 'main', type: 'main', cwd, start: t, end: null, last: t, usage: {} }, ...list],
  )
}

// The root checkout, resolved once. Null until the first resolve.
let root: string | null = null
// Whether that root uses the team, checked once. A repo that does not gets no `.agent-team/` folder.
let usesTeam = false

/** The root checkout the way status-pane finds it: only the plain `<root>/.git` layout; else the session's own folder. */
async function resolveRoot($: EngineInterface): Promise<string> {
  if (root !== null) return root
  const cwd = await $.session.cwd()
  let found = cwd
  try {
    const { exitCode, stdout } = await $.process.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'])
    const common = stdout.trim()
    if (exitCode === 0 && /^\/[^\n]*\/\.git$/.test(common)) found = common.slice(0, common.lastIndexOf('/'))
  } catch {
    // not a git checkout: keep the session's folder
  }
  usesTeam = false
  for (const marker of ['docs/agents/project.md', '.agent-team/state.json']) {
    try {
      await $.fs.read(`${found}/${marker}`)
      usesTeam = true
      break
    } catch {
      // not there
    }
  }
  root = found
  return root
}

/** Writes this session's rows for the local dashboard. A failed write never reaches the session. */
async function writeSnapshot($: EngineInterface) {
  try {
    const dir = await resolveRoot($)
    if (!usesTeam) return
    const sessionId = await $.session.id()
    const name = snapshotName(sessionId)
    if (name === null) return
    const rows = buildRows(await read($, records), await $.agent.list(), (await read($, prices)).table)
    const total = (await $.session.usage()).cost?.usd ?? null
    const text = buildSnapshot({ sessionId, cwd: await $.session.cwd(), updatedAt: await $.clock.now(), total, rows })
    await $.fs.write(`${dir}/${SNAPSHOT_DIR}/${name}`, text)
  } catch {
    // the dashboard is optional: skip this write
  }
}

/** Moves `now`, stamps the end of agents that stopped running, and starts or stops the tick to match. */
async function refresh($: EngineInterface) {
  const t = await $.clock.now()
  await update($, clockAtom, () => t)
  const active = new Set((await $.agent.list()).filter(a => ACTIVE.has(a.status)).map(a => a.id))
  await update($, records, list =>
    list.map(r => {
      if (r.id === MAIN) return r
      if (active.has(r.id)) return r.end === null ? r : { ...r, end: null }
      return r.end !== null ? r : { ...r, end: r.last }
    }),
  )
  const isRunning = (await read($, records)).some(r => r.id !== MAIN && r.end === null)
  if (isRunning && !tick) tick = $.clock.every(TICK_MS, () => void refresh($))
  if (!isRunning && tick) {
    tick.cancel()
    tick = null
  }
  await writeSnapshot($)
}

async function openPane($: EngineInterface) {
  try {
    await $.ui.open({ id: PANE, title: 'Agents' })
  } catch {
    // A session with nothing to draw into (-p, an SDK host) has no pane. The records still keep.
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'agent-gantt',
      description: 'Show this session\'s agents as a Gantt chart in a pane',
    })
    await ensureMain($, await $.clock.now())
    await loadPrices($)
    await refresh($)
    return next(e)
  })

  on('command.run', { command: 'agent-gantt' }, async $ => {
    await ensureMain($, await $.clock.now())
    await loadPrices($, true)
    await refresh($)
    await openPane($)
    return { text: 'Agent pane opened.' }
  })

  on('agent.spawn', async ($, e, next) => {
    const out = await next(e)
    if (out.deny !== undefined || out.agentId === undefined) return out
    const id = out.agentId
    const t = await $.clock.now()
    await ensureMain($, t)
    await loadPrices($)
    const isFirst = (await read($, records)).length <= 1
    const record: AgentRecord = {
      id,
      parentId: e.parentAgentId ?? MAIN,
      name: e.name ?? e.description,
      type: e.subagentType,
      cwd: e.cwd ?? (await $.session.cwd()),
      start: t,
      end: null,
      last: t,
      usage: {},
    }
    await update($, records, list => (list.some(r => r.id === id) ? list : [...list, record]))
    await refresh($)
    if (isFirst) await openPane($)
    return out
  })

  on('turn.complete', async ($, e, next) => {
    const t = await $.clock.now()
    const out = await next(e)
    const id = e.agentId ?? MAIN
    if (id === MAIN) await ensureMain($, t)
    const { usage } = e
    await update($, records, list =>
      list.map(r => (r.id !== id ? r : { ...r, last: t, end: r.end === null ? null : t, usage: usage ? addUsage(r.usage, usage) : r.usage })),
    )
    await refresh($)
    return out
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const list = await read($, records)
    const { table, note } = await read($, prices)
    const now = await read($, clockAtom)
    const rows = buildRows(list, await $.agent.list(), table)
    const total = (await $.session.usage()).cost?.usd

    const NAME = 18
    const FIXED = NAME + 10 + 5 + 7 + 6 + 6 + 2 + 6 // the seven columns and the spaces between them
    const room = e.props.bodyColumns - FIXED - 1
    const isInline = room >= 16
    const width = isInline ? room : Math.max(10, e.props.bodyColumns - 1)
    const t0 = rows[0]?.start ?? now
    const t1 = Math.max(now, t0 + 1)

    const head = [fit('agent', NAME), fit('repo', 10), fit('start', 5), fit('end', 7), 'tokens'.padStart(6), 'cost'.padStart(6), 'ch'].join(' ')

    return (
      <Box flexDirection="column">
        <Text dimColor wrap="truncate-end">{head}</Text>
        {rows.map(row => {
          const label = `${row.depth > 0 ? `${'  '.repeat(row.depth - 1)}└ ` : ''}${row.name}`
          const info = [
            fit(label, NAME),
            fit(row.repo, 10),
            fit(clock(row.start), 5),
            fit(row.end === null ? 'running' : clock(row.end), 7),
            tokens(row.tokens).padStart(6),
            dollars(row.cost).padStart(6),
            String(row.childCount).padStart(2),
          ].join(' ')
          const line = bar(row.start, row.end ?? t1, t0, t1, width)
          const color = row.end === null ? 'success' : 'inactive'
          return (
            <Box key={row.id} flexDirection={isInline ? 'row' : 'column'}>
              <Text dimColor={row.end !== null} wrap="truncate-end">{isInline ? `${info} ` : info}</Text>
              <Text color={color} wrap="truncate-end">{line}</Text>
            </Box>
          )
        })}
        <Text dimColor>{`Session total ${dollars(total)}`}</Text>
        {table === null && note !== '' && <Text dimColor>{`Costs hidden: ${note}`}</Text>}
      </Box>
    )
  })
}

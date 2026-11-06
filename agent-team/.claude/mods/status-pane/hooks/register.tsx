import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import { groupTickets } from './groups'

const PANE = 'status-pane'
const STATE = '.agent-team/state.json'
const EVERY_MS = 5000

// Change a tag when the value's fields change: it declines what an earlier
// version stored, which outlives a reload.
const view = atom({ plugin: 'status-pane', key: 'view' } as const, { mtimeMs: 0, groups: [] }, { shape: 'view-1' })
const agents = atom({ plugin: 'status-pane', key: 'agents' } as const, [], { shape: 'agents-1' })

// The state file at the root checkout, so a session in a worktree or subfolder
// reads the Chief of Staff's file. Falls back to the session's relative path.
let file = STATE

let timer: { cancel: () => void } | undefined

// One pass: the agent list, then the state file when its mtime moved.
// Nothing here throws; a bad file keeps the last good view.
async function poll($: EngineInterface) {
  try {
    const list = (await $.agent.list()).map(a => ({ id: a.id, type: a.type, description: a.description }))
    if (JSON.stringify(list) !== JSON.stringify(await read($, agents))) await update($, agents, () => list)
    const stat = await $.fs.stat(file).catch(() => undefined)
    if (!stat || stat.mtimeMs === (await read($, view)).mtimeMs) return
    const state: unknown = JSON.parse(await $.fs.read(file))
    if (typeof state !== 'object' || state === null) return
    await update($, view, () => ({ mtimeMs: stat.mtimeMs, groups: groupTickets(state) }))
  } catch {
    // empty, half-written or unreadable: keep what is drawn
  }
}

async function open($: EngineInterface) {
  try {
    const { exitCode, stdout } = await $.process.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'])
    const common = stdout.trim()
    if (exitCode === 0 && common) file = `${common.slice(0, common.lastIndexOf('/'))}/${STATE}`
  } catch {
    // not a git checkout: keep the relative path
  }
  await $.ui.open({ id: PANE, title: 'Status' })
  await poll($)
  timer ??= $.clock.every(EVERY_MS, () => void poll($))
}

export const register: Register = (on, options) => {
  const environmentId = String(options.environmentId ?? '').trim()
  const autoOpen = options.autoOpen === true

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'status-pane', description: 'Show the Chief of Staff status in a pane' })
    if (autoOpen || (await $.ui.panes()).some(p => p.id === PANE)) void open($)

    return next(e)
  })

  on('session.end', async ($, e, next) => {
    timer?.cancel()
    timer = undefined

    return next(e)
  })

  on('ui.close', { id: PANE }, async ($, e, next) => {
    timer?.cancel()
    timer = undefined

    return next(e)
  })

  on('command.run', { command: 'status-pane' }, async $ => {
    await open($)

    return { text: 'Status pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Link, Button } = $.ui.resolve(e)
    const { groups, mtimeMs } = await read($, view)
    const subs = await read($, agents)

    return (
      <Box flexDirection="column">
        {mtimeMs === 0 && <Text dimColor>No state yet.</Text>}
        {groups.map(g => (
          <Box flexDirection="column" key={g.name}>
            <Text bold>
              {g.name} ({g.count})
            </Text>
            {g.rows.map(r => (
              <Text key={r.id}>
                {'  '}
                <Text bold>{r.id}</Text>
                {r.title && ` ${r.title}`}
                {environmentId && r.childThreadId && (
                  <Link href={`t3-thread://v2/${environmentId}/${r.childThreadId}`}> thread</Link>
                )}
                <Text dimColor>
                  {' | '}
                  {r.risk} | {r.next}
                </Text>
              </Text>
            ))}
          </Box>
        ))}
        <Text bold>Subagents ({subs.length})</Text>
        {subs.map(a => (
          <Button key={a.id} onPress={() => void $.ui.view({ agentId: a.id })}>
            {a.type}: {a.description}
          </Button>
        ))}
        <Button key="back" onPress={() => void $.ui.view({})}>
          Back to main
        </Button>
      </Box>
    )
  })
}

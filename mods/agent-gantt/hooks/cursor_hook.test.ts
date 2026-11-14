import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { DatabaseSync } from 'node:sqlite'
import { fileURLToPath } from 'node:url'

const HOOK = fileURLToPath(new URL('../../../agent-team/scripts/cursor_gantt_hook.ts', import.meta.url))

test('the Cursor hook answers first, exits as Cursor needs, and writes the snapshot under the root checkout', () => {
  const tmp = mkdtempSync(join(tmpdir(), 'cursor-hook-'))
  try {
    const app = join(tmp, 'app')
    const work = join(app, '.worktrees/x')
    const plain = join(tmp, 'plain')
    mkdirSync(work, { recursive: true })
    mkdirSync(plain)
    mkdirSync(join(app, 'docs/agents'), { recursive: true })
    writeFileSync(join(app, 'docs/agents/project.md'), '# project\n')
    execFileSync('git', ['init', '-q', app])
    const run = (stdin: string) =>
      spawnSync('node', [HOOK], { input: stdin, encoding: 'utf8', env: { PATH: process.env.PATH, HOME: tmp } })
    const ev = (cwd: string, name: string, extra: object = {}) => JSON.stringify({ hook_event_name: name, conversation_id: 'c1', model: 'm', workspace_roots: [cwd], ...extra })
    const gantt = join(app, '.agent-team/gantt')
    const names = () => JSON.parse(readFileSync(join(gantt, 'c1.json'), 'utf8')).rows.map((r: any) => [r.depth, r.name])
    // name, stdin, stdout, exit code, the snapshot files and rows after (null: no gantt folder)
    const cases: [string, string, string, number, [string[], unknown[]] | null][] = [
      ['subagentStart, no app root', ev(plain, 'subagentStart', { subagent_id: 's0' }), '{"permission":"allow"}', 0, null],
      ['beforeSubmitPrompt, bad cwd', ev('/nonexistent/folder', 'beforeSubmitPrompt', { prompt: 'x' }), '{"continue":true}', 0, null],
      ['garbage stdin', 'not json', '', 1, null],
      ['prompt in a worktree folder writes the root checkout snapshot', ev(work, 'beforeSubmitPrompt', { prompt: 'Fix it' }), '{"continue":true}', 0, [['c1.json', 'cursor'], [[1, 'Fix it']]]],
      ['a subagent with its own conversation id joins its parent', ev(work, 'subagentStart', { conversation_id: 'sub1', parent_conversation_id: 'c1', subagent_id: 's1', subagent_type: 'explore', task: 'look' }), '{"permission":"allow"}', 0, [['c1.json', 'cursor'], [[1, 'Fix it'], [2, 'look']]]],
    ]
    for (const [name, stdin, stdout, code, files] of cases) {
      const r = run(stdin)
      assert.deepEqual([r.stdout, r.status], [stdout, code], name)
      if (files === null) assert.ok(!existsSync(gantt) && !existsSync(join(plain, '.agent-team')), name)
      else assert.deepEqual([readdirSync(gantt).sort(), names()], files, name)
    }

    // A stop reads c1's run from Cursor's store under HOME: 1M input on sonnet is $2.00 at prices.json. A store it cannot read keeps the rows.
    const store = join(tmp, '.cursor/projects/p/sdk-agent-store/c1')
    mkdirSync(store, { recursive: true })
    const db = new DatabaseSync(join(store, 'index.db'))
    db.exec('create table agents (agent_id, workspace_ref); create table runs (agent_id, turn_number, model, usage_json, started_at, created_at)')
    const at = new Date().toISOString()
    db.prepare('insert into runs values (?, ?, ?, ?, ?, ?)').run('c1', 1, 'claude-sonnet-4', JSON.stringify({ inputTokens: 1_000_000 }), at, at)
    db.close()
    const spend = () => {
      const snap = JSON.parse(readFileSync(join(gantt, 'c1.json'), 'utf8'))
      return [snap.rows.map((r: any) => [r.name, r.tokens]), snap.total]
    }
    const stops: [string, () => void, number, unknown][] = [
      ['stop prices the run', () => {}, 0, [[['Fix it', 1_000_000], ['look', 0]], 2]],
      ['stop with an unreadable store', () => writeFileSync(join(store, 'index.db'), 'not a database'), 0, [[['Fix it', 1_000_000], ['look', 0]], 2]],
    ]
    const storeWith = (n: number) => {
      rmSync(join(store, 'index.db'), { force: true })
      const d = new DatabaseSync(join(store, 'index.db'))
      d.exec('create table agents (agent_id, workspace_ref); create table runs (agent_id, turn_number, model, usage_json, started_at, created_at)')
      for (let t = 1; t <= n; t++) d.prepare('insert into runs values (?, ?, ?, ?, ?, ?)').run('c1', t, 'claude-sonnet-4', JSON.stringify({ inputTokens: 1_000_000 }), at, at)
      d.close()
    }
    stops.push(
      ['stop with 2 runs', () => storeWith(2), 0, [[['Fix it', 2_000_000], ['look', 0]], 4]],
      ['stop with an older, shorter read keeps the longer saved runs', () => storeWith(1), 0, [[['Fix it', 2_000_000], ['look', 0]], 4]],
    )
    for (const [name, before, code, want] of stops) {
      before()
      const r = run(ev(work, 'stop'))
      assert.deepEqual([r.stdout, r.status, spend()], ['', code, want], name)
    }

    // A TICKET HELPER conversation: its request shows at once, and a stop reads the ticket from the `result` of its run.
    const helperStore = join(tmp, '.cursor/projects/p/sdk-agent-store/h1')
    mkdirSync(helperStore, { recursive: true })
    const hdb = new DatabaseSync(join(helperStore, 'index.db'))
    hdb.exec('create table agents (agent_id, workspace_ref); create table runs (agent_id, turn_number, model, usage_json, started_at, created_at, result)')
    hdb.prepare('insert into runs values (?, ?, ?, ?, ?, ?, ?)').run('h1', 1, 'claude-sonnet-4', JSON.stringify({ inputTokens: 10 }), at, at, 'TICKET HELPER DONE\nTickets: CW-7: Fix it, https://example.test/7\nPlaced: none')
    hdb.close()
    const helper = (name: string, extra: object = {}) => run(JSON.stringify({ hook_event_name: name, conversation_id: 'h1', model: 'm', workspace_roots: [work], ...extra }))
    const filed = () => { const s = JSON.parse(readFileSync(join(gantt, 'h1.json'), 'utf8')); return [s.heading, s.request, s.ticket] }
    helper('beforeSubmitPrompt', { prompt: "TICKET HELPER. Rules.\n\nThe user's request, verbatim:\n\nFix it\n" })
    assert.deepEqual(filed(), ['TICKET HELPER', 'Fix it', null], 'request before the ticket')
    helper('stop')
    assert.deepEqual(filed(), ['TICKET HELPER', 'Fix it', 'CW-7'], 'stop reads the ticket from result')

    // Long results (3 x 600 KB, over Node's 1 MiB default output limit) must not make the store read fail and drop the usage.
    const bigStore = join(tmp, '.cursor/projects/p/sdk-agent-store/b1')
    mkdirSync(bigStore, { recursive: true })
    const bdb = new DatabaseSync(join(bigStore, 'index.db'))
    bdb.exec('create table agents (agent_id, workspace_ref); create table runs (agent_id, turn_number, model, usage_json, started_at, created_at, result)')
    for (let t = 1; t <= 3; t++) bdb.prepare('insert into runs values (?, ?, ?, ?, ?, ?, ?)').run('b1', t, 'claude-sonnet-4', JSON.stringify({ inputTokens: 1_000_000 }), at, at, 'x'.repeat(600_000))
    bdb.close()
    const big = (name: string, extra: object = {}) => run(JSON.stringify({ hook_event_name: name, conversation_id: 'b1', model: 'm', workspace_roots: [work], ...extra }))
    big('beforeSubmitPrompt', { prompt: 'Go' })
    big('stop')
    const bigSnap = JSON.parse(readFileSync(join(gantt, 'b1.json'), 'utf8'))
    assert.deepEqual([bigSnap.rows.map((r: any) => r.tokens), bigSnap.total], [[3_000_000], 6], 'stop with long results still records the usage')
  } finally {
    rmSync(tmp, { recursive: true, force: true })
  }
})

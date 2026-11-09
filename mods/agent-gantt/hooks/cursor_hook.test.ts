import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
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
  } finally {
    rmSync(tmp, { recursive: true, force: true })
  }
})

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createDetails, prDetail, specDetail } from './details.ts'
import type { DetailWant } from './details.ts'

const SHA = 'a'.repeat(40)
const PATH = 'docs/superpowers/specs/x-design.md'

test('spec sections: only the known headings, in the spec order, capped; none found gives nothing', () => {
  const spec = ['# T', '## Design', 'skipped', '## calls I made', 'a call', '```', '## Not a heading', '```', '### Sub', 'inside', '## Goal', 'x'.repeat(2500), '## Touches', '', '## Non-goals', 'none', ''].join('\n')
  const got = specDetail(spec)
  assert.deepEqual(got.map((s) => s.name), ['calls I made', 'Goal', 'Non-goals'])
  assert.equal(got[0].text, 'a call\n```\n## Not a heading\n```\n### Sub\ninside')
  assert.equal(got[1].text.slice(0, 2000), 'x'.repeat(2000))
  assert.equal(got[1].text.length, 2001)
  assert.deepEqual(specDetail('# T\n## Design\ntext\n'), [])
  assert.deepEqual(specDetail(''), [])
})

test('PR detail: body sections, Not proven lines, files cap, latest review verdicts, bad input', () => {
  const body = 'Not proven: in the summary, not the Proof\n\n## Summary\n\nDid it.\n\n## Release note\n\nA note.\n\n## Proof\n\n- ok\n\nNot proven:\n- first\n  more of first\n\n- second\n\nContext size: x\n'
  const comment = (b: string, url?: unknown, authorAssociation = 'OWNER') => ({ body: b, url, authorAssociation })
  const files = Array.from({ length: 32 }, (_, i) => ({ path: `f${i}`, additions: i, deletions: 1 }))
  const got = prDetail(JSON.stringify({
    body,
    files: [...files, { path: 7 }, null],
    comments: [comment('## Code review (pass 1)\n**Verdict:** CHANGES NEEDED', 'https://x.test/1'), comment('## Code review (pass 2)\n**Verdict:** PASS', 'javascript:alert(1)'), comment('## Security review\nVerdict: PASS', 'https://x.test/3'), comment('chatter Verdict: PASS'), comment('## Security review\nVerdict: PASS', 'https://x.test/4', 'NONE'), comment('## Code review\nVerdict: PASS', 'https://x.test/5', 'CONTRIBUTOR'), 'junk'],
  }))!
  assert.deepEqual(got.sections, [{ name: 'Summary', text: 'Did it.' }, { name: 'Release note', text: 'A note.' }, { name: 'Not proven', text: '- first\nmore of first\n- second' }])
  assert.equal(got.files!.length, 30)
  assert.deepEqual(got.files![3], { path: 'f3', add: 3, del: 1 })
  assert.equal(got.moreFiles, 2)
  assert.deepEqual(got.reviews, [{ name: 'Code review', verdict: 'PASS' }, { name: 'Security review', verdict: 'PASS', url: 'https://x.test/3' }])
  assert.deepEqual(prDetail(JSON.stringify({ body: '## Changes\n\nc' }))!.sections, [{ name: 'Summary', text: 'c' }])
  for (const bad of ['not json', '[]', 'null']) assert.equal(prDetail(bad), null, bad)
})

test('createDetails: spec read once per sha, bad inputs never reach git, PR read once a minute, failures keep the last result', async () => {
  let clock = 0
  const gitCalls: string[][] = []
  const ghCalls: string[][] = []
  let gitReply: string | Error = '## Goal\n\ng'
  let ghReply: string | Error = JSON.stringify({ body: '## Summary\n\ns' })
  const d = createDetails({
    now: () => clock,
    git: async (a) => { gitCalls.push(a); if (gitReply instanceof Error) throw gitReply; return gitReply },
    run: async (a) => { ghCalls.push(a); if (ghReply instanceof Error) throw ghReply; return ghReply },
  })
  const settle = async (wants: Parameters<typeof d.want>[0]) => { d.want(wants, { slug: 'o/r' }); await d.idle() }
  const spec = { id: 'CW-1', stage: 'awaiting-build', specPath: PATH, specSha: SHA }
  const pr = { id: 'CW-2', stage: 'awaiting-merge', pr: 5 }

  const bad = [{ ...spec, specSha: 'abc' }, { ...spec, specSha: `${SHA}\n` }, { ...spec, specPath: 'docs/../x.md' }, { ...spec, specPath: 'src/x.md' }, { ...spec, specPath: 'docs/x.md --foo' }, { ...spec, specPath: 'docs/x.md' }, { ...spec, specSha: 'abcdef' }, { ...spec, specPath: undefined }, { ...pr, pr: '5' }, { ...pr, pr: 1.5 }, { ...spec, stage: 'spec' }, { ...pr, stage: 'blocked' }, { id: 'CW-9', stage: 'merged', pr: 5 }]
  await settle(bad)
  assert.deepEqual([gitCalls, ghCalls, d.get()], [[], [], {}])

  await settle([spec, pr])
  await settle([spec, pr])
  assert.deepEqual(gitCalls, [['show', `${SHA}:${PATH}`]])
  assert.deepEqual(ghCalls, [['pr', 'view', '5', '--repo', 'o/r', '--json', 'body,files,comments,mergeCommit']])
  assert.deepEqual(Object.keys(d.get()), ['CW-1', 'CW-2'])
  assert.equal(d.get()['CW-1'].kind, 'spec')
  assert.equal(d.get()['CW-2'].kind, 'changes')

  gitReply = ghReply = new Error('boom')
  clock += 59_000
  await settle([spec, pr])
  assert.equal(ghCalls.length, 1)
  clock += 2_000
  await settle([spec, pr])
  assert.equal(ghCalls.length, 2)
  assert.equal(d.get()['CW-2'].sections[0].text, 's', 'failed read keeps the last result')
  assert.equal(gitCalls.length, 1, 'a good spec read is never repeated')

  await settle([pr])
  assert.deepEqual(Object.keys(d.get()), ['CW-2'], 'no longer wanted is dropped')
  const fresh = { ...spec, id: 'CW-3', specSha: 'b'.repeat(40) }
  await settle([fresh])
  assert.deepEqual(d.get(), {}, 'a failed first spec read shows nothing')
  clock += 61_000
  gitReply = '## Goal\n\ng2'
  await settle([fresh])
  assert.equal(d.get()['CW-3'].sections[0].text, 'g2')
})

test('the stage picks the detail: spec while it waits for build approval and builds, the PR from merge approval on and for merged rows, nothing else', async () => {
  const d = createDetails({ git: async () => '## Goal\n\ng', run: async () => JSON.stringify({ body: '## Summary\n\ns' }) })
  const base = { specPath: PATH, specSha: 'abc1234', pr: 5 }
  const cases: [DetailWant, string | undefined][] = [
    [{ id: 'a', stage: 'awaiting-build' }, 'spec'], [{ id: 'a', stage: 'build' }, 'spec'], [{ id: 'a', stage: 'build-queued' }, 'spec'],
    [{ id: 'a', stage: 'awaiting-merge' }, 'changes'], [{ id: 'a', stage: 'merge' }, 'changes'], [{ id: 'a', stage: 'merge-queued' }, 'changes'],
    [{ id: 'a', stage: 'merged', merged: true }, 'changes'], [{ id: 'a', stage: 'spec' }, undefined], [{ id: 'a', stage: 'blocked' }, undefined],
  ]
  for (const [w, kind] of cases) {
    d.want([{ ...base, ...w }], { slug: 'o/r' })
    await d.idle()
    assert.equal(d.get().a?.kind, kind, `${w.stage}${w.merged ? ' merged' : ''}`)
  }
})

test('a merged PR gives its spec link only when exactly one spec file carries the ticket id and the merge commit is a full sha', async () => {
  const spec = (name: string) => `docs/superpowers/specs/${name}.md`
  const one = [spec('2026-11-08-cw-240-x-design'), spec('2026-11-08-cw-24-y-design'), 'docs/superpowers/plans/2026-11-08-cw-240-plan.md', 'src/cw-240-.md']
  const cases: [string, string[], unknown, { path: string; sha: string } | undefined][] = [
    ['one match', one, SHA, { path: one[0], sha: SHA }],
    ['none', one.slice(1), SHA, undefined],
    ['two', [...one, spec('2026-cw-240-other')], SHA, undefined],
    ['short merge sha', one, 'abc1234', undefined],
    ['no merge commit', one, undefined, undefined],
  ]
  for (const [name, files, oid, want] of cases) {
    const d = createDetails({ git: async () => '', run: async () => JSON.stringify({ body: '', files: files.map((path) => ({ path, additions: 1, deletions: 0 })), mergeCommit: oid ? { oid } : null }) })
    d.want([{ id: 'CW-240', stage: 'merged', pr: 5, merged: true }], { slug: 'o/r' })
    await d.idle()
    assert.deepEqual(d.get()['CW-240']?.spec, want, name)
  }
})

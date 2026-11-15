import { test } from 'node:test'
import assert from 'node:assert/strict'
import { esc, localTimes, groupLabel, stageSentence, riskText, dayWords, actionFor, approveCommand, pressAction, pressMessage, todoCommand, promptLink, ganttSummary, clock, summaryLine, renderMarkdown, renderStatus, renderBacklog, bandKey, pageOf, renderGantt, barCategory, ciOwner, renderBadges, tabCounts, renderMerged, renderChief, ownerBadge, foreign, tabFromStorage, drawCharts, versionWatch } from './app.js'

const row = (o = {}) => ({ id: 'CW-1', title: 't', risk: 'low', next: 'n', stage: 'build', ...o })
const group = (rows) => [{ name: 'Building', count: rows.length, rows }]

test('status text is escaped and never becomes markup', () => {
  const html = renderStatus(group([row({ title: '<script>alert(1)</script>', next: 'a & b' })]))
  assert.match(html, /&lt;script&gt;/)
  assert.match(html, /a &amp; b/)
  assert.ok(!html.includes('<script'))
  assert.equal(esc(`"'<>&`), '&quot;&#39;&lt;&gt;&amp;')
})

test('only http(s) urls become links; a missing prUrl has no PR anchor', () => {
  const none = renderStatus(group([row()]))
  assert.ok(!none.includes('<a '))
  const bad = renderStatus(group([row({ issueUrl: 'javascript:alert(1)', prUrl: 'data:text/html,x' })]))
  assert.ok(!bad.includes('href='))
  const ok = renderStatus(group([row({ issueUrl: 'https://x.test/issues/1', prUrl: 'https://x.test/pull/2' })]))
  assert.match(ok, /href="https:\/\/x\.test\/issues\/1"/)
  assert.match(ok, /href="https:\/\/x\.test\/pull\/2"/)
})

test('threadLink becomes a copy button carrying the exact link', () => {
  const link = '<t3-thread://v2/env/th"1>'
  const html = renderStatus(group([row({ threadLink: link })]))
  assert.match(html, /<div class="head">.*<button type="button" class="copy-icon with-thread" data-copy="&lt;t3-thread:\/\/v2\/env\/th&quot;1&gt;" aria-label="Copy thread link" title="Copy thread link"><svg[^>]*><path.*?<\/svg><svg[^>]*><rect/)
  assert.ok(!html.includes('>Copy thread link<'))
  assert.ok(!renderStatus(group([row()])).includes('copy-icon'))
})

test('empty inputs show quiet lines', () => {
  assert.match(renderStatus([]), /No state yet/)
  assert.match(renderGantt([], 0), /No sessions yet/)
})

test('the header is one sentence: Your turn first in the attention colour, zero counts left out, blocked apart from waiting, the Backlog not counted', () => {
  const g = (name, count, rows = []) => ({ name, count, rows })
  const text = (groups) => renderBadges(groups).replace(/<[^>]+>/g, '')
  const blockedRow = { id: 'A', stage: 'blocked' }
  const cases = [
    [[], 'Nothing needs you'],
    [[g('Awaiting merge approval', 0), g('Building', 0)], 'Nothing needs you'],
    [[g('Awaiting merge approval', 1)], '1 needs you'],
    [[g('Awaiting merge approval', 1), g('Awaiting build approval', 1), g('Building', 3), g('Speccing', 0)], '2 need you \u00b7 3 in progress'],
    [[g('Queued to build', 2), g('Waiting to spec', 4), g('Other', 1, [blockedRow]), g('Backlog', 9)], 'Nothing needs you \u00b7 6 waiting \u00b7 1 blocked'],
    [[g('Building', 2), g('Other', 1, [blockedRow])], 'Nothing needs you \u00b7 2 in progress \u00b7 1 blocked'],
  ]
  for (const [groups, want] of cases) assert.equal(text(groups), want)
  assert.match(renderBadges([g('Awaiting merge approval', 2), g('Other', 1, [blockedRow])]), /<span class="hs-need">2 need you<\/span>.*<span class="hs-blocked">1 blocked<\/span>/)
  assert.equal(renderBadges(undefined), '')
  assert.equal(renderBadges(null), '')
})

test('tab counts sum the Your turn, In progress and Up next groups (Waiting to spec in, Backlog out), count the merged list, and give the Backlog group its own count', () => {
  const g = (name, count) => ({ name, count, rows: [] })
  const status = [g('Awaiting merge approval', 2), g('Building', 3), g('Queued to build', 1), g('Other', undefined), g('Waiting to spec', 5), g('Backlog', 9)]
  const cases = [
    [status, [1, 2, 3], { ship: 11, done: 3, backlog: 9 }],
    [[], [], { ship: 0, done: 0, backlog: 0 }],
    [undefined, undefined, { ship: 0, done: 0, backlog: 0 }],
    [[g('Backlog', 'many')], [], { ship: 0, done: 0, backlog: 0 }],
  ]
  for (const [s, m, want] of cases) assert.deepEqual(tabCounts(s, m), want)
})

test('group labels are plain words; an unknown name shows as it is; data-group keeps the api name', () => {
  const cases = [
    ['Awaiting merge approval', 'Ready to merge'],
    ['Awaiting build approval', 'Spec ready to build'],
    ['Awaiting teammate review', 'In review'],
    ['Merging', 'Merging'],
    ['Queued to merge', 'Waiting to merge'],
    ['Speccing', 'Writing the spec'],
    ['Building', 'Building'],
    ['Queued to build', 'Waiting to build'],
    ['Other', 'Blocked or waiting'],
    ['Writing tickets', 'Writing tickets'],
    ['Backlog', 'Backlog'],
    ['Mystery', 'Mystery'],
  ]
  for (const [name, want] of cases) assert.equal(groupLabel(name), want, name)
  const html = renderStatus([{ name: 'Waiting to spec', count: 1, rows: [row()] }, { name: 'Queued to merge', count: 1, rows: [row()] }])
  assert.match(html, /data-group="Waiting to spec"[^>]*><summary><h3>Waiting to spec </)
  assert.match(html, /data-group="Queued to merge"[^>]*><summary><h3>Waiting to merge </)
})

test('the stage sentence names the stage in plain words with no time; only the Other group draws it on a card', () => {
  const cases = [
    ['awaiting-merge', 'Waiting for your merge approval'],
    ['blocked', 'Blocked. Needs an answer from you'],
    ['build', 'Building'],
    ['spec-queued', 'Waiting for a spec slot'],
    ['some-new-stage', 'some new stage'],
  ]
  for (const [stage, want] of cases) assert.equal(stageSentence(stage), want, stage)
  const has = (name, r) => renderStatus([{ name, count: 1, rows: [row(r)] }]).includes('Waiting for a spec slot')
  assert.equal(has('Other', { stage: 'spec-queued' }), true)
  assert.equal(has('Queued to build', { stage: 'spec-queued' }), false, 'the section already says it')
})

test('no card or row shows since a time, in any group', () => {
  const at = new Date(2026, 10, 14, 9, 5).toISOString()
  const names = ['Awaiting merge approval', 'Awaiting build approval', 'Awaiting teammate review', 'Queued to merge', 'Speccing', 'Queued to build', 'Waiting to spec', 'Other', 'Building', 'Merging', 'Mystery']
  for (const name of names) for (const stage of ['build', 'build-queued', 'awaiting-merge', 'blocked', 'mystery']) {
    const html = renderStatus([{ name, count: 1, rows: [row({ stage, stageAt: at })] }])
    assert.doesNotMatch(html, /since \d{1,2}:\d\d [ap]m/, `${name} ${stage}`)
  }
})

test('risk shows the level word only, in its colour class; unreadable text shows as it is; empty shows nothing', () => {
  const cases = [
    ['low', { text: 'Low', level: 'low' }],
    ['Medium: touches the api', { text: 'Medium', level: 'medium' }],
    [' HIGH - migrations', { text: 'High', level: 'high' }],
    ['not rated yet', { text: 'not rated yet', level: '' }],
    ['', null],
    [undefined, null],
  ]
  for (const [input, want] of cases) assert.deepEqual(riskText(input), want, String(input))
  const meta = (risk) => renderStatus(group([row({ risk })])).match(/<span class="meta">([\s\S]*?)<\/span><\/div>/)[1]
  for (const [input, level, word] of [['low', 'low', 'Low'], ['medium: <i>x</i>', 'medium', 'Medium'], ['HIGH - migrations', 'high', 'High']]) {
    const m = meta(input)
    assert.ok(m.includes(`<span class="badge risk risk-${level}">${word}</span>`), input)
    assert.doesNotMatch(m, /risk-none|<i>|migrations|Low risk|Medium risk|High risk/)
  }
  assert.match(meta('not <b>rated</b>'), /<span class="risk-none">not &lt;b&gt;rated&lt;\/b&gt;<\/span>/)
  assert.doesNotMatch(meta(''), /risk/)
})

test('an action sits in the middle row only for a stage that needs the user and an http(s) url', () => {
  const urls = { prUrl: 'https://x.test/pull/2', specUrl: 'https://x.test/blob/s.md', issueUrl: 'https://x.test/issues/1' }
  const cases = [
    [{ stage: 'awaiting-merge' }, { label: 'Open PR', url: urls.prUrl }],
    [{ stage: 'awaiting-build' }, { label: 'Open spec', url: urls.specUrl }],
    [{ stage: 'blocked' }, null],
    [{ stage: 'build' }, null],
    [{ stage: 'awaiting-merge', prUrl: 'javascript:alert(1)' }, null],
    [{ stage: 'awaiting-build', specUrl: undefined }, null],
  ]
  for (const [r, want] of cases) assert.deepEqual(actionFor({ ...urls, ...r }), want, JSON.stringify(r))
  const html = renderStatus([{ name: 'Awaiting merge approval', count: 1, rows: [row({ ...urls, stage: 'awaiting-merge' })] }])
  assert.match(html, /<div class="actions"><a class="action" href="https:\/\/x\.test\/pull\/2"[^>]*>Open PR<\/a>/)
  assert.doesNotMatch(renderStatus(group([row(urls)])), /class="action"/)
})

test('dayWords says today, yesterday or the date', () => {
  const now = new Date(2026, 10, 14, 15, 0).getTime()
  const at = (d, h = 9) => new Date(2026, 10, d, h, 0).getTime()
  const cases = [[at(14, 0), 'today'], [at(13, 23), 'yesterday'], [at(7), '2026-11-07'], [new Date(2025, 11, 31, 12).getTime(), '2025-12-31'], [NaN, ''], [undefined, '']]
  for (const [ms, want] of cases) assert.equal(dayWords(ms, now), want, String(ms))
})

test('a card footer summarises the time and cost from the gantt; nothing without one', () => {
  const sessions = [sess({ rows: [task({ cost: 1, segments: [[T, T + 2 * MIN]] }), sub({ cost: 0.5, segments: [[T + MIN, T + 3 * MIN]] })] })]
  assert.deepEqual(ganttSummary(sessions, T + 10 * MIN), { ms: 3 * MIN, cost: 1.5 })
  assert.equal(ganttSummary([], T), null)
  const foot = (gantt) => renderStatus(group([row({ gantt })])).match(/<span class="summary"[^>]*>([^<]*)</)?.[1]
  assert.equal(foot(sessions), '3m 00s \u00b7 $1.50')
  assert.equal(foot(undefined), undefined)
  assert.equal(ganttSummary([sess({ rows: [task({ cost: null })] })], T + 10 * MIN).cost, null)
  // A running session's summary moves with the clock; the span carries the ticket id so the page can refresh it between rebuilds.
  const running = [sess({ rows: [task({ end: null, segments: [[T, null]] })] })]
  assert.notEqual(summaryLine(running, T + 5 * MIN), summaryLine(running, T + 6 * MIN))
  assert.match(renderStatus(group([row({ gantt: running })])), /<span class="summary" data-ticket="CW-1">/)
})

const T = Date.UTC(2026, 10, 7, 12, 0, 0)
const grow = (o) => ({ id: 'a', depth: 0, name: 'agent', repo: 'r', start: T, end: T + 600000, tokens: 12345, cost: null, ...o })
const sess = (o = {}) => ({ sessionId: 's', cwd: '/x', updatedAt: T, stale: false, total: 0.5, rows: [grow()], ...o })

test('gantt escapes text, formats tokens and cost in the row title, and marks running rows', () => {
  const html = renderGantt([sess({ rows: [grow({ name: '<img onerror=x>', kind: 'task' }), grow({ id: 'b', kind: 'task', end: null, tokens: 950, cost: 0.42, model: 'opus-5-5', harness: 'T3 Code' })] })], T + 60000)
  assert.ok(!html.includes('<img'))
  assert.match(html, /&lt;img onerror=x&gt;/)
  assert.match(html, /title="&lt;img onerror=x&gt;\nr · \d\d?:\d\d [ap]m to \d\d?:\d\d [ap]m · 12\.3k tokens\n\/x"/)
  assert.match(html, /r · \d\d?:\d\d [ap]m, running · 950 tokens · opus-5-5 · T3 Code/)
  assert.match(html, /\$0\.42/)
  assert.match(html, /bar cat-other running/)
})

const MIN = 60000
const task = (o) => grow({ kind: 'task', depth: 1, ...o })
const sub = (o) => grow({ kind: 'agent', depth: 2, ...o })
// What the chart shows per row: class, name, duration, cost and the bars as [left, width].
const view = (html) =>
  html
    .split('<div class="grow')
    .slice(1)
    .map((chunk) => ({
      cls: /^([^"]*)"/.exec(chunk)[1].trim(),
      name: /class="name"[^>]*>([^<]*)/.exec(chunk)[1].trim(),
      dur: /class="num dur">([^<]*)/.exec(chunk)[1],
      cost: /class="num cost">([^<]*)/.exec(chunk)[1],
      bars: [...chunk.matchAll(/left:([\d.]+)%;width:([\d.]+)%/g)].map((m) => [Number(m[1]), Number(m[2])]),
    }))

test('renderGantt draws one waterfall of active time', () => {
  const one = (rows, o) => renderGantt([sess({ rows, ...o })], T + 10 * MIN)
  const sums = (html) => view(html).map((r) => `${r.name}|${r.dur}|${r.cost}`)
  const cases = [
    {
      name: 'sessions merge into one list in start order',
      html: renderGantt(
        [
          sess({ sessionId: 'a', rows: [task({ name: 'late', start: T + 60 * MIN, segments: [[T + 60 * MIN, T + 61 * MIN]], end: T + 61 * MIN })] }),
          sess({ sessionId: 'b', rows: [task({ name: 'early', segments: [[T, T + 2 * MIN]], end: T + 2 * MIN })] }),
        ],
        T + 90 * MIN,
      ),
      want: ['early|2m 00s|–', 'late|1m 00s|–', 'Total|3m 00s|–'],
    },
    {
      name: 'an idle gap between tasks takes no width',
      html: one([
        task({ name: 'a', segments: [[T, T + MIN]], end: T + MIN }),
        task({ name: 'b', start: T + 240 * MIN, segments: [[T + 240 * MIN, T + 241 * MIN]], end: T + 241 * MIN }),
      ]),
      want: ['a|1m 00s|–', 'b|1m 00s|–', 'Total|2m 00s|–'],
      bars: [[[0, 50]], [[50, 50]], []],
    },
    {
      name: 'a task row shows only its own time; a subagent row shows its own share; cost and Total still cover all',
      html: one([
        task({ name: 't', cost: 1, segments: [[T, T + 2 * MIN]] }),
        sub({ name: 'x', start: T + MIN, cost: 0.5, segments: [[T + MIN, T + 3 * MIN]] }),
        sub({ name: 'y', start: T + MIN, cost: 0.25, segments: [[T + MIN, T + 2 * MIN]] }),
      ]),
      want: ['t|2m 00s|$1.75', 'x|2m 00s|$0.50', 'y|1m 00s|$0.25', 'Total|3m 00s|$1.75'],
      bars: [[[0, 66.67]], [[33.33, 66.67]], [[33.33, 33.33]], []],
      classes: ['', 'sub', 'sub', 'gtotal'],
    },
    {
      name: 'an unknown cost anywhere in a task gives a dash for it and for the total',
      html: one([task({ name: 't', cost: 1, segments: [[T, T + MIN]] }), sub({ name: 'x', cost: null, segments: [[T, T + MIN]] }), task({ name: 'u', start: T + MIN, cost: 2, segments: [[T + MIN, T + 2 * MIN]] })]),
      want: ['t|1m 00s|–', 'x|1m 00s|–', 'u|1m 00s|$2.00', 'Total|2m 00s|–'],
    },
    {
      name: 'an older snapshot session row is not drawn when tasks exist, and is the task when none do',
      html: one([grow({ name: 'main', kind: 'session', segments: [[T, T + MIN]] }), task({ name: 't', segments: [[T, T + MIN]] })]),
      want: ['t|1m 00s|–', 'Total|1m 00s|–'],
    },
    {
      name: 'a session row alone is a task',
      html: one([grow({ name: 'main', kind: 'session', cost: 2, segments: [[T, T + MIN]] }), sub({ name: 'x', depth: 1, start: T + MIN, cost: 1, segments: [[T + MIN, T + 2 * MIN]] })]),
      want: ['main|1m 00s|$2.00', 'x|1m 00s|$1.00', 'Total|2m 00s|$3.00'],
    },
    {
      name: 'a running span ends at now; a stale session stops at its last update',
      html: renderGantt([sess({ stale: true, updatedAt: T + MIN, rows: [task({ end: null, segments: [[T, null]] })] })], T + 90 * MIN),
      want: ['agent|1m 00s|–', 'Total|1m 00s|–'],
      classes: ['stale', 'gtotal'],
    },
  ]
  for (const c of cases) {
    assert.deepEqual(sums(c.html), c.want, c.name)
    if (c.bars) assert.deepEqual(view(c.html).map((r) => r.bars), c.bars, c.name)
    if (c.classes) assert.deepEqual(view(c.html).map((r) => r.cls), c.classes, c.name)
  }
  assert.match(one([task({ end: null, segments: [[T, null]] })]), /10m 00s/)
  const stale = renderGantt([sess({ stale: true, updatedAt: T + MIN, rows: [task({ end: null, segments: [[T, null]] })] })], T + 90 * MIN)
  assert.match(stale, /<span class="pill">stale<\/span>/)
  assert.ok(!/ running/.test(stale))
})

test('each bar has an escaped tooltip with its own range, length and the row model; a running bar says running', () => {
  const html = renderGantt([sess({ rows: [task({ name: '<b>t</b>', model: 'opus-5-5', end: null, segments: [[T, T + MIN], [T + 5 * MIN, null]] })] })], T + 8 * MIN)
  const titles = [...html.matchAll(/class="bar[^"]*"[^>]*title="([^"]*)"/g)].map((m) => m[1])
  assert.equal(titles.length, 2)
  assert.match(titles[0], /^&lt;b&gt;t&lt;\/b&gt;\nOther · \d\d?:\d\d [ap]m to \d\d?:\d\d [ap]m · 1m 00s · opus-5-5$/)
  assert.match(titles[1], /^&lt;b&gt;t&lt;\/b&gt;\nOther · \d\d?:\d\d [ap]m, running · opus-5-5$/)
})

test('the engine total shows as a note only when it differs from the row sum by a cent or more', () => {
  const html = (...totals) => renderGantt(totals.map((total, i) => sess({ sessionId: `s${i}`, total, rows: [task({ cost: 1, segments: [[T + i * MIN, T + (i + 1) * MIN]], start: T + i * MIN })] })), T + 10 * MIN)
  assert.match(html(1.5), /Claude Code reports \$1\.50 for these sessions\. Row costs use prices\.json\./)
  assert.match(html(0.5, 0.5, 0.5), /reports \$1\.50/)
  assert.doesNotMatch(html(1), /reports/)
  assert.doesNotMatch(html(1.009), /reports/)
  assert.doesNotMatch(html(1.5, null), /reports/)
})

test('a note says some rows were priced before the CW-220 fix when any drawn session lacks pricing 2', () => {
  const note = /priced before the token rate fix and keep their old costs/
  const html = (...pricing) => renderGantt(pricing.map((p, i) => sess({ sessionId: `s${i}`, pricing: p, total: null, rows: [task({ cost: 1 })] })), T + 10 * MIN)
  assert.doesNotMatch(html(2, 2), note)
  for (const p of [[2, undefined], [null]]) assert.match(html(...p), note)
})

test('a card with sessions gets a closed Agents segment that reopens when its id is in the open set', () => {
  const g = [sess()]
  const html = (open) => renderStatus(group([row({ gantt: g }), row({ id: 'CW-2' })]), open)
  assert.match(html(), /<button type="button" class="seg" data-ticket="CW-1" data-view="agents" id="seg-ticket-CW-1-agents" aria-expanded="false" aria-controls="pan-ticket-CW-1-agents">Agents <span class="pill">1<\/span>/)
  assert.match(html(new Set(['CW-1'])), /data-view="agents" id="seg-ticket-CW-1-agents" aria-expanded="true"/)
  assert.match(html(new Set(['CW-1'])), /<div class="panel" id="pan-ticket-CW-1-agents" role="region" aria-labelledby="seg-ticket-CW-1-agents"><div class="chart-body" data-ticket="CW-1">/)
  assert.equal(html().match(/class="chart-body"/g).length, 1)
  // The pill counts tasks and subagents across sessions, not sessions; an older snapshot's session row beside task rows is not one.
  const rows = [grow({ kind: 'session' }), grow({ kind: 'task', depth: 1 }), grow({ kind: 'agent', depth: 2 }), grow({ kind: 'task', depth: 1 })]
  assert.match(renderStatus(group([row({ gantt: [sess({ rows }), sess({ rows: [grow({ kind: 'task' })] })] })])), /Agents <span class="pill">4<\/span>/)
})

test('each ticket has a closed Details section that lists what is known, escaped, and reopens from the info set', () => {
  const full = row({
    id: 'CW-1',
    stage: 'spec-queued',
    risk: 'medium: <i>touches</i> the api',
    next: 'ship <b>it</b> & wait',
    issueUrl: 'https://x.test/issues/1',
    prUrl: 'https://x.test/pull/2',
    threadLink: 't3-thread://v2/env/<th>',
    gantt: [
      sess({ sessionId: 'a', updatedAt: T, rows: [task({ tokens: 1000, cost: 1 }), sub({ tokens: 500, cost: 0.5 })] }),
      sess({ sessionId: 'b', updatedAt: T + MIN, stale: true, rows: [task({ start: T + MIN, tokens: 2000, cost: 0.25 })] }),
    ],
  })
  const bare = row({ id: 'CW-2', stage: '', risk: '', next: '' })
  const section = (html, id) => html.split(`id="pan-ticket-${id}-details"`)[1].split('</li>')[0]
  const lines = (html) => [...html.matchAll(/<dt>([^<]*)<\/dt><dd>([\s\S]*?)<\/dd>/g)].map((m) => [m[1], m[2].replace(/<[^>]+>/g, '')])
  const html = renderStatus(group([full, bare]))

  const got = lines(section(html, 'CW-1'))
  assert.deepEqual(got.slice(0, 6), [
    ['Stage', 'spec queued'],
    ['Risk', 'medium: &lt;i&gt;touches&lt;/i&gt; the api'],
    ['Next', 'ship &lt;b&gt;it&lt;/b&gt; &amp; wait'],
    ['Agents', '2 sessions, 2 tasks, 1 subagent'],
    ['Tokens', '3.5k'],
    ['Cost', '$1.75'],
  ])
  assert.equal(got.length, 7)
  assert.match(got[6][1], /^\d{4}-\d\d-\d\d \d\d?:\d\d [ap]m \(stale\)$/)
  const links = section(html, 'CW-1').match(/<p class="info-links">([\s\S]*?)<\/p>/)[1]
  assert.equal(links, '<code>t3-thread://v2/env/&lt;th&gt;</code>')
  assert.ok(!section(html, 'CW-1').includes('<i>') && !section(html, 'CW-1').includes('<th>'))

  const none = section(html, 'CW-2')
  assert.ok(none.startsWith(' role="region" aria-labelledby="seg-ticket-CW-2-details" hidden><div class="info-body" data-ticket="CW-2">'))
  assert.match(none, /<p class="quiet">Nothing more known yet<\/p>/)
  assert.doesNotMatch(none, /<dt>|href=|<dd><\/dd>|info-links|info-facts/)

  const opened = renderStatus(group([full]), new Set(), new Set(), new Set(['CW-1']))
  assert.match(opened, /data-view="details" id="seg-ticket-CW-1-details" aria-expanded="true"/)
  assert.ok(!section(opened, 'CW-1').split('>')[0].includes('hidden'))
})

test('a spec or changes detail shows its sections, files and reviews as escaped text; only http urls link', () => {
  const spec = { kind: 'spec', url: 'https://x.test/blob/a.md', sections: [{ name: 'Goal', text: 'ship <b>it</b>\nline two' }, { name: 'Touches', text: 'a & b' }] }
  const changes = {
    kind: 'changes',
    url: 'javascript:alert(1)',
    sections: [{ name: 'Summary', text: '<img src=x onerror=alert(1)>' }],
    files: [{ path: 'a/<b>.ts', add: 3, del: 1 }],
    moreFiles: 4,
    reviews: [{ name: 'Code review', verdict: 'PASS', url: 'https://x.test/c' }, { name: 'Security review', verdict: 'CHANGES NEEDED', url: 'data:x' }],
  }
  const html = renderStatus(group([row({ id: 'CW-1', stage: '', risk: '', next: '', detail: spec }), row({ id: 'CW-2', stage: '', risk: '', next: '', detail: changes })]))
  const section = (id) => html.split(`id="pan-ticket-${id}-details"`)[1].split('</li>')[0]
  const a = section('CW-1')
  assert.match(a, /<header class="detail-head"><span>Spec<\/span><span class="detail-open"><a href="https:\/\/x\.test\/blob\/a\.md"/)
  assert.match(a, /<h4>Goal<\/h4><div class="detail-section"><p>ship &lt;b&gt;it&lt;\/b&gt; line two<\/p><\/div>/)
  assert.match(a, /<h4>Touches<\/h4><div class="detail-section"><p>a &amp; b<\/p><\/div>/)
  assert.doesNotMatch(a, /Nothing more known|<dl/)
  const b = section('CW-2')
  assert.match(b, /<header class="detail-head"><span>Changes<\/span><\/header>/)
  assert.match(b, /&lt;img src=x onerror=alert\(1\)&gt;/)
  assert.match(b, /<span class="badge pass"><a href="https:\/\/x\.test\/c"[^>]*>Code review PASS<\/a><\/span>/)
  assert.match(b, /<span class="badge fail">Security review CHANGES NEEDED<\/span>/)
  assert.match(b, /<h4>Files \(5\)<\/h4><div class="detail-files"><span class="path">a\/&lt;b&gt;\.ts<\/span><span class="delta"><span class="add">\+3<\/span> <span class="del">\u22121<\/span><\/span><\/div><p class="detail-more">and 4 more files<\/p>/)
  assert.doesNotMatch(b, /javascript:|data:x|<img/)
  const bare = renderStatus(group([row({ id: 'CW-3', stage: '', risk: '', next: '', detail: { kind: 'changes', sections: [], files: [{ path: 'f.ts', add: 1, del: 0 }] } })]))
  assert.match(bare, /<span class="path">f\.ts<\/span>/)
})

test('markdown renders the elements it covers', () => {
  const cases = [
    ['## Goal', '<p class="md-h">Goal</p>'],
    ['a **b** and __c__, *d* and _e_, snake_case_name', '<p>a <strong>b</strong> and <strong>c</strong>, <em>d</em> and <em>e</em>, snake_case_name</p>'],
    ['use `a <b> **c**` here', '<p>use <code>a &lt;b&gt; **c**</code> here</p>'],
    ['```js\nif (a < b) {}\n\n```\nafter', '<pre><code>if (a &lt; b) {}\n</code></pre><p>after</p>'],
    ['~~~\nopen fence', '<pre><code>open fence</code></pre>'],
    ['- one\n  more\n  - nested\n* two\n\nend', '<ul><li>one more<ul><li>nested</li></ul></li><li>two</li></ul><p>end</p>'],
    ['1. a\n2) b\n- c', '<ol><li>a</li><li>b</li></ol><ul><li>c</li></ul>'],
    ['see [the spec](https://x.test/a?b=1&c=2) now', '<p>see <a href="https://x.test/a?b=1&amp;c=2" target="_blank" rel="noopener noreferrer">the spec</a> now</p>'],
    ['line one\nline two\n\nnext', '<p>line one line two</p><p>next</p>'],
    ['> quoted\n> twice', '<blockquote>quoted twice</blockquote>'],
    ['| a | b |\n|---|---|\n| 1 | 2 |', '<pre class="md-table">| a | b |\n|---|---|\n| 1 | 2 |</pre>'],
    ['https://bare.test stays text', '<p>https://bare.test stays text</p>'],
    ['', ''],
  ]
  for (const [input, want] of cases) assert.equal(renderMarkdown(input), want, input)
})

test('hostile markdown comes out inert: no tag, no event attribute, no link that is not http(s)', () => {
  const inputs = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '[x](javascript:alert(1))',
    '[x](JaVaScRiPt:alert(1)) [y](data:text/html,<b>) [z](vbscript:x)',
    '[x](https://a.test/"onmouseover="alert(1))',
    '`<b>onerror=x</b>` **<i onclick=x>**',
    '# <script>x</script>\n- <script>y</script>\n> <svg onload=x>\n| <iframe |\n```\n<script>z</script>\n```',
  ]
  for (const input of inputs) {
    const html = renderMarkdown(input)
    assert.ok(!/<(script|img|svg|iframe|b|i)[\s>]/.test(html), html)
    assert.ok(!/<[^>]*\son\w+=/.test(html), html)
    for (const [, href] of html.matchAll(/href="([^"]*)"/g)) assert.match(href, /^https?:\/\//, html)
  }
  assert.equal(renderMarkdown('[x](javascript:alert(1))'), '<p>x)</p>')
  assert.match(renderMarkdown('[x](https://a.test/"onmouseover="alert(1))'), /href="https:\/\/a\.test\/&quot;onmouseover=&quot;alert\(1"/)
})

test('every row starts with its ticket number; Spec and PR sit in the meta line only for http(s) urls; Details repeats none of them', () => {
  const base = { id: 'CW-1', title: 't', issueUrl: 'https://x.test/issues/1', mergedAt: 0 }
  const live = (name, r) => renderStatus([{ name, count: 1, rows: [row({ ...base, ...r })] }])
  const renders = [(r) => live('Building', r), (r) => live('Queued to build', r), (r) => live('Other', { stage: 'blocked', ...r }), (r) => renderMerged([{ ...base, ...r }], 0, 10, new Set(), new Set(['CW-1'])).html]
  const [spec, pr, bad] = ['https://x.test/blob/a.md', 'https://x.test/pull/1', 'javascript:alert(1)']
  for (const [specUrl, prUrl, want] of [[spec, pr, ['Spec', 'PR']], [spec, undefined, ['Spec']], [undefined, pr, ['PR']], [bad, bad, []]]) {
    for (const [i, render] of renders.entries()) {
      const html = render({ specUrl, prUrl })
      assert.match(html, /<div class="head"><span class="id"><a href="https:\/\/x\.test\/issues\/1"[^>]*>CW-1<\/a><\/span><span class="title">t<\/span>/, i)
      assert.deepEqual([...html.match(/class="meta">([^]*?)<\/div>/)[1].matchAll(/<a [^>]*>([^<]*)<\/a>/g)].map((m) => m[1]), want, `${i} ${specUrl} ${prUrl}`)
      for (const [, href] of html.matchAll(/href="([^"]*)"/g)) assert.match(href, /^https?:\/\//, i)
      assert.doesNotMatch(html.match(/<p class="info-links">[^]*?<\/p>/)?.[0] ?? '', /<a /, i)
    }
  }
  assert.doesNotMatch(renders[0]({ title: '' }), /class="title"/)
})

test('a merged row has a closed Details section filled only when open; it shows the PR text and no links', () => {
  const e = { id: 'CW-9', title: 't', prUrl: 'https://x.test/pull/9', issueUrl: 'https://x.test/issues/9', specUrl: 'https://x.test/blob/s.md', mergedAt: 0, detail: { kind: 'changes', sections: [{ name: 'Summary', text: 'Did **it**' }] } }
  const closed = renderMerged([e], 0).html
  assert.match(closed, /data-view="details" id="seg-merged-CW-9-details" aria-expanded="false"/)
  assert.match(closed, /<div class="panel" id="pan-merged-CW-9-details"[^>]* hidden><div class="info-body" data-merged="CW-9"><\/div><\/div>/)
  const open = renderMerged([e], 0, 10, new Set(), new Set(['CW-9'])).html
  assert.match(open, /data-view="details" id="seg-merged-CW-9-details" aria-expanded="true"/)
  assert.doesNotMatch(open, /id="pan-merged-CW-9-details"[^>]* hidden>/)
  assert.doesNotMatch(open, /info-links/)
  assert.match(open, /<p>Did <strong>it<\/strong><\/p>/)
})

test('status sections draw open unless collapsed; a closed one keeps its heading and count; the name is escaped', () => {
  const groups = [
    { name: 'Building', count: 1, rows: [row()] },
    { name: 'Queued <b>', count: 2, rows: [row({ id: 'CW-2' })] },
  ]
  const section = (html, name) => html.match(new RegExp(`<details class="group" data-group="${name}"[^>]*>`))[0]
  const all = renderStatus(groups)
  assert.ok(section(all, 'Building').endsWith(' open>') && section(all, 'Queued &lt;b&gt;').endsWith(' open>'))
  const some = renderStatus(groups, new Set(), new Set(['Queued <b>']))
  assert.ok(section(some, 'Building').endsWith(' open>'))
  assert.ok(!section(some, 'Queued &lt;b&gt;').includes('open'))
  assert.match(some, /<summary><h3>Queued &lt;b&gt; <span class="pill">2<\/span><\/h3><\/summary>/)
  assert.ok(!some.includes('<b>'))
})

test('merged list pages by ten, clamps the page, disables the pager ends and escapes text', () => {
  const list = Array.from({ length: 25 }, (_, i) => ({ id: `CW-${i + 1}`, title: `t${i + 1}`, prUrl: `https://x.test/pull/${i + 1}`, mergedAt: new Date(2026, 0, 2, 3, 4).getTime() }))
  const cards = (html) => (html.match(/<li class="ticket compact">/g) ?? []).length
  const cases = [
    [0, 0, 10, 'Page 1 of 3', /data-page="-1" disabled/],
    [1, 1, 10, 'Page 2 of 3', /data-page="0">Newer[\s\S]*data-page="2">Older/],
    [2, 2, 5, 'Page 3 of 3', /data-page="3" disabled/],
    [99, 2, 5, 'Page 3 of 3', /disabled/],
    [-4, 0, 10, 'Page 1 of 3', /disabled/],
  ]
  for (const [page, want, count, label, rx] of cases) {
    const r = renderMerged(list, page)
    assert.equal(r.page, want, `page ${page}`)
    assert.equal(cards(r.html), count, `page ${page}`)
    assert.ok(r.html.includes(label), `page ${page}`)
    assert.match(r.html, rx, `page ${page}`)
  }
  const one = renderMerged(list.slice(0, 3), 0)
  assert.ok(!one.html.includes('pager'))
  assert.match(one.html, /merged 2026-01-02 3:04 am/)
  assert.match(renderMerged([], 5).html, /Nothing merged yet/)
  const bad = renderMerged([{ id: '<b>', title: '<script>x</script>', prUrl: 'javascript:1', issueUrl: 'javascript:2', mergedAt: 0 }], 0).html
  assert.ok(!bad.includes('<script') && !bad.includes('<b>') && !bad.includes('href='))
})

test('merged row shows spend only when the entry has it', () => {
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const html = (spend) => renderMerged([{ ...e, ...(spend ? { spend } : {}) }], 0).html
  assert.doesNotMatch(html(), /\$|tokens/)
  assert.match(html({ cost: 0.4166, tokens: 955168 }), / \u00b7 \$0\.42 \u00b7 955\.2k tokens/)
  const none = html({ cost: null, tokens: 12 })
  assert.match(none, /12 tokens/)
  assert.doesNotMatch(none, /\$|–/)
})

test('groups sort into bands, keep api order inside a band', () => {
  const g = (name, rows = [row({ id: `${name}-1`, stage: 'build' })]) => ({ name, count: rows.length, rows })
  const bandsOf = (html) => [...html.matchAll(/<h2>([^<]+)<\/h2>|<h3>([^<]+?) <span/g)].map((m) => m[1] ?? m[2])
  const names = [g('Building'), g('Mystery'), g('Awaiting build approval'), g('Queued to build'), g('Awaiting merge approval'), g('Speccing')]
  assert.deepEqual(bandsOf(renderStatus(names)), ['Your turn', 'Spec ready to build', 'Ready to merge', 'In progress', 'Building', 'Mystery', 'Writing the spec', 'Up next', 'Waiting to build'])
  assert.deepEqual(bandsOf(renderStatus([g('Merging')])), ['In progress', 'Merging'])
  const other = renderStatus([g('Waiting to spec', [row({ id: 'B', stage: 'spec-queued' })]), g('Other', [row({ id: 'A', stage: 'blocked', next: 'Waiting on Dana' })]), g('Building')])
  assert.match(other, /Waiting for a spec slot[\s\S]*class="ticket blocked"[\s\S]*Blocked\. Needs an answer from you/)
  assert.equal((other.match(/class="ticket blocked"/g) ?? []).length, 1, 'only the blocked row has the red edge')
  const queued = renderStatus([g('Queued to build', [row({ stage: 'build-queued', stageAt: new Date(2026, 10, 14, 9, 5).toISOString(), risk: 'low' })])])
  assert.match(queued, /<span class="meta"><span class="badge risk risk-low">Low<\/span><\/span>/)
  assert.match(renderStatus([g('Awaiting merge approval')]), /class="group needs-merge"/)
})

test('a running ticket helper is a placeholder card; a Todo row shows only under Waiting to spec; the Backlog is not on the Ship loop tab and there is no Not started band', () => {
  const hostile = '<img src=x onerror=1>'
  const link = '<t3-thread://v2/env/th1>'
  const mine = sess({ rows: [task({ segments: [[T, T + MIN]] })] })
  const writing = { name: 'Writing tickets', count: 1, rows: [row({ id: `helper:${hostile}`, title: hostile, helper: true, risk: '', next: '', stage: '', threadLink: link, gantt: [mine] })] }
  const spec = { name: 'Waiting to spec', count: 2, rows: [row({ id: 'CW-6', stage: 'spec-queued' }), row({ id: 'CW-7', title: hostile, issueUrl: 'https://x.test/issues/7', risk: '', next: '', stage: '' })] }
  const backlog = { name: 'Backlog', count: 1, rows: [row({ id: 'CW-8', title: 'later', risk: '', next: '', stage: '', gantt: [mine] })] }
  const html = renderStatus([...group([row()]), writing, { name: 'Queued to build', count: 1, rows: [row({ id: 'CW-9' })] }, spec, backlog])
  const part = (name) => html.split(`<details class="band band-${name}"`)[1]?.split('<details class="band ')[0] ?? ''
  const card = part('progress')
  assert.match(card, /<span class="id">Ticket helper<\/span><span class="title">&lt;img src=x onerror=1&gt;<\/span>/)
  assert.match(card, /data-copy="&lt;t3-thread:\/\/v2\/env\/th1&gt;"/)
  assert.match(card, /class="seg" data-ticket="helper:&lt;img[^"]*" data-view="agents"/)
  const placeholder = card.split('<li class="ticket">').find((li) => li.includes('Ticket helper')).split('</li>')[0]
  assert.ok(!/<a |class="info-body"/.test(placeholder), 'no link or Details panel on the placeholder')
  assert.match(placeholder, /data-view="details"[^>]* disabled title="No ticket yet"/)
  assert.ok(card.indexOf('Building') < card.indexOf('Writing tickets'), 'api order kept')
  assert.ok(!html.includes('<img'))
  const next = part('queued')
  assert.ok(next.indexOf('data-group="Queued to build"') < next.indexOf('data-group="Waiting to spec"'), 'Waiting to spec follows Queued to build')
  const waiting = next.split('data-group="Waiting to spec"')[1]
  assert.equal([...waiting.matchAll(/<li class="ticket compact">/g)].length, 2, 'spec-queued and Todo rows are compact cards')
  assert.ok(!waiting.includes('<li class="ticket">') && !/risk|since/.test(waiting.split('<li class="ticket compact">')[2]))
  assert.match(waiting, /href="https:\/\/x\.test\/issues\/7"/)
  assert.deepEqual([html.includes('band-not-started'), html.includes('Not started'), html.includes('data-group="Backlog"'), html.includes('CW-8')], [false, false, false, false])
  assert.equal(renderStatus([spec]).includes('No state yet'), false)
  assert.equal(renderStatus([backlog]), '<p class="quiet">No state yet</p>')
})

test('merged row with sessions has a closed Agents segment that stays open when its id is in the open set; one without has a disabled one', () => {
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const html = (gantt, open) => renderMerged([{ ...e, ...(gantt ? { gantt } : {}) }, { ...e, id: 'CW-2' }], 0, 10, open).html
  assert.match(html([sess(), sess()]), /<button type="button" class="seg" data-merged="CW-1" data-view="agents" id="seg-merged-CW-1-agents" aria-expanded="false" aria-controls="pan-merged-CW-1-agents">Agents <span class="pill">2<\/span><\/button>/)
  assert.match(html([sess()], new Set(['CW-1'])), /data-merged="CW-1" data-view="agents" id="seg-merged-CW-1-agents" aria-expanded="true"/)
  assert.equal(html([sess()]).match(/class="chart-body"/g).length, 1)
  for (const none of [html([]), html()]) {
    assert.match(none, /data-merged="CW-1" data-view="agents" id="seg-merged-CW-1-agents" aria-expanded="false" disabled title="No agent sessions recorded">Agents <span class="pill">0<\/span>/)
    assert.doesNotMatch(none, /class="chart-body"|pan-merged-CW-1-agents/)
  }
})

test('the Agents pill counts every task and subagent on every row type; an empty gantt is a disabled Agents 0', () => {
  const g = [sess({ rows: [task({}), sub({}), sub({}), task({}), grow({ kind: 'agent', depth: 2 })] })]
  const pm = (gantt) => renderChief({ chief: {}, pm: [{ sessionId: 'M', role: 'ranking', state: 'idle', gantt }] }, 0, new Set()).html
  const cases = [
    ['card', (gantt) => renderStatus(group([row({ gantt })]))],
    ['merged', (gantt) => renderMerged([{ id: 'M', title: 't', mergedAt: 0, gantt }], 0, 10).html],
    ['project manager', pm],
  ]
  for (const [name, render] of cases) {
    assert.match(render(g), /Agents <span class="pill">5<\/span>/, name)
    assert.match(render([]), /disabled[^>]*>Agents <span class="pill">0<\/span>/, name)
  }
})

test('owner avatar on every card type; Agents is left out only for a foreign owner with no sessions; Details stays', () => {
  const kinds = {
    status: (o, viewer) => renderStatus(group([row(o)]), new Set(), new Set(), new Set(), '', viewer),
    backlog: (o, viewer) => renderBacklog([{ name: 'Backlog', count: 1, rows: [row(o)] }], new Set(), 0, new Set(), new Set(), '', viewer),
    done: (o, viewer) => renderMerged([{ ...o, mergedAt: 0 }], 0, 10, new Set(), new Set(), viewer).html,
  }
  const owners = [['viewer', 'david'], ['viewer in another case', 'DAVID'], ['other', 'noah'], ['none', undefined]]
  for (const [kind, render] of Object.entries(kinds)) {
    for (const [who, owner] of owners) {
      for (const viewer of ['david', null]) {
        for (const gantt of [[], [sess({ rows: [task({})] })]]) {
          const html = render({ ...row(), ...(owner ? { owner } : {}), gantt }, viewer)
          const name = `${kind} ${who} viewer=${viewer} tasks=${gantt.length}`
          assert.equal(html.includes('class="owner"'), owner !== undefined, `${name} avatar`)
          assert.equal(html.includes('data-view="agents"'), !(foreign(owner, viewer) && gantt.length === 0), `${name} agents`)
          assert.ok(html.includes('data-view="details"'), `${name} details`)
        }
      }
    }
  }
  assert.equal(ownerBadge(undefined), '')
  const bad = ownerBadge('<b>"x')
  assert.ok(!bad.includes('<b>') && bad.includes('&lt;b&gt;') && bad.includes('<span class="initial">&lt;</span>') && /src="https:\/\/avatars\.githubusercontent\.com\/%3Cb%3E%22x\?s=40"/.test(bad))
})

test('drawCharts writes a chart body only when its html changed; a body with no entry is never written', () => {
  const finished = [sess({ rows: [task({ end: T + MIN, segments: [[T, T + MIN]] })] })]
  const running = [sess({ rows: [task({ end: null, segments: [[T, null]] })] })]
  const cases = [
    { name: 'same data and now, ticket and merged', gantt: finished, nows: [T + 5 * MIN, T + 5 * MIN], want: [1, 1] },
    { name: 'finished task, later now', gantt: finished, nows: [T + 5 * MIN, T + 6 * MIN], want: [1, 1] },
    { name: 'running task, later now', gantt: running, nows: [T + 5 * MIN, T + 6 * MIN], want: [2, 2] },
    { name: 'id missing from the data', gantt: finished, nows: [T + 5 * MIN], want: [0, 0], ids: ['X', 'Y'] },
  ]
  for (const { name, gantt, nows, want, ids = ['CW-1', 'CW-2'] } of cases) {
    const bodies = { '.chart-body[data-ticket]': { dataset: { ticket: ids[0] } }, '.chart-body[data-merged]': { dataset: { merged: ids[1] } } }
    const root = { querySelectorAll: (sel) => (bodies[sel] ? [bodies[sel]] : []) }
    const data = { status: [{ rows: [{ id: 'CW-1', gantt }] }], merged: [{ id: 'CW-2', gantt }] }
    const calls = new Map(Object.values(bodies).map((b) => [b, 0]))
    for (const now of nows) drawCharts(root, data, now, (b) => calls.set(b, calls.get(b) + 1))
    assert.deepEqual([...calls.values()], want, name)
  }
})

test('versionWatch asks for a reload only when a later version differs from the first', () => {
  const cases = [
    [[undefined, 'a', 'a', 'b'], [false, false, false, true]],
    [['a', 'a', 'a'], [false, false, false]],
    [[null, 'a'], [false, false]],
    [['a', null, '', 7, 'a'], [false, false, false, false, false]],
  ]
  for (const [input, want] of cases) {
    const seen = versionWatch()
    assert.deepEqual(input.map(seen), want, JSON.stringify(input))
  }
})

test('every row in every section is a li.ticket card in ul.cards; no row or rows class is left', () => {
  const g = (name, o = {}) => ({ name, count: 1, rows: [row({ id: `${name}-1`, stage: 'build', ...o })] })
  const merged = [{ id: 'CW-9', title: 'm', mergedAt: T }]
  const pm = { chief: { state: 'idle' }, pm: [{ sessionId: 's1', role: 'ranking', state: 'finished', gantt: [] }] }
  const cases = [
    ['Your turn', renderStatus([g('Awaiting merge approval')]), 'ticket attn'],
    ['In progress', renderStatus([g('Building')]), 'ticket'],
    ['Up next', renderStatus([g('Queued to build')]), 'ticket compact'],
    ['blocked Up next', renderStatus([g('Other', { stage: 'blocked' })]), 'ticket blocked'],
    ['Waiting to spec', renderStatus([g('Waiting to spec', { stage: '' })]), 'ticket compact'],
    ['Backlog tab', renderBacklog([g('Backlog', { stage: '' })]), 'ticket compact'],
    ['Done', renderMerged(merged, 0).html, 'ticket compact'],
    ['project manager', renderChief(pm, 0).html, 'ticket compact'],
  ]
  for (const [name, html, cls] of cases) {
    assert.match(html, new RegExp(`<ul class="cards"><li class="${cls}">`), name)
    assert.ok(!/class="rows?"|<li class="row/.test(html), `${name}: no row class`)
  }
})

test('the Chief of Staff tab renders the card, the empty list, escaped role rows and a pager; an unknown saved tab opens Ship loop', () => {
  const empty = renderChief({ chief: { state: 'idle' }, pm: [] }).html
  assert.match(empty, /No Chief of Staff session in the last 24 hours\./)
  assert.match(empty, /No project manager threads yet\./)
  assert.ok(!empty.includes('Ticket helper'))
  assert.ok(!empty.includes('data-chief'))
  const link = '<t3-thread://v2/env/th1>'
  const hostile = '<img src=x onerror=1>'
  const pm = (i, o = {}) => ({ sessionId: `s${i}`, role: 'ranking', state: 'finished', gantt: [sess({ sessionId: `s${i}`, rows: [task({ segments: [[T, T + MIN]] })] })], ...o })
  const api = { chief: { state: 'running', threadLink: link, gantt: [sess()] }, pm: [pm(1, { role: hostile, state: hostile, sessionId: hostile, threadLink: link }), pm(2, { role: 'hygiene' }), ...Array.from({ length: 10 }, (_, i) => pm(i + 3))] }
  const first = renderChief(api, 0, new Set([hostile]))
  assert.match(first.html, /state-running/)
  assert.match(first.html, /data-chief/)
  assert.match(first.html, /data-copy="&lt;t3-thread:\/\/v2\/env\/th1&gt;"/)
  assert.match(first.html, /Hygiene/)
  assert.ok(!first.html.includes('<img'))
  assert.match(first.html, /data-pm="&lt;img[^"]*" data-view="agents" id="[^"]*" aria-expanded="true"/)
  assert.equal([...first.html.matchAll(/<li class="ticket compact">/g)].length, 10)
  assert.match(first.html, /Page 1 of 2/)
  const last = renderChief(api, 99)
  assert.equal(last.page, 1)
  assert.equal([...last.html.matchAll(/<li class="ticket compact">/g)].length, 2)
  assert.deepEqual(['cos', 'done', 'backlog', 'ship', null, undefined, 'x', 'COS', 'DONE', 5].map(tabFromStorage), ['cos', 'done', 'backlog', 'ship', 'ship', 'ship', 'ship', 'ship', 'ship', 'ship'])
  const bodies = { 'data-chief': [{ dataset: {} }], 'data-pm': [{ dataset: { pm: 's2' } }, { dataset: { pm: 'gone' } }] }
  const drawn = []
  drawCharts({ querySelectorAll: (sel) => bodies[/data-[a-z]+/.exec(sel)?.[0]] ?? [] }, { status: [], merged: [], ...api }, T, (b, html) => drawn.push([b.dataset.pm ?? 'chief', html.includes('class="gantt"')]))
  assert.deepEqual(drawn, [['s2', true], ['chief', true]])
})

test('a group with an http(s) moreUrl ends with an escaped Full backlog link inside its section; any other moreUrl draws none', () => {
  const rows = [row({ id: 'CW-8', title: 'later', risk: '', next: '', stage: '' })]
  const html = (moreUrl) => renderBacklog([{ name: 'Backlog', count: 9, rows, moreUrl }])
  const ok = html('https://x.test/o/r/issues?a=1&b="2"')
  assert.match(ok, /<\/ul><p class="more"><a href="https:\/\/x\.test\/o\/r\/issues\?a=1&amp;b=&quot;2&quot;" target="_blank" rel="noopener noreferrer">Full backlog<\/a><\/p><\/details>/)
  for (const bad of ['javascript:alert(1)', '//x.test/issues', undefined]) assert.ok(!html(bad).includes('Full backlog'), String(bad))
})

test('ciOwner gives each CI span to the task that last finished a working span before it', () => {
  const item = (...spans) => ({ spans: spans.map(([a, b, open = false]) => [T + a * MIN, T + b * MIN, open]), s: {} })
  const A = item([0, 2])
  const B = item([5, 9, true])
  const C = item([3, 4])
  const cases = [
    ['the gap after A ends, before B starts', [A, item([6, 8])], [3, 4], 0],
    ['starts while B runs: B has no finished span, A owns it', [A, B], [6, 8], 0],
    ['still running: the task that finished last before it', [A, C], [7, null], 1],
    ['before any task finished: the earliest task', [A, C], [1, 2], 0],
    ['a tie goes to the earlier task', [item([0, 2]), item([1, 2])], [3, 4], 0],
    ['a later finish beats an earlier one', [item([0, 4]), item([1, 2])], [5, 6], 0],
  ]
  for (const [name, items, [a, b], want] of cases) {
    assert.deepEqual(ciOwner(items, [[T + a * MIN, b === null ? T + 20 * MIN : T + b * MIN, b === null]]), [want], name)
  }
})

test('renderGantt draws each CI wait bar on its task row and leaves durations, costs and the Total alone', () => {
  const now = T + 30 * MIN
  const sessions = [
    sess({
      rows: [
        task({ name: 'first', cost: 1, segments: [[T, T + 2 * MIN]], end: T + 2 * MIN }),
        task({ name: 'second', cost: 2, start: T + 10 * MIN, segments: [[T + 10 * MIN, T + 12 * MIN]], end: T + 12 * MIN }),
      ],
    }),
  ]
  // Both spans start after "first" ended and before "second" started; the second overlaps the first and is open.
  const ci = [[T + 3 * MIN, T + 6 * MIN], [T + 5 * MIN, null]]
  const withCi = renderGantt(sessions, now, ci)
  const rows = view(withCi)
  assert.deepEqual(rows.map((r) => r.name), ['first', 'second', 'Total'])
  assert.deepEqual(rows.map((r) => [r.dur, r.cost]), view(renderGantt(sessions, now)).map((r) => [r.dur, r.cost]))
  // Axis: 2m of first + 27m of merged CI (3m to 30m, second's work lies inside it) = 29m. The CI bar sits on first's track only, before its work bar so work stays on top.
  assert.deepEqual(rows[0].bars, [[6.9, 93.1], [0, 6.9]])
  assert.deepEqual(rows[1].bars, [[31.03, 6.9]])
  assert.equal([...withCi.matchAll(/class="bar cat-ci"/g)].length, 1)
  assert.ok(!withCi.includes(' running"'))
  assert.ok(!withCi.includes('CI wait</span>'))
  assert.match(withCi, /title="CI wait\n\d\d?:\d\d [ap]m, running · 27m 00s"/)
  assert.equal(renderGantt(sessions, now, []), renderGantt(sessions, now), 'no CI spans, same chart as before')
})

test('barCategory reads the start of a row name and falls back to other', () => {
  const cases = {
    planning: ['Spec CW-385: Stamp approval-comment times', 'Ticket helper CW-345', 'Backlog ranking', 'approve 370', 'take over', 'CHIEF OF STAFF NOTICE: queue moved', 'Spec CW-1: Review the code'],
    building: ['Build CW-310: Merge the docs', 'CW-385 build', 'build', 'Implement CW-306 plan', 'Build CW-339 task 1'],
    review: ['Code review PR 397', 'Small-diff code and security review', 'Re-review fix commit', 'Fix CW-339 review findings', 'CW-339 changes on PR #352'],
    docs: ['Docs check PR 397', 'Compact added agent text'],
    merge: ['Merge CW-310: Build it', 'merge PR #389', 'CW-389 merge PR #389'],
    other: ['how many tokens', 'Delegated task node:delegated-task:command%3Amcp%3A602cbc46-', 'outside a task', 'main', 'task', undefined, null, 7],
  }
  for (const [want, names] of Object.entries(cases)) for (const name of names) assert.equal(barCategory(name), want, String(name))
})

test('renderGantt colors each bar by its row name, keeps the category on a running bar and lists the drawn categories in order', () => {
  const rows = [
    task({ name: 'Build CW-1: x', segments: [[T, T + MIN]], end: T + MIN }),
    sub({ name: 'Code review PR 1', segments: [[T + MIN, T + 2 * MIN]], end: T + 2 * MIN }),
    task({ name: 'Spec CW-2: y', start: T + 3 * MIN, end: null, segments: [[T + 3 * MIN, null]] }),
  ]
  const html = renderGantt([sess({ rows })], T + 5 * MIN, [[T + 2 * MIN, T + 3 * MIN]])
  const bars = [...html.matchAll(/class="bar ([^"]*)"/g)].map((m) => m[1])
  assert.deepEqual(bars, ['cat-ci', 'cat-building', 'cat-review', 'cat-planning running'])
  const legend = [...html.matchAll(/<li><span class="swatch cat-(\w+)"><\/span>([^<]*)<\/li>/g)].map((m) => m[1])
  assert.deepEqual(legend, ['planning', 'building', 'review', 'ci'])
  assert.match(html, /class="grow gtotal"[\s\S]*\n<ul class="legend" aria-label="Bar colors">(<li>[^]*?<\/li>)+<\/ul>\n<\/div>$/)
  assert.doesNotMatch(html, /^<div class="gantt">\n<ul class="legend"/)
  assert.equal([...renderGantt([sess({ rows: [rows[0]] })], T + 5 * MIN).matchAll(/class="swatch/g)].length, 1)
  assert.doesNotMatch(renderGantt([], T), /legend/)
})

test('every row type draws the same switch first in its foot; one panel is open at most and a row with no tasks has a disabled Agents', () => {
  const g = [sess()]
  const status = (name, r) => (open, info) => renderStatus([{ name, count: 1, rows: [r] }], open, new Set(), info)
  const merged = (gantt) => (open, info) => renderMerged([{ id: 'M', title: 't', mergedAt: 0, ...(gantt ? { gantt } : {}) }], 0, 10, open, info).html
  const pm = (open) => renderChief({ chief: {}, pm: [{ sessionId: 'M', role: 'ranking', state: 'idle', gantt: g }] }, 0, open).html
  const both = ['agents', 'details']
  const cases = [
    ['live card', status('Building', row({ id: 'M', gantt: g })), both, both],
    ['card with no tasks', status('Building', row({ id: 'M' })), both, ['details']],
    ['flat row', status('Queued to build', row({ id: 'M', gantt: g })), both, both],
    ['blocked row', status('Other', row({ id: 'M', stage: 'blocked', gantt: g })), both, both],
    ['helper', status('Building', row({ id: 'M', helper: true, gantt: g })), both, ['agents']],
    ['merged', merged(g), both, both],
    ['merged with no tasks', merged(), both, ['details']],
    ['project manager', pm, ['agents'], ['agents']],
  ]
  const [none, id] = [new Set(), new Set(['M'])]
  const opened = (html) => [...html.matchAll(/data-view="(\w+)" id="[^"]*" aria-expanded="true"/g)].map((m) => m[1])
  for (const [name, render, views, can] of cases) {
    const closed = render(none, none)
    assert.match(closed, /<div class="foot"><div class="switch" role="group" aria-label="M panels">/, name)
    assert.deepEqual([...closed.matchAll(/class="seg" data-\w+="M" data-view="(\w+)"/g)].map((m) => m[1]), views, name)
    assert.equal(/id="pan-[a-z]+-M-agents"/.test(closed), can.includes('agents'), name)
    for (const [v, html] of [['agents', render(id, none)], ['details', render(none, id)], ['agents', render(id, id)]]) {
      assert.deepEqual(opened(html), can.includes(v) ? [v] : [], `${name} ${v}`)
      assert.equal(html.match(/<div class="panel"[^>]*>/g)?.filter((t) => !t.includes(' hidden')).length ?? 0, can.includes(v) ? 1 : 0, `${name} ${v} panels`)
    }
  }
})

test('a stale Todo list says how old it is and greys only its Todo rows; a stale Backlog greys its group; a fresh one or one with no readAt draws nothing', () => {
  const now = Date.now()
  const late = { readAt: now - (3 * 60 + 16) * 60_000 - 5_000, stale: true }
  const todo = (o = {}) => row({ id: 'CW-8', risk: '', next: '', stage: '', ...o })
  const spec = (g, rowStale) => renderStatus([{ name: 'Waiting to spec', count: 2, rows: [row({ id: 'CW-6', stage: 'spec-queued' }), todo(rowStale ? { stale: true } : {})], ...g }])
  const stale = spec(late, true)
  assert.match(stale, /<\/summary><p class="read-age">Read from the tracker 3h 16m ago<\/p><ul/)
  assert.deepEqual([...stale.matchAll(/<li class="ticket compact( stale)?">/g)].map((m) => m[1] ?? ''), ['', ' stale'], 'only the Todo row is grey')
  assert.ok(!stale.includes('group stale'), 'the group is not grey')
  for (const g of [{ readAt: now - 600_000 }, {}]) assert.ok(!/read-age|stale/.test(spec(g, false)), JSON.stringify(g))
  const backlog = (g) => renderBacklog([{ name: 'Backlog', count: 1, rows: [todo()], ...g }])
  assert.match(backlog(late), /<details class="group stale"[^>]*>.*<\/summary><p class="read-age">Read from the tracker 3h 16m ago<\/p><ul/)
  for (const g of [{ readAt: now - 600_000 }, {}]) assert.ok(!/read-age|group stale/.test(backlog(g)), JSON.stringify(g))
})

test('clock: local 12-hour time with am/pm', () => {
  const cases = [
    [0, 0, '12:00 am'],
    [0, 30, '12:30 am'],
    [9, 5, '9:05 am'],
    [12, 0, '12:00 pm'],
    [23, 59, '11:59 pm'],
  ]
  for (const [h, m, want] of cases) assert.equal(clock(new Date(2026, 0, 2, h, m).getTime()), want)
})

test('renderBacklog draws the Backlog group 10 rows of its page, clamps the page, and shows the pager only past one page; no group says so', () => {
  const ids = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => `CW-${from + i}`)
  // [rows, page, drawn ids, "Page X of Y" or null, disabled button, data-backlog-page of Previous and Next]
  const cases = [
    [0, 0, [], null, null, []],
    [10, 3, ids(1, 10), null, null, []],
    [11, -1, ids(1, 10), 'Page 1 of 2', 'Previous', [-1, 1]],
    [11, 1, ids(11, 11), 'Page 2 of 2', 'Next', [0, 2]],
    [11, 9, ids(11, 11), 'Page 2 of 2', 'Next', [0, 2]],
    [25, 1, ids(11, 20), 'Page 2 of 3', null, [0, 2]],
    [25, 2, ids(21, 25), 'Page 3 of 3', 'Next', [1, 3]],
    [25, NaN, ids(1, 10), 'Page 1 of 3', 'Previous', [-1, 1]],
  ]
  for (const [n, page, drawn, text, disabled, targets] of cases) {
    const html = renderBacklog([{ name: 'Backlog', count: n, rows: ids(1, n).map((id) => row({ id })), moreUrl: 'https://x.test/b' }], new Set(), page)
    const label = `${n} rows, page ${page}`
    assert.deepEqual([...html.matchAll(/<span class="id">([^<]*)</g)].map((m) => m[1]), drawn, label)
    assert.equal(html.match(/<nav class="pager">[\s\S]*?<span>([^<]*)<\/span>/)?.[1] ?? null, text, label)
    assert.deepEqual([...html.matchAll(/<button type="button" data-backlog-page="-?\d+" disabled>([^<]*)</g)].map((m) => m[1]), disabled ? [disabled] : [], label)
    assert.deepEqual([...html.matchAll(/data-backlog-page="(-?\d+)"/g)].map((m) => Number(m[1])), targets, label)
    assert.match(html, new RegExp(`<span class="pill">${n}</span>`), label)
    // The Full backlog link stays, after the pager when there is one.
    assert.match(html, text ? /<\/nav><p class="more"><a href="https:\/\/x\.test\/b"/ : /<\/ul><p class="more"><a href="https:\/\/x\.test\/b"/, label)
  }
  assert.match(renderBacklog([{ name: 'Building', count: 1, rows: [row()] }]), /^<p class="quiet">Nothing in the Backlog<\/p>$/)
  assert.match(renderBacklog(undefined), /Nothing in the Backlog/)
  assert.match(renderBacklog([{ name: 'Backlog', count: 1, rows: [row()] }], new Set(['Backlog'])), /data-group="Backlog">/, 'collapsed')
  assert.deepEqual([pageOf(0, 5, 10), pageOf(25, 2.9, 10), pageOf(25, 'x', 10)], [{ at: 0, pages: 1 }, { at: 2, pages: 3 }, { at: 0, pages: 3 }])
})

test('top-level bands draw open unless their band key is collapsed, and leave their sub-sections alone', () => {
  const groups = [{ name: 'Awaiting merge approval', count: 1, rows: [row()] }, { name: 'Building', count: 1, rows: [row({ id: 'CW-2' })] }]
  const head = (html, slug) => html.match(new RegExp(`<details class="band band-${slug}"[^>]*>`))[0]
  const api = { chief: {}, pm: [] }
  const cases = [
    ['status, none collapsed', () => renderStatus(groups), 'needs', true],
    ['status, Your turn collapsed', () => renderStatus(groups, new Set(), new Set([bandKey('needs')])), 'needs', false],
    ['status, other band stays open', () => renderStatus(groups, new Set(), new Set([bandKey('needs')])), 'progress', true],
    ['status, a group name collapses no band', () => renderStatus(groups, new Set(), new Set(['Building'])), 'progress', true],
    ['chief, none collapsed', () => renderChief(api).html, 'pm', true],
    ['chief, pm collapsed', () => renderChief(api, 0, new Set(), 10, new Set([bandKey('pm')])).html, 'pm', false],
  ]
  for (const [name, html, slug, open] of cases) assert.equal(head(html(), slug).endsWith(' open>'), open, name)
  // A collapsed band leaves its sub-sections' own state alone.
  const inside = renderStatus(groups, new Set(), new Set([bandKey('needs')])).match(/<details class="group needs-merge" data-group="Awaiting merge approval"[^>]*>/)[0]
  assert.ok(inside.endsWith(' open>'))
})

test('localTimes: UTC times in status text become local am/pm with no zone; anything else stays', () => {
  const was = process.env.TZ
  process.env.TZ = 'America/Toronto'
  try {
    const now = Date.UTC(2026, 10, 14, 12, 0)
    const cases = [
      ['build since 3:55am UTC: child building', 'build since 10:55 pm: child building'],
      ['since 2:05pm UTC', 'since 9:05 am'],
      ['12:00am UTC', '7:00 pm'],
      ['12:00pm UTC', '7:00 am'],
      ['at 14:05', 'at 9:05 am'],
      ['2026-11-02T09:30:00Z', '2026-11-02T09:30:00Z'],
      ['took 10:30:00', 'took 10:30:00'],
      ['at 25:00', 'at 25:00'],
      ['no time here', 'no time here'],
    ]
    for (const [text, want] of cases) assert.equal(localTimes(text, now), want, text)
  } finally {
    if (was === undefined) delete process.env.TZ
    else process.env.TZ = was
  }
})

test('Details show status times in local time with no UTC', () => {
  const html = renderStatus(group([row({ next: 'build since 3:55am UTC: x', risk: 'low, ran at 3:53am' })]))
  assert.match(html, /<dt>Next<\/dt><dd>build since \d\d?:\d\d [ap]m: x<\/dd>/)
  assert.match(html, /<dt>Risk<\/dt><dd>low, ran at \d\d?:\d\d [ap]m<\/dd>/)
  assert.doesNotMatch(html, /UTC/)
})

test('every card is a top row, an optional middle row and a bottom row; the meta holds risk, Spec, PR, time and cost in that order; no status, wait or next line', () => {
  const urls = { specUrl: 'https://x.test/blob/s.md', prUrl: 'https://x.test/pull/2', next: 'why', stageAt: new Date().toISOString(), gantt: [sess({ rows: [task({ cost: 1, segments: [[T, T + 2 * MIN]], end: T + 2 * MIN })] })] }
  const full = 'Low \u00b7 Spec \u00b7 PR \u00b7 2m 00s \u00b7 $1.00'
  const cases = [
    ['Awaiting merge approval', { stage: 'awaiting-merge' }, true, full],
    ['Building', { stage: 'build' }, false, full],
    ['Queued to build', { stage: 'build-queued' }, false, full],
    ['Todo', { stage: '', risk: '' }, false, 'Spec \u00b7 PR \u00b7 2m 00s \u00b7 $1.00'],
    ['Other', { stage: 'blocked' }, false, `${full} \u00b7 Blocked. Needs an answer from you`],
    ['Writing tickets', { stage: '', helper: true }, false, 'Low \u00b7 2m 00s \u00b7 $1.00'],
  ]
  for (const [name, r, middle, meta] of cases) {
    const html = renderStatus([{ name, count: 1, rows: [row({ ...urls, ...r })] }]).split('</li>')[0]
    const [head, actions, foot] = ['class="head"', 'class="actions"', 'class="foot"'].map((k) => html.indexOf(k))
    assert.ok(head > 0 && foot > head && (actions === -1 ? !middle : middle && actions > head && actions < foot), name)
    assert.equal(html.match(/<span class="meta">([\s\S]*?)<\/span><\/div>/)[1].replace(/<[^>]+>/g, ''), meta, name)
    assert.doesNotMatch(html, /class="(status|wait|next)"/, name)
  }
})

test('Approve and Changes show only on a card waiting for approval; they open the Chief of Staff thread with the command typed in, or copy it with no thread', () => {
  const cases = [
    [{ id: 'CW-402', stage: 'awaiting-merge' }, 'approve 402', 'changes 402: '],
    [{ id: 'GUY-7', stage: 'awaiting-build' }, 'approve 7', 'changes 7: '],
    [{ id: 'CW-402', stage: 'awaiting-review' }, null, null],
    [{ id: 'CW-402', stage: 'blocked' }, null, null],
    [{ id: 'helper:x', stage: 'awaiting-merge' }, null, null],
  ]
  for (const [r, approve, changes] of cases) {
    assert.equal(approveCommand(r), approve, JSON.stringify(r))
    assert.equal(approveCommand(r, 'changes'), changes, JSON.stringify(r))
    const controls = (link) => renderStatus([{ name: 'Other', count: 1, rows: [row(r)] }], new Set(), new Set(), new Set(), link).match(/<a class="approve"[^>]*>\w+<\/a>|<button type="button" class="approve"[^>]*>\w+<\/button>/g) ?? []
    const prompt = (t, tip, ret = '') => `<a class="approve" href="${promptLink('<t3-thread://v2/e/t>', t)}" title="${esc(`Opens the Chief of Staff thread with "${t}" typed in${tip}`)}"${ret}>`
    assert.deepEqual(controls('<t3-thread://v2/e/t>'), approve === null ? [] : [`${prompt(approve, ' and presses Send for you. If it can\'t, press Send.', ` data-return="${approve}"`)}Approve</a>`, `${prompt(changes, '. Add what to change, then press Send.')}Changes</a>`], JSON.stringify(r))
    assert.deepEqual(controls(), approve === null ? [] : [`<button type="button" class="approve" data-copy="${approve}">Approve</button>`, `<button type="button" class="approve" data-copy="${changes}">Changes</button>`], JSON.stringify(r))
  }
})

test('promptLink turns a dashboard thread link into a T3 prompt link and refuses anything else', () => {
  const cases = [
    ['<t3-thread://v2/env-1/th:2>', 't3code://threads/env-1/th:2?prompt=a%20b%26c'],
    [undefined, null],
    ['t3-thread://v2/env/th', null],
    ['<t3-thread://v1/env/th>', null],
    ['<t3-thread://v2/env/th/extra>', null],
    ['<t3-thread://v2/en"v/th>', null],
  ]
  for (const [link, want] of cases) assert.equal(promptLink(link, 'a b&c'), want, String(link))
})

test('each Backlog card has a Mark todo control after the switch and before the meta line, a link to the Chief of Staff thread or a copy button; no other tab has one', () => {
  const link = '<t3-thread://v2/e/t>'
  const cases = [
    ['WISE-419', 'mark 419 todo'],
    ['CW-7', 'mark 7 todo'],
    ['helper:x', null],
  ]
  for (const [id, cmd] of cases) {
    assert.equal(todoCommand({ id }), cmd, id)
    const backlog = (chief) => renderBacklog([{ name: 'Backlog', count: 1, rows: [row({ id })] }], new Set(), 0, new Set(), new Set(), chief)
    const foot = (html) => html.match(/<div class="foot">([\s\S]*?)<span class="meta">/)[1]
    const tip = `Opens the Chief of Staff thread with "${cmd}" typed in and presses Send for you. If it can't, press Send.`
    const withLink = cmd && `<a class="todo" href="${promptLink(link, cmd)}" title="${esc(tip)}" data-return="${cmd}">Mark todo</a>`
    const copy = cmd && `<button type="button" class="todo" data-copy="${cmd}">Mark todo</button>`
    for (const [chief, want] of [[link, withLink], [undefined, copy], ['t3-thread://v2/e/t', copy]]) {
      const f = foot(backlog(chief))
      assert.ok(want ? f.endsWith(want) && f.length > want.length : !f.includes('todo'), `${id} ${chief}`)
    }
    const groups = ['Todo', 'Building', 'Awaiting merge approval'].map((name) => ({ name, count: 1, rows: [row({ id })] }))
    assert.doesNotMatch(renderStatus(groups, new Set(), new Set(), new Set(), link), /class="todo"/, id)
  }
})

test('pressMessage: one line per reason for each control, none when sent or a repeat click was busy', () => {
  const tail = ' Press Send in the Chief of Staff thread.'
  for (const action of ['Approve', 'Mark todo']) {
    const generic = `${action} not sent: the dashboard could not press Return.${tail}`
    const cases = [
      [{ sent: true }, ''],
      [{ sent: false, reason: 'busy' }, `${action} not sent: another one-click send was still running.${tail}`],
      [{ sent: false, reason: 'not-frontmost' }, `${action} not sent: T3 Code was not in front.${tail}`],
      [{ sent: false, reason: 'permission' }, new RegExp(`^${action} not sent: macOS has not allowed .* System Settings > Privacy & Security > Accessibility, turn on T3 Code \\(or the app that started the dashboard\\)`)],
      [{ sent: false, reason: 'error' }, generic],
      [{ sent: false, reason: 'toString' }, generic],
      [{ sent: false }, generic],
      [null, generic],
    ]
    for (const [answer, want] of cases) {
      if (want instanceof RegExp) assert.match(pressMessage(answer, false, action), want)
      else assert.equal(pressMessage(answer, false, action), want, `${action} ${JSON.stringify(answer)}`)
    }
    assert.equal(pressMessage({ sent: false, reason: 'busy' }, true, action), '')
  }
  assert.match(pressMessage({ sent: false, reason: 'busy' }), /^Approve not sent:/)
})

test('pressAction names the control from the command', () => {
  for (const [command, want] of [['approve 402', 'Approve'], ['mark 419 todo', 'Mark todo']]) assert.equal(pressAction(command), want, command)
})

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { esc, renderStatus, renderGantt, renderBadges, renderMerged } from './app.js'

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
  assert.match(html, /<button[^>]*data-copy="&lt;t3-thread:\/\/v2\/env\/th&quot;1&gt;"/)
  assert.ok(!renderStatus(group([row()])).includes('<button'))
})

test('empty inputs show quiet lines', () => {
  assert.match(renderStatus([]), /No state yet/)
  assert.match(renderGantt([], 0), /No sessions yet/)
})

test('header badges count the three groups, hide empty alerts and use the singular for one', () => {
  const g = (merge, build, queue) =>
    [['Awaiting merge approval', merge], ['Awaiting build approval', build], ['Queued to build', queue]]
      .filter(([, count]) => count !== undefined)
      .map(([name, count]) => ({ name, count, rows: [] }))
  const text = (html) => [...html.matchAll(/<span class="(badge[^"]*)">([^<]*)<\/span>/g)].map((m) => `${m[1]}|${m[2]}`)
  const none = 'badge quiet|No tickets in the build queue'
  const cases = [
    [g(0, 0, 0), [none]],
    [g(undefined, undefined, undefined), [none]],
    [g(1, 1, 1), ['badge cta-high|1 thread awaiting merge approval', 'badge cta-medium|1 thread awaiting build approval', 'badge quiet|1 ticket in the build queue']],
    [g(3, 2, 5), ['badge cta-high|3 threads awaiting merge approval', 'badge cta-medium|2 threads awaiting build approval', 'badge quiet|5 tickets in the build queue']],
    [g(undefined, 2, undefined), ['badge cta-medium|2 threads awaiting build approval', none]],
  ]
  for (const [groups, want] of cases) assert.deepEqual(text(renderBadges(groups)), want)
  assert.equal(renderBadges(undefined), '')
  assert.equal(renderBadges(null), '')
})

const T = Date.UTC(2026, 10, 7, 12, 0, 0)
const grow = (o) => ({ id: 'a', depth: 0, name: 'agent', repo: 'r', start: T, end: T + 600000, tokens: 12345, cost: null, ...o })
const sess = (o = {}) => ({ sessionId: 's', cwd: '/x', updatedAt: T, stale: false, total: 0.5, rows: [grow()], ...o })

test('gantt escapes text, formats tokens and cost in the row title, and marks running rows', () => {
  const html = renderGantt([sess({ rows: [grow({ name: '<img onerror=x>', kind: 'task' }), grow({ id: 'b', kind: 'task', end: null, tokens: 950, cost: 0.42, model: 'opus-5-5', harness: 'T3 Code' })] })], T + 60000)
  assert.ok(!html.includes('<img'))
  assert.match(html, /&lt;img onerror=x&gt;/)
  assert.match(html, /title="&lt;img onerror=x&gt;\nr · \d\d:\d\d to \d\d:\d\d · 12\.3k tokens\n\/x"/)
  assert.match(html, /r · \d\d:\d\d, running · 950 tokens · opus-5-5 · T3 Code/)
  assert.match(html, /\$0\.42/)
  assert.match(html, /bar running/)
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
      name: 'a task row includes its subagents once even when they run in parallel; a subagent row shows its own share',
      html: one([
        task({ name: 't', cost: 1, segments: [[T, T + 2 * MIN]] }),
        sub({ name: 'x', start: T + MIN, cost: 0.5, segments: [[T + MIN, T + 3 * MIN]] }),
        sub({ name: 'y', start: T + MIN, cost: 0.25, segments: [[T + MIN, T + 2 * MIN]] }),
      ]),
      want: ['t|3m 00s|$1.75', 'x|2m 00s|$0.50', 'y|1m 00s|$0.25', 'Total|3m 00s|$1.75'],
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
  assert.ok(!/bar running/.test(stale))
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
  const note = /priced before the CW-220 rate fix and keep their old costs/
  const html = (...pricing) => renderGantt(pricing.map((p, i) => sess({ sessionId: `s${i}`, pricing: p, total: null, rows: [task({ cost: 1 })] })), T + 10 * MIN)
  assert.doesNotMatch(html(2, 2), note)
  for (const p of [[2, undefined], [null]]) assert.match(html(...p), note)
})

test('a card with sessions gets a closed chart that reopens when its id is in the open set', () => {
  const g = [sess()]
  const html = (open) => renderStatus(group([row({ gantt: g }), row({ id: 'CW-2' })]), open)
  assert.match(html(), /<details class="chart" data-ticket="CW-1"><summary>Agents <span class="pill">1<\/span>/)
  assert.match(html(new Set(['CW-1'])), /<details class="chart" data-ticket="CW-1" open>/)
  assert.equal(html().match(/<details class="chart"/g).length, 1)
  // The pill counts tasks across sessions, not sessions; an older snapshot's session row beside task rows is not one.
  const rows = [grow({ kind: 'session' }), grow({ kind: 'task', depth: 1 }), grow({ kind: 'agent', depth: 2 }), grow({ kind: 'task', depth: 1 })]
  assert.match(renderStatus(group([row({ gantt: [sess({ rows }), sess({ rows: [grow({ kind: 'task' })] })] })])), /Agents <span class="pill">3<\/span>/)
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
  const cards = (html) => (html.match(/<li class="row">/g) ?? []).length
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
  assert.match(one.html, /merged 2026-01-02 03:04/)
  assert.match(renderMerged([], 5).html, /Nothing merged yet/)
  const bad = renderMerged([{ id: '<b>', title: '<script>x</script>', prUrl: 'javascript:1', issueUrl: 'javascript:2', mergedAt: 0 }], 0).html
  assert.ok(!bad.includes('<script') && !bad.includes('<b>') && !bad.includes('href='))
})

test('merged row shows spend only when the entry has it', () => {
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const html = (spend) => renderMerged([{ ...e, ...(spend ? { spend } : {}) }], 0).html
  assert.doesNotMatch(html(), /cost|tokens/)
  assert.match(html({ cost: 0.4166, tokens: 955168 }), /<span class="num cost">\$0\.42<\/span><span class="meta">955\.2k tokens<\/span>/)
  const none = html({ cost: null, tokens: 12 })
  assert.match(none, /12 tokens/)
  assert.doesNotMatch(none, /cost|\$|–/)
})

test('groups sort into bands, keep api order inside a band, and show the stage only in Other', () => {
  const g = (name, rows = [row({ id: `${name}-1`, stage: 'build' })]) => ({ name, count: rows.length, rows })
  const bandsOf = (html) => [...html.matchAll(/<h2>([^<]+)<\/h2>|<h3>([^<]+?) <span/g)].map((m) => m[1] ?? m[2])
  const names = [g('Building'), g('Mystery'), g('Awaiting build approval'), g('Queued to build'), g('Awaiting merge approval'), g('Speccing')]
  assert.deepEqual(bandsOf(renderStatus(names)), ['Needs you', 'Awaiting build approval', 'Awaiting merge approval', 'In progress', 'Building', 'Mystery', 'Speccing', 'Queued', 'Queued to build'])
  assert.deepEqual(bandsOf(renderStatus([g('Merging')])), ['In progress', 'Merging'])
  const other = renderStatus([g('Other', [row({ id: 'A', stage: 'blocked' }), row({ id: 'B', stage: 'spec-queued' })]), g('Building')])
  assert.match(other, /class="row blocked"[\s\S]*>blocked<[\s\S]*>spec queued</)
  assert.equal((other.match(/badge stage/g) ?? []).length, 2)
  assert.match(renderStatus([g('Awaiting merge approval')]), /class="group needs-merge"/)
})

test('merged row with sessions has a closed Agents chart that stays open when its id is in the open set; one without has none', () => {
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const html = (gantt, open) => renderMerged([{ ...e, ...(gantt ? { gantt } : {}) }, { ...e, id: 'CW-2' }], 0, 10, open).html
  assert.match(html([sess(), sess()]), /<details class="chart" data-merged="CW-1"><summary>Agents <span class="pill">2<\/span><\/summary><div class="chart-body" data-merged="CW-1"><\/div>/)
  assert.match(html([sess()], new Set(['CW-1'])), /<details class="chart" data-merged="CW-1" open>/)
  assert.equal(html([sess()]).match(/<details/g).length, 1)
  assert.doesNotMatch(html([]), /<details|Agents/)
  assert.doesNotMatch(html(), /<details|Agents/)
})

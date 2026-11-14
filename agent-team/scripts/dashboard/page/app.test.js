import { test } from 'node:test'
import assert from 'node:assert/strict'
import { esc, renderMarkdown, renderStatus, renderGantt, renderBadges, renderMerged, renderChief, tabFromStorage, drawCharts, versionWatch } from './app.js'

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
  assert.match(html, /<div class="head">.*<button type="button" class="copy-icon" data-copy="&lt;t3-thread:\/\/v2\/env\/th&quot;1&gt;" aria-label="Copy thread link"/)
  assert.ok(!html.includes('>Copy thread link<'))
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
  assert.ok(!/bar running/.test(stale))
})

test('each bar has an escaped tooltip with its own range, length and the row model; a running bar says running', () => {
  const html = renderGantt([sess({ rows: [task({ name: '<b>t</b>', model: 'opus-5-5', end: null, segments: [[T, T + MIN], [T + 5 * MIN, null]] })] })], T + 8 * MIN)
  const titles = [...html.matchAll(/class="bar[^"]*"[^>]*title="([^"]*)"/g)].map((m) => m[1])
  assert.equal(titles.length, 2)
  assert.match(titles[0], /^&lt;b&gt;t&lt;\/b&gt;\n\d\d:\d\d to \d\d:\d\d · 1m 00s · opus-5-5$/)
  assert.match(titles[1], /^&lt;b&gt;t&lt;\/b&gt;\n\d\d:\d\d, running · opus-5-5$/)
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
  const section = (html, id) => html.match(new RegExp(`<details class="info" data-ticket="${id}"[^>]*>[\\s\\S]*?</details>`))[0]
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
  assert.match(got[6][1], /^\d{4}-\d\d-\d\d \d\d:\d\d \(stale\)$/)
  const links = section(html, 'CW-1').match(/<p class="info-links">([\s\S]*?)<\/p>/)[1]
  assert.equal(links.replace(/<a href="([^"]*)"[^>]*>/g, '[$1]').replace(/<\/a>/g, ''), '[https://x.test/issues/1]Issue #1 \u00b7 [https://x.test/pull/2]PR #2 \u00b7 <code>t3-thread://v2/env/&lt;th&gt;</code>')
  assert.ok(!section(html, 'CW-1').includes('<i>') && !section(html, 'CW-1').includes('<th>'))

  const none = section(html, 'CW-2')
  assert.ok(none.startsWith('<details class="info" data-ticket="CW-2"><summary>Details</summary>'))
  assert.match(none, /<p class="quiet">Nothing more known yet<\/p>/)
  assert.doesNotMatch(none, /<dt>|href=|<dd><\/dd>|info-links|info-facts/)

  assert.match(renderStatus(group([full]), new Set(), new Set(), new Set(['CW-1'])), /<details class="info" data-ticket="CW-1" open>/)
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
  const section = (id) => html.match(new RegExp(`<details class="info" data-ticket="${id}"[^>]*>[\\s\\S]*?</details>`))[0]
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

test('a Spec link sits right before PR on a card, a flat row and a merged row; it is left out without an http(s) url', () => {
  const sub = (html) => html.match(/<div class="sub">([\s\S]*?)<\/div>/)[1]
  const anchors = (html) => [...sub(html).matchAll(/<a href="([^"]*)"[^>]*>([^<]*)<\/a>/g)].map((m) => `${m[2]}=${m[1]}`)
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const renders = {
    card: (specUrl) => renderStatus(group([row({ prUrl: 'https://x.test/pull/1', specUrl })])),
    row: (specUrl) => renderStatus([{ name: 'Queued to build', count: 1, rows: [row({ prUrl: 'https://x.test/pull/1', specUrl })] }]),
    merged: (specUrl) => renderMerged([{ ...e, specUrl }], 0).html,
  }
  for (const [name, render] of Object.entries(renders)) {
    assert.deepEqual(anchors(render('https://x.test/blob/a.md')), ['Spec=https://x.test/blob/a.md', 'PR=https://x.test/pull/1'], name)
    for (const bad of [undefined, 'javascript:alert(1)']) {
      assert.deepEqual(anchors(render(bad)), ['PR=https://x.test/pull/1'], name)
      assert.ok(!render(bad).includes('class="spec"'), name)
    }
  }
})

test('a merged row has a closed Details section filled only when open; it shows the links line and the PR text', () => {
  const e = { id: 'CW-9', title: 't', prUrl: 'https://x.test/pull/9', issueUrl: 'https://x.test/issues/9', specUrl: 'https://x.test/blob/s.md', mergedAt: 0, detail: { kind: 'changes', sections: [{ name: 'Summary', text: 'Did **it**' }] } }
  const closed = renderMerged([e], 0).html
  assert.match(closed, /<details class="info" data-merged="CW-9"><summary>Details<\/summary><div class="info-body" data-merged="CW-9"><\/div><\/details>/)
  const open = renderMerged([e], 0, 10, new Set(), new Set(['CW-9'])).html
  assert.match(open, /<details class="info" data-merged="CW-9" open>/)
  assert.match(open, /<p class="info-links">[^]*Issue #9[^]*Spec[^]*PR #9[^]*<\/p>/)
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

test('a running ticket helper is a placeholder card, and Todo and Backlog are flat rows under Not started', () => {
  const hostile = '<img src=x onerror=1>'
  const link = '<t3-thread://v2/env/th1>'
  const mine = sess({ rows: [task({ segments: [[T, T + MIN]] })] })
  const writing = { name: 'Writing tickets', count: 1, rows: [row({ id: `helper:${hostile}`, title: hostile, helper: true, risk: '', next: '', stage: '', threadLink: link, gantt: [mine] })] }
  const todo = { name: 'Todo', count: 1, rows: [row({ id: 'CW-7', title: hostile, issueUrl: 'https://x.test/issues/7', risk: '', next: '', stage: '' })] }
  const backlog = { name: 'Backlog', count: 1, rows: [row({ id: 'CW-8', title: 'later', risk: '', next: '', stage: '', gantt: [mine] })] }
  const html = renderStatus([...group([row()]), writing, todo, backlog, { name: 'Queued to build', count: 1, rows: [row({ id: 'CW-9' })] }])
  const part = (name) => html.split(`<section class="band band-${name}">`)[1]?.split('</section>')[0] ?? ''
  const card = part('progress')
  assert.match(card, /<span class="id">Ticket helper<\/span> <span class="title">&lt;img src=x onerror=1&gt;<\/span>/)
  assert.match(card, /data-copy="&lt;t3-thread:\/\/v2\/env\/th1&gt;"/)
  assert.match(card, /<details class="chart" data-ticket="helper:&lt;img[^>]*>/)
  const placeholder = card.split('<li class="ticket">').find((li) => li.includes('Ticket helper')).split('</li>')[0]
  assert.ok(!/<a |Details|class="info"/.test(placeholder), 'no link or Details on the placeholder')
  assert.ok(card.indexOf('Building') < card.indexOf('Writing tickets'), 'api order kept')
  assert.ok(!html.includes('<img'))
  const idle = part('not-started')
  assert.ok(idle.indexOf('>Todo ') < idle.indexOf('>Backlog '), 'api order kept: Todo then Backlog')
  assert.equal([...idle.matchAll(/<li class="row">/g)].length, 2)
  assert.ok(!idle.includes('<li class="ticket"') && !idle.includes('badge risk'))
  assert.match(idle, /href="https:\/\/x\.test\/issues\/7"/)
  assert.match(idle, /data-ticket="CW-8"/)
  assert.ok(html.indexOf('band-queued') < html.indexOf('band-not-started'), 'Not started follows Queued')
  assert.equal(renderStatus([todo]).includes('No state yet'), false)
})

test('merged row with sessions has a closed Agents chart that stays open when its id is in the open set; one without has none', () => {
  const e = { id: 'CW-1', title: 't', prUrl: 'https://x.test/pull/1', mergedAt: 0 }
  const html = (gantt, open) => renderMerged([{ ...e, ...(gantt ? { gantt } : {}) }, { ...e, id: 'CW-2' }], 0, 10, open).html
  assert.match(html([sess(), sess()]), /<details class="chart" data-merged="CW-1"><summary>Agents <span class="pill">2<\/span><\/summary><div class="chart-body" data-merged="CW-1"><\/div>/)
  assert.match(html([sess()], new Set(['CW-1'])), /<details class="chart" data-merged="CW-1" open>/)
  assert.equal(html([sess()]).match(/<details class="chart"/g).length, 1)
  assert.doesNotMatch(html([]), /<details class="chart"|Agents/)
  assert.doesNotMatch(html(), /<details class="chart"|Agents/)
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
  assert.ok(/<details class="chart" data-pm="&lt;img[^>]* open>/.test(first.html))
  assert.equal([...first.html.matchAll(/<li class="row">/g)].length, 10)
  assert.match(first.html, /Page 1 of 2/)
  const last = renderChief(api, 99)
  assert.equal(last.page, 1)
  assert.equal([...last.html.matchAll(/<li class="row">/g)].length, 2)
  assert.deepEqual(['cos', 'ship', null, undefined, 'x', 'COS', 5].map(tabFromStorage), ['cos', 'ship', 'ship', 'ship', 'ship', 'ship', 'ship'])
  const bodies = { 'data-chief': [{ dataset: {} }], 'data-pm': [{ dataset: { pm: 's2' } }, { dataset: { pm: 'gone' } }] }
  const drawn = []
  drawCharts({ querySelectorAll: (sel) => bodies[/data-[a-z]+/.exec(sel)?.[0]] ?? [] }, { status: [], merged: [], ...api }, T, (b, html) => drawn.push([b.dataset.pm ?? 'chief', html.includes('class="gantt"')]))
  assert.deepEqual(drawn, [['s2', true], ['chief', true]])
})

test('a group with an http(s) moreUrl ends with an escaped Full backlog link inside its section; any other moreUrl draws none', () => {
  const rows = [row({ id: 'CW-8', title: 'later', risk: '', next: '', stage: '' })]
  const html = (moreUrl) => renderStatus([{ name: 'Backlog', count: 9, rows, moreUrl }])
  const ok = html('https://x.test/o/r/issues?a=1&b="2"')
  assert.match(ok, /<\/ul><p class="more"><a href="https:\/\/x\.test\/o\/r\/issues\?a=1&amp;b=&quot;2&quot;" target="_blank" rel="noopener noreferrer">Full backlog<\/a><\/p><\/details>/)
  for (const bad of ['javascript:alert(1)', '//x.test/issues', undefined]) assert.ok(!html(bad).includes('Full backlog'), String(bad))
})

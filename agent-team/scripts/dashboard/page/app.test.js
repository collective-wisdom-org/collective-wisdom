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
  const none = 'badge|No tickets in the build queue'
  const cases = [
    [g(0, 0, 0), [none]],
    [g(undefined, undefined, undefined), [none]],
    [g(1, 1, 1), ['badge cta-high|1 thread awaiting merge approval', 'badge cta-medium|1 thread awaiting build approval', 'badge|1 ticket in the build queue']],
    [g(3, 2, 5), ['badge cta-high|3 threads awaiting merge approval', 'badge cta-medium|2 threads awaiting build approval', 'badge|5 tickets in the build queue']],
    [g(undefined, 2, undefined), ['badge cta-medium|2 threads awaiting build approval', none]],
  ]
  for (const [groups, want] of cases) assert.deepEqual(text(renderBadges(groups)), want)
  assert.equal(renderBadges(undefined), '')
  assert.equal(renderBadges(null), '')
})

const T = Date.UTC(2026, 10, 7, 12, 0, 0)
const grow = (o) => ({ id: 'a', depth: 0, name: 'agent', repo: 'r', start: T, end: T + 600000, tokens: 12345, cost: null, ...o })
const sess = (o = {}) => ({ sessionId: 's', cwd: '/x', updatedAt: T, stale: false, total: 0.5, rows: [grow()], ...o })

test('gantt escapes names, formats tokens and cost, and marks running rows', () => {
  const html = renderGantt([sess({ rows: [grow({ name: '<img onerror=x>', depth: 1 }), grow({ end: null, tokens: 950, cost: 0.42 })] })], T + 60000)
  assert.ok(!html.includes('<img'))
  assert.match(html, /&lt;img onerror=x&gt;/)
  assert.match(html, /12\.3k/)
  assert.match(html, /950/)
  assert.match(html, /\$0\.42/)
  assert.match(html, /–/)
  assert.match(html, /running/)
  assert.match(html, /\$0\.50/)
})

test('gantt draws one bar per segment and model and harness cells, no kids', () => {
  const bars = (html) => [...html.matchAll(/<span class="bar( running)?" style="left:([\d.]+)%;width:([\d.]+)%/g)].map((m) => [m[1] ? 'running' : '', Number(m[2]), Number(m[3])])
  const seg = [[T, T + 100000], [T + 300000, T + 400000], [T + 500000, null]]
  const live = renderGantt([sess({ rows: [grow({ end: null, segments: seg, model: 'opus-5-5', harness: 'T3 Code' })] })], T + 600000)
  assert.deepEqual(bars(live), [['', 0, 16.67], ['', 50, 16.67], ['running', 83.33, 16.67]])
  assert.match(live, /<span class="model">opus-5-5<\/span>\s*<span class="harness">T3 Code<\/span>/)
  assert.match(live, /<span>Model<\/span><span>Harness<\/span>/)
  assert.ok(!/kids|Kids/.test(live))
  const stale = renderGantt([sess({ stale: true, updatedAt: T + 600000, rows: [grow({ segments: seg })] })], T + 900000)
  assert.ok(!/bar running/.test(stale))
  const old = renderGantt([sess({ rows: [grow()] })], T + 60000)
  assert.equal(bars(old).length, 1)
  assert.match(old, /<span class="model">–<\/span>\s*<span class="harness">–<\/span>/)
})

test('the shared axis follows now for a live session and freezes for a stale one', () => {
  // The closed row (index 1) shrinks on the axis as the running row grows.
  const closedWidth = (html) => Number([...html.matchAll(/class="bar[^"]*" style="[^"]*width:([\d.]+)%/g)][1][1])
  const run = (now, stale) => renderGantt([sess({ stale, updatedAt: T + 60000, rows: [grow({ end: null }), grow({ id: 'b', start: T, end: T + 60000 })] })], now)
  assert.ok(closedWidth(run(T + 600000, false)) < closedWidth(run(T + 120000, false)))
  assert.equal(closedWidth(run(T + 600000, true)), closedWidth(run(T + 120000, true)))
  assert.match(run(T, true), /class="session stale"/)
  assert.ok(!/class="session stale"/.test(run(T, false)))
})

test('a card with sessions gets a closed chart that reopens when its id is in the open set', () => {
  const g = [sess()]
  const html = (open) => renderStatus(group([row({ gantt: g }), row({ id: 'CW-2' })]), open)
  assert.match(html(), /<details class="chart" data-ticket="CW-1"><summary>Agents <span class="pill">1<\/span>/)
  assert.match(html(new Set(['CW-1'])), /<details class="chart" data-ticket="CW-1" open>/)
  assert.equal(html().match(/<details/g).length, 1)
})

test('merged list pages by ten, clamps the page, disables the pager ends and escapes text', () => {
  const list = Array.from({ length: 25 }, (_, i) => ({ id: `CW-${i + 1}`, title: `t${i + 1}`, prUrl: `https://x.test/pull/${i + 1}`, mergedAt: new Date(2026, 0, 2, 3, 4).getTime() }))
  const cards = (html) => (html.match(/<li class="ticket">/g) ?? []).length
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

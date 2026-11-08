// Dashboard page. Pure render functions (tested in Node) plus a browser shell.

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])

const isHttp = (u) => typeof u === 'string' && /^https?:\/\//i.test(u)
const link = (url, label) => (isHttp(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : esc(label))

const two = (n) => String(n).padStart(2, '0')
const clock = (ms) => {
  const d = new Date(ms)
  return `${two(d.getHours())}:${two(d.getMinutes())}`
}
const tokens = (n) => (n >= 999_950 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1e3).toFixed(1)}k` : String(n))
const dollars = (c) => (c === null || c === undefined ? '–' : `$${c.toFixed(2)}`)

const riskClass = (risk) => {
  const w = /^[a-z]+/.exec(String(risk ?? '').trim().toLowerCase())
  return w && ['low', 'medium', 'high'].includes(w[0]) ? ` risk-${w[0]}` : ''
}

// Bands are a page-side order over the /api groups. A group name the page does not know goes to In progress.
const NEEDS_YOU = ['Awaiting merge approval', 'Awaiting build approval']
const QUEUED = ['Queued to merge', 'Queued to build', 'Other']
const BANDS = [
  { name: 'Needs you', slug: 'needs', has: (n) => NEEDS_YOU.includes(n) },
  { name: 'In progress', slug: 'progress', has: (n) => !NEEDS_YOU.includes(n) && !QUEUED.includes(n) },
  { name: 'Queued', slug: 'queued', has: (n) => QUEUED.includes(n) },
]
const GROUP_CLASS = new Map([['Awaiting merge approval', ' needs-merge'], ['Awaiting build approval', ' needs-build']])
const STAGE_WORDS = new Map([['blocked', 'blocked'], ['spec-queued', 'spec queued']])

const stageWords = (stage) => STAGE_WORDS.get(stage) ?? stage.replace(/-/g, ' ')

const list = (x) => (Array.isArray(x) ? x.filter((e) => typeof e === 'object' && e !== null) : [])

/** What the spec or the PR says, as plain text. It comes from agents, so every string is escaped and only an http(s) url becomes an anchor. */
function renderDetail(d) {
  const sections = list(d?.sections)
  const files = list(d?.files)
  const reviews = list(d?.reviews)
  if (sections.length === 0 && files.length === 0 && reviews.length === 0 && !(d?.moreFiles > 0)) return ''
  const open = isHttp(d.url) ? ` <span class="detail-open">${link(d.url, 'Open')}</span>` : ''
  const out = [`<h4 class="detail-head">${d.kind === 'changes' ? 'Changes' : 'Spec'}${open}</h4>`]
  for (const s of sections) out.push(`<h4>${esc(s.name)}</h4><p class="detail-text">${esc(s.text)}</p>`)
  for (const v of reviews) out.push(`<p class="detail-review">${esc(v.name)}: ${link(v.url, v.verdict)}</p>`)
  if (files.length || d.moreFiles > 0) {
    const items = files.map((f) => `<li>${esc(f.path)} <span class="add">+${esc(Number(f.add) || 0)}</span> <span class="del">\u2212${esc(Number(f.del) || 0)}</span></li>`)
    if (d.moreFiles > 0) items.push(`<li>and ${esc(d.moreFiles)} more ${d.moreFiles === 1 ? 'file' : 'files'}</li>`)
    out.push(`<ul class="detail-files">${items.join('')}</ul>`)
  }
  return out.join('')
}

/** The `Details` body: a line per known fact, in a fixed order, or one quiet line when none is known. */
export function renderDetails(r, now) {
  const lines = []
  const add = (label, html) => lines.push(`<dt>${label}</dt><dd>${html}</dd>`)
  if (r.stage) add('Stage', esc(stageWords(r.stage)))
  if (r.risk) add('Risk', esc(r.risk))
  if (r.next) add('Next', esc(r.next))
  if (isHttp(r.issueUrl)) add('Issue', link(r.issueUrl, r.issueUrl))
  if (isHttp(r.prUrl)) add('PR', link(r.prUrl, r.prUrl))
  if (r.threadLink) add('Thread', `<code>${esc(r.threadLink)}</code>`)
  if (r.gantt && r.gantt.length > 0) {
    const items = ganttTasks(r.gantt, now)
    const drawn = items.flatMap((i) => [i, ...i.kids])
    const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
    const subagents = drawn.filter((d) => d.r.kind === 'agent').length
    const agents = [plural(r.gantt.length, 'session'), items.length ? plural(items.length, 'task') : '', subagents ? plural(subagents, 'subagent') : '']
    add('Agents', esc(agents.filter(Boolean).join(', ')))
    add('Tokens', esc(tokens(drawn.reduce((n, d) => n + (d.r.tokens || 0), 0))))
    const cost = ganttCost(items)
    if (typeof cost === 'number') add('Cost', esc(dollars(cost)))
    const newest = r.gantt.reduce((a, s) => (s.updatedAt > a.updatedAt ? s : a))
    add('Last update', esc(`${stamp(newest.updatedAt)}${newest.stale ? ' (stale)' : ''}`))
  }
  const facts = lines.length ? `<dl class="info-list">${lines.join('')}</dl>` : ''
  return facts + renderDetail(r.detail) || '<p class="quiet">Nothing more known yet</p>'
}

/** One ticket as a card (`li.ticket`) or a flat row (`li.row`). The stage shows only in `Other`, where the heading does not say it. */
function ticket(r, { flat, other, open, info }) {
  const copy = r.threadLink ? `<button type="button" class="copy" data-copy="${esc(r.threadLink)}">Copy thread link</button>` : ''
  const stage = other && r.stage ? `<span class="badge stage">${esc(stageWords(r.stage))}</span>` : ''
  const next = r.next ? `<${flat ? 'span' : 'div'} class="next">${esc(r.next)}</${flat ? 'span' : 'div'}>` : ''
  const blocked = other && r.stage === 'blocked' ? ' blocked' : ''
  return `<li class="${flat ? 'row' : 'ticket'}${blocked}">
  <div class="head"><span class="id">${link(r.issueUrl, r.id)}</span>${r.title ? ` <span class="title">${esc(r.title)}</span>` : ''}</div>
  <div class="sub">${stage}${r.risk ? `<span class="badge risk${riskClass(r.risk)}">${esc(r.risk)}</span>` : ''}${r.prUrl ? `<span class="pr">${link(r.prUrl, 'PR')}</span>` : ''}${flat ? next : ''}${copy}</div>
  ${flat ? '' : next}
  ${r.gantt && taskCount(r.gantt) ? `<details class="chart" data-ticket="${esc(r.id)}"${open.has(r.id) ? ' open' : ''}><summary>Agents <span class="pill">${esc(taskCount(r.gantt))}</span></summary><div class="chart-body" data-ticket="${esc(r.id)}"></div></details>` : ''}
  <details class="info" data-ticket="${esc(r.id)}"${info.has(r.id) ? ' open' : ''}><summary>Details</summary><div class="info-body" data-ticket="${esc(r.id)}">${renderDetails(r, Date.now())}</div></details>
</li>`
}

/** `open` holds the ids of tickets whose `Agents` chart is open, `info` those whose `Details` is open. */
export function renderStatus(groups, open = new Set(), collapsed = new Set(), info = new Set()) {
  if (!groups || groups.length === 0) return '<p class="quiet">No state yet</p>'
  return BANDS.map((band) => {
    const mine = groups.filter((g) => band.has(g.name))
    if (mine.length === 0) return ''
    const flat = band.slug === 'queued'
    const sections = mine
      .map((g) => {
        const rows = g.rows.map((r) => ticket(r, { flat, other: g.name === 'Other', open, info })).join('\n')
        return `<details class="group${GROUP_CLASS.get(g.name) ?? ''}" data-group="${esc(g.name)}"${collapsed.has(g.name) ? '' : ' open'}><summary><h3>${esc(g.name)} <span class="pill">${esc(g.count)}</span></h3></summary><ul class="${flat ? 'rows' : 'cards'}">${rows}</ul></details>`
      })
      .join('\n')
    return `<section class="band band-${band.slug}"><h2>${band.name}</h2>${sections}</section>`
  }).join('\n')
}

export function renderBadges(groups) {
  if (!Array.isArray(groups)) return ''
  const count = (name) => groups.find((g) => g.name === name)?.count ?? 0
  const merge = count('Awaiting merge approval')
  const build = count('Awaiting build approval')
  const queue = count('Queued to build')
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
  return [
    merge > 0 ? `<span class="badge cta-high">${plural(merge, 'thread')} awaiting merge approval</span>` : '',
    build > 0 ? `<span class="badge cta-medium">${plural(build, 'thread')} awaiting build approval</span>` : '',
    `<span class="badge quiet">${queue > 0 ? `${plural(queue, 'ticket')} in the build queue` : 'No tickets in the build queue'}</span>`,
  ].join('')
}

const stamp = (ms) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())} ${clock(ms)}`
}

const spent = (s) => (s ? `${typeof s.cost === 'number' ? `<span class="num cost">${dollars(s.cost)}</span>` : ''}<span class="meta">${tokens(s.tokens)} tokens</span>` : '')

/** One page of the merged list as flat rows plus a pager. `page` is 0-based and comes back clamped; `open` holds the ids of merged charts to keep open. */
export function renderMerged(list, page, size = 10, open = new Set()) {
  if (!list || list.length === 0) return { html: '<p class="quiet">Nothing merged yet</p>', page: 0 }
  const pages = Math.ceil(list.length / size)
  const at = Math.min(Math.max(0, Math.trunc(page) || 0), pages - 1)
  const rows = list
    .slice(at * size, (at + 1) * size)
    .map(
      (e) => `<li class="row">
  <div class="head"><span class="id">${link(e.issueUrl, e.id)}</span> <span class="title">${esc(e.title)}</span></div>
  <div class="sub"><span class="pr">${link(e.prUrl, 'PR')}</span><span class="next">merged ${esc(stamp(e.mergedAt))}</span>${spent(e.spend)}</div>
  ${e.gantt && taskCount(e.gantt) ? `<details class="chart" data-merged="${esc(e.id)}"${open.has(e.id) ? ' open' : ''}><summary>Agents <span class="pill">${esc(taskCount(e.gantt))}</span></summary><div class="chart-body" data-merged="${esc(e.id)}"></div></details>` : ''}
</li>`,
    )
    .join('\n')
  const pager =
    pages > 1
      ? `<nav class="pager"><button type="button" data-page="${at - 1}"${at === 0 ? ' disabled' : ''}>Newer</button> <span>Page ${at + 1} of ${pages}</span> <button type="button" data-page="${at + 1}"${at === pages - 1 ? ' disabled' : ''}>Older</button></nav>`
      : ''
  return { html: `<ul class="rows">${rows}</ul>${pager}`, page: at }
}

const duration = (ms) => {
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return m < 60 ? `${m}m ${two(s % 60)}s` : `${Math.floor(m / 60)}h ${two(m % 60)}m`
}

/** Merges working spans [a, b, open] into disjoint ones, in order. A merged span is open if any part of it is. */
const union = (spans) => {
  const out = []
  for (const [a, b, open] of [...spans].sort((x, y) => x[0] - y[0])) {
    const last = out[out.length - 1]
    if (last && a <= last[1]) {
      last[1] = Math.max(last[1], b)
      last[2] = last[2] || open
    } else out.push([a, b, open])
  }
  return out
}

const sumCost = (list) => (list.some((c) => typeof c !== 'number') ? null : list.reduce((n, c) => n + c, 0))

/** A task's cost with the rows under it; null when any of them is unpriced. */
const itemCost = (i) => sumCost([i.r.cost, ...i.kids.map((k) => k.r.cost)])

/** The chart's Total: the sum over its tasks, null when any row is unpriced. */
const ganttCost = (items) => sumCost(items.map(itemCost))

/** The row's working spans with open ends closed at the session's clock; a row with none draws one span from start to end. */
function spansOf(r, clockNow) {
  const raw = Array.isArray(r.segments) && r.segments.length ? r.segments : [[r.start, r.end]]
  return raw.map(([a, b]) => {
    const open = b === null || b === undefined
    return [a, open ? Math.max(a, clockNow) : b, open]
  })
}

/**
 * The top-level tasks of the sessions in start order, each with the rows nested under it.
 * A task is a `task` row or an `agent` row at depth 1. An older snapshot's `session` row is dropped when its session has task rows, else it is a task.
 */
function ganttTasks(sessions, now) {
  const items = []
  for (const s of sessions ?? []) {
    const clockNow = s.stale ? s.updatedAt : now
    const hasTasks = s.rows.some((r) => r.kind === 'task')
    let current = null
    for (const r of s.rows) {
      if (r.kind === 'session' && hasTasks) continue
      const row = { r, s, spans: spansOf(r, clockNow), clockNow }
      if (r.kind === 'agent' && r.depth >= 2 && current) current.kids.push(row)
      else items.push((current = { ...row, kids: [] }))
    }
  }
  return items.sort((a, b) => a.r.start - b.r.start)
}

/** How many tasks the chart draws, for the `Agents` pill. */
export const taskCount = (sessions) => ganttTasks(sessions, 0).length

const rowTitle = ({ r, s, clockNow }) => {
  const running = (r.end === null || r.end === undefined) && !s.stale
  const range = running ? `${clock(r.start)}, running` : `${clock(r.start)} to ${clock(r.end ?? clockNow)}`
  const meta = [r.repo, range, `${tokens(r.tokens)} tokens`, r.model, r.harness].filter((p) => p !== null && p !== undefined && p !== '')
  return [r.name, meta.join(' · '), s.cwd].join('\n')
}

export function renderGantt(sessions, now) {
  if (!sessions || sessions.length === 0) return '<p class="quiet">No sessions yet</p>'
  const items = ganttTasks(sessions, now)
  if (items.length === 0) return '<p class="quiet">No tasks yet</p>'
  // The axis is active time: the union of every working span, so a time maps to the active ms before it and gaps take no width.
  const active = union(items.flatMap((i) => [...i.spans, ...i.kids.flatMap((k) => k.spans)]))
  const total = active.reduce((n, [a, b]) => n + (b - a), 0)
  const scale = Math.max(1, total)
  const pos = (t) => {
    let before = 0
    for (const [a, b] of active) {
      if (t >= b) before += b - a
      else {
        if (t > a) before += t - a
        break
      }
    }
    return before
  }
  const bars = (row, spans) =>
    union(spans)
      .map(([a, b, open]) => {
        const left = Math.min(99, (pos(a) / scale) * 100)
        const width = Math.min(100 - left, Math.max(0.5, ((pos(b) - pos(a)) / scale) * 100))
        const running = open && !row.s.stale
        const range = running ? `${clock(a)}, running` : `${clock(a)} to ${clock(b)}`
        const meta = [range, running ? '' : duration(b - a), row.r.model].filter((p) => p !== null && p !== undefined && p !== '')
        const title = esc(`${row.r.name}\n${meta.join(' · ')}`)
        return `<span class="bar${running ? ' running' : ''}" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%" title="${title}"></span>`
      })
      .join('')
  const length = (spans) => union(spans).reduce((n, [a, b]) => n + (b - a), 0)
  const line = (row, spans, cost, depth) => `<div class="grow${depth > 0 ? ' sub' : ''}${row.s.stale ? ' stale' : ''}" title="${esc(rowTitle(row))}">
  <span class="name" style="padding-left:${depth * 1.2}em">${esc(row.r.name)}${row.s.stale ? ' <span class="pill">stale</span>' : ''}</span>
  <span class="track">${bars(row, spans)}</span>
  <span class="num dur">${duration(length(spans))}</span>
  <span class="num cost">${dollars(cost)}</span>
</div>`
  const rows = items.map((i) => {
    return [line(i, i.spans, itemCost(i), 0), ...i.kids.map((k) => line(k, k.spans, k.r.cost, Math.max(1, k.r.depth - i.r.depth)))].join('\n')
  })
  const sum = ganttCost(items)
  const reported = sessions.every((s) => typeof s.total === 'number') ? sessions.reduce((n, s) => n + s.total, 0) : null
  const note =
    sum !== null && reported !== null && Math.abs(reported - sum) >= 0.01 - 1e-9
      ? `<p class="gnote">Claude Code reports ${dollars(reported)} for these sessions. Row costs use prices.json.</p>`
      : ''
  const isOld = sessions.some((s) => s.pricing !== 2)
  const oldNote = isOld ? '<p class="gnote">Some rows were priced before the CW-220 rate fix and keep their old costs.</p>' : ''
  return `<div class="gantt">
${rows.join('\n')}
<div class="grow gtotal"><span class="name">Total</span><span class="num dur">${duration(total)}</span><span class="num cost">${dollars(sum)}</span></div>
${note}
${oldNote}
</div>`
}

// Last html written to each chart body, so an unchanged chart is left alone and a hovered bar keeps its tooltip.
const shownCharts = new WeakMap()

/** Renders each open chart body in `root` and calls `apply(body, html)` only when its html changed since the last write. */
export function drawCharts(root, data, now, apply) {
  const rows = new Map(data.status.flatMap((g) => g.rows).map((r) => [r.id, r]))
  const merged = new Map(data.merged.map((e) => [e.id, e]))
  const draw = (body, entry) => {
    if (!entry) return
    const html = renderGantt(entry.gantt, now)
    if (shownCharts.get(body) === html) return
    apply(body, html)
    shownCharts.set(body, html)
  }
  for (const body of root.querySelectorAll('.chart-body[data-ticket]')) draw(body, rows.get(body.dataset.ticket))
  for (const body of root.querySelectorAll('.chart-body[data-merged]')) draw(body, merged.get(body.dataset.merged))
}

/** Returns `seen(version)`: true when a page version differs from the first one seen. Anything but a non-empty string is ignored. */
export function versionWatch() {
  let baseline = null
  return (version) => {
    if (typeof version !== 'string' || !version) return false
    if (baseline === null) {
      baseline = version
      return false
    }
    return version !== baseline
  }
}

if (typeof document !== 'undefined') {
  // Updates a chart in place so the element under the pointer survives a tick and its native tooltip can show.
  const patchChart = (body, html) => {
    if (body.innerHTML === '') {
      body.innerHTML = html
      return
    }
    const tpl = document.createElement('template')
    tpl.innerHTML = html
    patchNode(body, tpl.content)
  }
  const patchNode = (old, next) => {
    const a = [...old.childNodes]
    const b = [...next.childNodes]
    for (let i = 0; i < b.length; i++) {
      const o = a[i]
      const n = b[i]
      if (!o) old.append(n)
      else if (o.nodeType !== n.nodeType || o.nodeName !== n.nodeName) o.replaceWith(n)
      else if (o.nodeType !== 1) {
        if (o.nodeValue !== n.nodeValue) o.nodeValue = n.nodeValue
      } else if (o.childNodes.length !== n.childNodes.length) o.replaceWith(n)
      else {
        for (const { name, value } of n.attributes) if (o.getAttribute(name) !== value) o.setAttribute(name, value)
        for (const { name } of [...o.attributes]) if (!n.hasAttribute(name)) o.removeAttribute(name)
        patchNode(o, n)
      }
    }
    for (const o of a.slice(b.length)) o.remove()
  }
  // Collapsed section names live in localStorage; every access can throw (blocked, full, bad JSON).
  const COLLAPSED_KEY = 'cw-dashboard-collapsed'
  const readCollapsed = () => {
    try {
      const list = JSON.parse(localStorage.getItem(COLLAPSED_KEY))
      return new Set(Array.isArray(list) ? list.filter((n) => typeof n === 'string') : [])
    } catch {
      return new Set()
    }
  }
  const writeCollapsed = (names) => {
    try {
      localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...names]))
    } catch {}
  }
  let last = null
  let shownStatus = null
  const shownInfo = new Map()
  const draw = () => {
    if (!last) return
    const now = Date.now()
    drawCharts(document, last, now, patchChart)
    // Rewrite a details body only when its html changed, so a selection inside an open one survives the tick.
    const rows = new Map(last.status.flatMap((g) => g.rows).map((r) => [r.id, r]))
    for (const body of document.querySelectorAll('.info-body[data-ticket]')) {
      const row = rows.get(body.dataset.ticket)
      if (!row) continue
      const html = renderDetails(row, now)
      if (shownInfo.get(row.id) !== html) {
        shownInfo.set(row.id, html)
        body.innerHTML = html
      }
    }
  }
  // The merged list is redrawn only when its html changed (compared with every chart closed, so opening one is not a change), so a poll keeps the page and any selection.
  let mergedPage = 0
  let shownMerged = null
  const drawMerged = () => {
    if (!last) return
    const r = renderMerged(last.merged, mergedPage)
    mergedPage = r.page
    if (r.html !== shownMerged) {
      shownMerged = r.html
      const open = new Set([...document.querySelectorAll('details.chart[data-merged][open]')].map((d) => d.dataset.merged))
      document.getElementById('merged').innerHTML = renderMerged(last.merged, mergedPage, 10, open).html
      draw()
    }
  }
  const seen = versionWatch()
  const poll = async () => {
    const err = document.getElementById('error')
    try {
      const res = await fetch('/api', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      last = await res.json()
      if (last.theme === 'dark' || last.theme === 'light') document.documentElement.dataset.theme = last.theme
      else delete document.documentElement.dataset.theme
      if (seen(last.version)) {
        location.reload()
        return
      }
      err.textContent = last.restartError || ''
      // The status is rebuilt only when it changed, so a copy label, a selection or a click is not lost.
      // Charts count by session id and task count (the pill), so new snapshot numbers alone do not rebuild the cards.
      const json = JSON.stringify(last.status, (k, v) => (k === 'gantt' ? [v.map((s) => s.sessionId), taskCount(v)] : v))
      if (json !== shownStatus) {
        shownStatus = json
        const open = new Set([...document.querySelectorAll('details.chart[data-ticket][open]')].map((d) => d.dataset.ticket))
        const info = new Set([...document.querySelectorAll('details.info[data-ticket][open]')].map((d) => d.dataset.ticket))
        shownInfo.clear()
        document.getElementById('status').innerHTML = renderStatus(last.status, open, readCollapsed(), info)
        document.getElementById('cta').innerHTML = renderBadges(last.status)
      }
      draw()
      drawMerged()
    } catch (e) {
      err.textContent = `Could not refresh: ${e.message}`
    }
  }
  document.addEventListener('click', (ev) => {
    const target = ev.target instanceof Element ? ev.target : null
    const pager = target?.closest('button[data-page]')
    if (pager) {
      mergedPage = Number(pager.dataset.page)
      drawMerged()
      return
    }
    const btn = target?.closest('button[data-copy]')
    if (!btn) return
    const label = btn.textContent
    navigator.clipboard.writeText(btn.dataset.copy).then(
      () => {
        btn.textContent = 'Copied'
        setTimeout(() => { btn.textContent = label }, 1500)
      },
      () => {
        btn.textContent = 'Copy failed'
        setTimeout(() => { btn.textContent = label }, 1500)
      },
    )
  })
  // toggle does not bubble, so listen in the capture phase.
  document.addEventListener(
    'toggle',
    (ev) => {
      const d = ev.target
      if (!(d instanceof Element) || !d.matches('details.group')) return
      const names = readCollapsed()
      if (d.open) names.delete(d.dataset.group)
      else names.add(d.dataset.group)
      writeCollapsed(names)
    },
    true,
  )
  poll()
  setInterval(poll, 5000)
  setInterval(draw, 1000)
}

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

export function renderStatus(groups, open = new Set()) {
  if (!groups || groups.length === 0) return '<p class="quiet">No state yet</p>'
  return groups
    .map((g) => {
      const rows = g.rows
        .map((r) => {
          const copy = r.threadLink
            ? `<button type="button" class="copy" data-copy="${esc(r.threadLink)}">Copy thread link</button>`
            : ''
          return `<li class="ticket">
  <div class="top">
    <span class="id">${link(r.issueUrl, r.id)}</span>
    ${r.stage ? `<span class="badge stage">${esc(r.stage)}</span>` : ''}
    <span class="badge risk${riskClass(r.risk)}">${esc(r.risk)}</span>
    ${r.prUrl ? `<span class="pr">${link(r.prUrl, 'PR')}</span>` : ''}
    ${copy}
  </div>
  ${r.title ? `<div class="title">${esc(r.title)}</div>` : ''}
  ${r.next ? `<div class="next">${esc(r.next)}</div>` : ''}
  ${r.gantt && r.gantt.length ? `<details class="chart" data-ticket="${esc(r.id)}"${open.has(r.id) ? ' open' : ''}><summary>Agents <span class="pill">${esc(r.gantt.length)}</span></summary><div class="chart-body" data-ticket="${esc(r.id)}"></div></details>` : ''}
</li>`
        })
        .join('\n')
      return `<section class="group"><h3>${esc(g.name)} <span class="pill">${esc(g.count)}</span></h3><ul class="cards">${rows}</ul></section>`
    })
    .join('\n')
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
    `<span class="badge">${queue > 0 ? `${plural(queue, 'ticket')} in the build queue` : 'No tickets in the build queue'}</span>`,
  ].join('')
}

const stamp = (ms) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())} ${clock(ms)}`
}

/** One page of the merged list as cards plus a pager. `page` is 0-based and comes back clamped. */
export function renderMerged(list, page, size = 10) {
  if (!list || list.length === 0) return { html: '<p class="quiet">Nothing merged yet</p>', page: 0 }
  const pages = Math.ceil(list.length / size)
  const at = Math.min(Math.max(0, Math.trunc(page) || 0), pages - 1)
  const cards = list
    .slice(at * size, (at + 1) * size)
    .map(
      (e) => `<li class="ticket">
  <div class="top">
    <span class="id">${link(e.issueUrl, e.id)}</span>
    <span class="pr">${link(e.prUrl, 'PR')}</span>
  </div>
  <div class="title">${esc(e.title)}</div>
  <div class="next">merged ${esc(stamp(e.mergedAt))}</div>
</li>`,
    )
    .join('\n')
  const pager =
    pages > 1
      ? `<nav class="pager"><button type="button" data-page="${at - 1}"${at === 0 ? ' disabled' : ''}>Newer</button> <span>Page ${at + 1} of ${pages}</span> <button type="button" data-page="${at + 1}"${at === pages - 1 ? ' disabled' : ''}>Older</button></nav>`
      : ''
  return { html: `<ul class="cards">${cards}</ul>${pager}`, page: at }
}

export function renderGantt(sessions, now) {
  if (!sessions || sessions.length === 0) return '<p class="quiet">No sessions yet</p>'
  return sessions
    .map((s) => {
      const clockNow = s.stale ? s.updatedAt : now
      const endOf = (r) => (r.end === null || r.end === undefined ? clockNow : r.end)
      const t0 = s.rows.length ? Math.min(...s.rows.map((r) => r.start)) : 0
      const t1 = s.rows.length ? Math.max(...s.rows.map(endOf)) : 0
      const span = Math.max(1, t1 - t0)
      const rows = s.rows
        .map((r) => {
          const segments = Array.isArray(r.segments) && r.segments.length ? r.segments : [[r.start, r.end]]
          const bars = segments
            .map(([a, b]) => {
              const open = b === null || b === undefined
              const left = Math.min(99, Math.max(0, ((a - t0) / span) * 100))
              const width = Math.min(100 - left, Math.max(0.5, (((open ? clockNow : b) - a) / span) * 100))
              return `<span class="bar${open && !s.stale ? ' running' : ''}" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%"></span>`
            })
            .join('')
          const running = r.end === null || r.end === undefined
          return `<div class="grow">
  <span class="name" style="padding-left:${Math.max(0, r.depth) * 1.2}em">${esc(r.name)}</span>
  <span class="num cost">${dollars(r.cost)}</span>
  <span class="track">${bars}</span>
  <span class="meta">
    <span class="repo">${esc(r.repo)}</span>
    <span class="num t0">${clock(r.start)}</span>
    <span class="num t1">${running && !s.stale ? 'running' : clock(endOf(r))}</span>
    <span class="num tok">${tokens(r.tokens)}</span>
    <span class="model">${esc(r.model ?? '–')}</span>
    <span class="harness">${esc(r.harness ?? '–')}</span>
  </span>
</div>`
        })
        .join('\n')
      return `<section class="session${s.stale ? ' stale' : ''}">
  <h3>${esc(s.cwd)} <span class="total">${dollars(s.total)}</span>${s.stale ? ' <span class="pill">stale</span>' : ''}</h3>
  <div class="grow head"><span>Agent</span><span>Repo</span><span class="num">Start</span><span class="num">End</span><span class="num">Tokens</span><span class="num">Cost</span><span>Model</span><span>Harness</span><span>Timeline</span></div>
  ${rows}
</section>`
    })
    .join('\n')
}

if (typeof document !== 'undefined') {
  let last = null
  let shownStatus = null
  const draw = () => {
    if (!last) return
    const now = Date.now()
    const rows = new Map(last.status.flatMap((g) => g.rows).map((r) => [r.id, r]))
    for (const body of document.querySelectorAll('.chart-body')) {
      const row = rows.get(body.dataset.ticket)
      if (row) body.innerHTML = renderGantt(row.gantt, now)
    }
  }
  // The merged list is redrawn only when its html changed, so a poll keeps the page and any selection.
  let mergedPage = 0
  let shownMerged = null
  const drawMerged = () => {
    if (!last) return
    const r = renderMerged(last.merged, mergedPage)
    mergedPage = r.page
    if (r.html !== shownMerged) {
      shownMerged = r.html
      document.getElementById('merged').innerHTML = r.html
    }
  }
  const poll = async () => {
    const err = document.getElementById('error')
    try {
      const res = await fetch('/api', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      last = await res.json()
      err.textContent = ''
      // The status is rebuilt only when it changed, so a copy label, a selection or a click is not lost.
      // Charts count by session id, so new snapshot numbers alone do not rebuild the cards.
      const json = JSON.stringify(last.status, (k, v) => (k === 'gantt' ? v.map((s) => s.sessionId) : v))
      if (json !== shownStatus) {
        shownStatus = json
        const open = new Set([...document.querySelectorAll('details.chart[open]')].map((d) => d.dataset.ticket))
        document.getElementById('status').innerHTML = renderStatus(last.status, open)
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
  poll()
  setInterval(poll, 5000)
  setInterval(draw, 1000)
}

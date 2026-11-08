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

export function renderStatus(groups) {
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
</li>`
        })
        .join('\n')
      return `<section class="group"><h3>${esc(g.name)} <span class="pill">${esc(g.count)}</span></h3><ul class="cards">${rows}</ul></section>`
    })
    .join('\n')
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
          const running = r.end === null || r.end === undefined
          const left = Math.min(99, Math.max(0, ((r.start - t0) / span) * 100))
          const width = Math.min(100 - left, Math.max(0.5, ((endOf(r) - r.start) / span) * 100))
          return `<div class="grow">
  <span class="name" style="padding-left:${Math.max(0, r.depth) * 1.2}em">${esc(r.name)}</span>
  <span class="num cost">${dollars(r.cost)}</span>
  <span class="track"><span class="bar${running && !s.stale ? ' running' : ''}" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%"></span></span>
  <span class="meta">
    <span class="repo">${esc(r.repo)}</span>
    <span class="num t0">${clock(r.start)}</span>
    <span class="num t1">${running && !s.stale ? 'running' : clock(endOf(r))}</span>
    <span class="num tok">${tokens(r.tokens)}</span>
    <span class="num kids">${esc(r.childCount)}</span>
  </span>
</div>`
        })
        .join('\n')
      return `<section class="session${s.stale ? ' stale' : ''}">
  <h3>${esc(s.cwd)} <span class="total">${dollars(s.total)}</span>${s.stale ? ' <span class="pill">stale</span>' : ''}</h3>
  <div class="grow head"><span>Agent</span><span>Repo</span><span class="num">Start</span><span class="num">End</span><span class="num">Tokens</span><span class="num">Cost</span><span class="num">Kids</span><span>Timeline</span></div>
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
    document.getElementById('gantt').innerHTML = renderGantt(last.gantt, Date.now())
  }
  const poll = async () => {
    const err = document.getElementById('error')
    try {
      const res = await fetch('/api', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      last = await res.json()
      err.textContent = ''
      // The status is rebuilt only when it changed, so a copy label, a selection or a click is not lost.
      const json = JSON.stringify(last.status)
      if (json !== shownStatus) {
        shownStatus = json
        document.getElementById('status').innerHTML = renderStatus(last.status)
      }
      draw()
    } catch (e) {
      err.textContent = `Could not refresh: ${e.message}`
    }
  }
  document.addEventListener('click', (ev) => {
    const btn = ev.target instanceof Element ? ev.target.closest('button[data-copy]') : null
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

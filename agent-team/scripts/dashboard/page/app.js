// Dashboard page. Pure render functions (tested in Node) plus a browser shell.

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])

const isHttp = (u) => typeof u === 'string' && /^https?:\/\//i.test(u)
const link = (url, label) => (isHttp(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : esc(label))

const two = (n) => String(n).padStart(2, '0')
/** Local 12-hour time: 9:05 am, 12:00 pm. */
export const clock = (ms) => {
  const d = new Date(ms)
  return `${d.getHours() % 12 || 12}:${two(d.getMinutes())} ${d.getHours() < 12 ? 'am' : 'pm'}`
}

const CLOCK_TIME = /(?<![\d:])(\d{1,2}):(\d{2})(?!\d|:)(?:\s?(am|pm)\b)?(?:\s?UTC\b|Z\b)?/gi
/**
 * Each clock time in status text (`3:55am UTC`, `3:53am`, `14:05`), written in UTC by the Chief of Staff, as the viewer's local `h:mm am/pm` with no zone.
 * A time has no date, so it takes the latest moment at or before `now` (plus a minute of clock skew) with that UTC hour and minute.
 * An hour or minute out of range, or digits right before or after (`10:30:00`, an ISO timestamp), leaves the match as it is.
 */
export const localTimes = (text, now = Date.now()) =>
  String(text ?? '').replace(CLOCK_TIME, (match, hh, mm, ap) => {
    let h = Number(hh)
    if (Number(mm) > 59 || (ap ? h > 12 : h > 23)) return match
    if (ap) h = (h % 12) + (ap.toLowerCase() === 'pm' ? 12 : 0)
    const limit = now + 60_000
    const d = new Date(limit)
    let at = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), h, Number(mm))
    if (at > limit) at -= 86_400_000
    return clock(at)
  })
const tokens = (n) => (n >= 999_950 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1e3).toFixed(1)}k` : String(n))
const dollars = (c) => (c === null || c === undefined ? '–' : `$${c.toFixed(2)}`)

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

/** The level word of a risk text, `{ text: 'Low', level: 'low' }`, shown as a pill badge in the level's colour. Text with no readable level comes back as it is with an empty level; an empty risk comes back as null. */
export function riskText(risk) {
  const raw = String(risk ?? '').trim()
  if (!raw) return null
  const w = /^[a-z]+/.exec(raw.toLowerCase())
  return w && ['low', 'medium', 'high'].includes(w[0]) ? { text: `${w[0][0].toUpperCase()}${w[0].slice(1)}`, level: w[0] } : { text: localTimes(raw), level: '' }
}

// Bands are a page-side order over the /api groups. A group name the page does not know goes to In progress.
const NEEDS_YOU = ['Awaiting merge approval', 'Awaiting build approval']
const QUEUED = ['Queued to merge', 'Queued to build', 'Waiting to spec', 'Other']
// The Backlog group is drawn on its own tab by renderBacklog, in no band of the Ship loop tab.
const BACKLOG = 'Backlog'
const BANDS = [
  { name: 'Your turn', slug: 'needs', has: (n) => NEEDS_YOU.includes(n) },
  { name: 'In progress', slug: 'progress', has: (n) => !NEEDS_YOU.includes(n) && !QUEUED.includes(n) && n !== BACKLOG },
  { name: 'Up next', slug: 'queued', flat: true, has: (n) => QUEUED.includes(n) },
]
/** The saved-collapsed key of a top-level section. The colon keeps it apart from every API group name. */
export const bandKey = (slug) => `band:${slug}`
const GROUP_CLASS = new Map([['Awaiting merge approval', ' needs-merge'], ['Awaiting build approval', ' needs-build']])
const STAGE_WORDS = new Map([['blocked', 'blocked'], ['spec-queued', 'spec queued']])

const stageWords = (stage) => STAGE_WORDS.get(stage) ?? stage.replace(/-/g, ' ')

const GROUP_LABELS = new Map([
  ['Awaiting merge approval', 'Ready to merge'],
  ['Awaiting build approval', 'Spec ready to build'],
  ['Awaiting teammate review', 'In review'],
  ['Queued to merge', 'Waiting to merge'],
  ['Speccing', 'Writing the spec'],
  ['Queued to build', 'Waiting to build'],
  ['Other', 'Blocked or waiting'],
])
/** The label shown for an API group name; an unknown name is returned as it is (the caller escapes it). `data-group` keeps the API name. */
export const groupLabel = (name) => GROUP_LABELS.get(name) ?? name

const STAGE_SENTENCES = new Map([
  ['awaiting-merge', 'Waiting for your merge approval'],
  ['awaiting-build', 'Spec is waiting for your approval'],
  ['blocked', 'Blocked. Needs an answer from you'],
  ['awaiting-review', "Waiting for a teammate's review"],
  ['merge', 'Merging now'],
  ['merge-queued', 'Waiting for a merge slot'],
  ['spec', 'Writing the spec'],
  ['spec-queued', 'Waiting for a spec slot'],
  ['build', 'Building'],
  ['build-queued', 'Waiting for a build slot'],
])
/** One plain sentence for where a ticket stands; an unknown stage shows its slug with spaces. */
export const stageSentence = (stage) => {
  const s = String(stage ?? '')
  return STAGE_SENTENCES.get(s) ?? stageWords(s)
}
/** The time since `at` (ms), in words, two units at most: `<1m`, `42m`, `3h 16m`, `3d 4h`. */
function ageWords(at, now) {
  const m = Math.max(0, Math.floor((now - at) / 60_000))
  const units = (big, bigUnit, rest, restUnit) => `${big}${bigUnit}${rest ? ` ${rest}${restUnit}` : ''}`
  if (m < 1) return '<1m'
  if (m < 60) return `${m}m`
  if (m < 1440) return units(Math.floor(m / 60), 'h', m % 60, 'm')
  return units(Math.floor(m / 1440), 'd', Math.floor(m / 60) % 24, 'h')
}

/** `today`, `yesterday` or `YYYY-MM-DD` for a local date; empty for a time that is not a number. */
export function dayWords(ms, now) {
  if (typeof ms !== 'number' || !Number.isFinite(ms)) return ''
  const day = (t) => {
    const d = new Date(t)
    return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  }
  const diff = Math.round((day(now) - day(ms)) / 86_400_000)
  if (diff === 0) return 'today'
  if (diff === 1) return 'yesterday'
  const d = new Date(ms)
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}

const ACTIONS = new Map([
  ['awaiting-merge', ['Open PR', 'prUrl']],
  ['awaiting-build', ['Open spec', 'specUrl']],
])
/** The one action a ticket that needs the user offers, or null when the stage has none or its url is not http(s). */
export function actionFor(r) {
  const a = ACTIONS.get(r?.stage)
  return a && isHttp(r[a[1]]) ? { label: a[0], url: r[a[1]] } : null
}

const list = (x) => (Array.isArray(x) ? x.filter((e) => typeof e === 'object' && e !== null) : [])

const MARKER = /^( *)([-*+]|\d{1,9}[.)])\s+(\S.*)$/

/**
 * Inline markdown for one run of text: code spans, then `[label](url)` links, then bold and italic.
 * Every piece of text goes through esc() before a tag is built around it, and a link goes through link(), so only an http(s) url becomes an anchor.
 */
function inline(raw) {
  const emphasis = (t) =>
    t
      .replace(/\*\*([^*]+)\*\*|__([^_]+)__/g, (_, a, b) => `<strong>${a ?? b}</strong>`)
      .replace(/(^|[^\w*])\*(?=\S)([^*]+?)\*(?![\w*])/g, '$1<em>$2</em>')
      .replace(/(^|[^\w_])_(?=\S)([^_]+?)_(?![\w_])/g, '$1<em>$2</em>')
  const text = String(raw)
  const re = /`([^`]+)`|\[([^\]]+)\]\(([^)\s]*)\)/g
  let out = ''
  let at = 0
  for (let m; (m = re.exec(text)); at = re.lastIndex) {
    out += emphasis(esc(text.slice(at, m.index)))
    out += m[1] !== undefined ? `<code>${esc(m[1])}</code>` : link(m[3], m[2])
  }
  return out + emphasis(esc(text.slice(at)))
}

const listHtml = (l) => {
  const items = (tag, list) => `<${tag}>${list.join('')}</${tag}>`
  return items(l.tag, l.items.map((it) => `<li>${inline(it.text)}${it.sub ? items(it.sub.tag, it.sub.items.map((s) => `<li>${inline(s)}</li>`)) : ''}</li>`))
}

/**
 * Markdown to markup for the spec and PR text, which comes from agents and PR authors. No dependency.
 * Covers headings, bullet and numbered lists (one nested level), fenced code, quotes, paragraphs and `|` tables (shown as preformatted text); the rest shows as plain text.
 */
export function renderMarkdown(text) {
  const lines = String(text ?? '').replace(/\r\n?/g, '\n').replace(/^\t+/gm, (t) => '    '.repeat(t.length)).split('\n')
  const out = []
  let para = []
  let quote = []
  let list = null
  const endText = () => {
    if (para.length) out.push(`<p>${inline(para.join(' '))}</p>`)
    if (quote.length) out.push(`<blockquote>${inline(quote.join(' '))}</blockquote>`)
    para = []
    quote = []
  }
  const endList = () => {
    if (list) out.push(listHtml(list))
    list = null
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const fence = line.match(/^\s*(```|~~~)/)
    const marker = line.match(MARKER)
    if (line.trim() === '') endText()
    else if (marker) {
      const tag = /\d/.test(marker[2]) ? 'ol' : 'ul'
      endText()
      if (list && marker[1].length >= 2) (list.items.at(-1).sub ??= { tag, items: [] }).items.push(marker[3])
      else {
        if (list && list.tag !== tag) endList()
        list ??= { tag, items: [] }
        list.items.push({ text: marker[3], sub: null })
      }
    } else if (list && !fence && /^ {2,}\S/.test(line)) {
      const last = list.items.at(-1)
      if (last.sub) last.sub.items.push(`${last.sub.items.pop()} ${line.trim()}`)
      else last.text += ` ${line.trim()}`
    } else {
      endList()
      const heading = line.match(/^ {0,3}#{1,6}\s+(.*?)(?:\s+#+)?\s*$/)
      const quoted = line.match(/^ {0,3}>\s?(.*)$/)
      const table = /^\s*\|/.test(line)
      if (fence || heading || table) endText()
      if (fence) {
        const code = []
        while (++i < lines.length && !lines[i].trim().startsWith(fence[1])) code.push(lines[i])
        out.push(`<pre><code>${esc(code.join('\n'))}</code></pre>`)
      } else if (heading) out.push(`<p class="md-h">${inline(heading[1])}</p>`)
      else if (table) {
        const rows = [line]
        while (/^\s*\|/.test(lines[i + 1] ?? '')) rows.push(lines[++i])
        out.push(`<pre class="md-table">${esc(rows.join('\n'))}</pre>`)
      } else if (quoted) {
        if (para.length) endText()
        quote.push(quoted[1])
      } else {
        if (quote.length) endText()
        para.push(line.trim())
      }
    }
  }
  endText()
  endList()
  return out.join('')
}

/** What the spec or the PR says. It comes from agents, so the text goes through renderMarkdown, every other string is escaped and only an http(s) url becomes an anchor. */
function renderDetail(d) {
  const sections = list(d?.sections)
  const files = list(d?.files)
  const reviews = list(d?.reviews)
  if (sections.length === 0 && files.length === 0 && reviews.length === 0 && !(d?.moreFiles > 0)) return ''
  const open = isHttp(d.url) ? `<span class="detail-open">${link(d.url, 'Open')}</span>` : ''
  const out = [`<header class="detail-head"><span>${d.kind === 'changes' ? 'Changes' : 'Spec'}</span>${open}</header>`]
  for (const s of sections) out.push(`<div class="detail-block"><h4>${esc(s.name)}</h4><div class="detail-section">${renderMarkdown(s.text)}</div></div>`)
  if (reviews.length) out.push(`<div class="detail-reviews">${reviews.map((v) => `<span class="badge ${v.verdict === 'PASS' ? 'pass' : 'fail'}">${link(v.url, `${v.name} ${v.verdict}`)}</span>`).join('')}</div>`)
  if (files.length || d.moreFiles > 0) {
    const rows = files.map((f) => `<span class="path">${esc(f.path)}</span><span class="delta"><span class="add">+${esc(Number(f.add) || 0)}</span> <span class="del">−${esc(Number(f.del) || 0)}</span></span>`)
    const more = d.moreFiles > 0 ? `<p class="detail-more">and ${esc(d.moreFiles)} more ${d.moreFiles === 1 ? 'file' : 'files'}</p>` : ''
    out.push(`<div class="detail-block"><h4>Files (${files.length + (d.moreFiles > 0 ? d.moreFiles : 0)})</h4><div class="detail-files">${rows.join('')}</div>${more}</div>`)
  }
  return `<section class="detail">${out.join('')}</section>`
}

/** The `Details` body: the thread link, the ticket and usage facts, then the spec or PR text. Each part is left out when empty; with none, one quiet line. */
export function renderDetails(r, now) {
  const ticketFacts = []
  if (r.stage) ticketFacts.push(['Stage', esc(stageWords(r.stage))])
  if (r.risk) ticketFacts.push(['Risk', esc(localTimes(r.risk))])
  if (r.next) ticketFacts.push(['Next', esc(localTimes(r.next)), 'wide'])
  const usage = []
  if (r.gantt && r.gantt.length > 0) {
    const items = ganttTasks(r.gantt, now)
    const drawn = items.flatMap((i) => [i, ...i.kids])
    const subagents = drawn.filter((d) => d.r.kind === 'agent').length
    const agents = [plural(r.gantt.length, 'session'), items.length ? plural(items.length, 'task') : '', subagents ? plural(subagents, 'subagent') : '']
    usage.push(['Agents', esc(agents.filter(Boolean).join(', '))])
    usage.push(['Tokens', esc(tokens(drawn.reduce((n, d) => n + (d.r.tokens || 0), 0)))])
    const cost = ganttCost(items)
    if (typeof cost === 'number') usage.push(['Cost', esc(dollars(cost))])
    const newest = r.gantt.reduce((a, s) => (s.updatedAt > a.updatedAt ? s : a))
    usage.push(['Last update', esc(`${stamp(newest.updatedAt)}${newest.stale ? ' (stale)' : ''}`)])
  }
  const grid = (facts) => (facts.length ? `<dl class="info-grid">${facts.map(([k, v, cls]) => `<div${cls ? ` class="${cls}"` : ''}><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>` : '')
  const facts = grid(ticketFacts) + grid(usage)
  const html = (r.threadLink ? `<p class="info-links"><code>${esc(r.threadLink)}</code></p>` : '') + (facts ? `<div class="info-facts">${facts}</div>` : '') + renderDetail(r.detail)
  return html || '<p class="quiet">Nothing more known yet</p>'
}

/** The copy glyph: two overlapping rounded rectangles, drawn in the button's text color. */
const COPY_ICON = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5v-.5A1.5 1.5 0 0 0 9 1.5H3A1.5 1.5 0 0 0 1.5 3v6A1.5 1.5 0 0 0 3 10.5h.5"/></svg>'

/** The thread glyph: a speech bubble, drawn before the copy glyph on a ticket card so the button reads as the thread's link. */
const THREAD_ICON = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2.5 3.5A1.5 1.5 0 0 1 4 2h8a1.5 1.5 0 0 1 1.5 1.5v6A1.5 1.5 0 0 1 12 11H7l-3 2.5V11A1.5 1.5 0 0 1 2.5 9.5z"/></svg>'

const copyButton = (l, { thread = false } = {}) => (l ? `<button type="button" class="copy-icon${thread ? ' with-thread' : ''}" data-copy="${esc(l)}" aria-label="Copy thread link" title="Copy thread link">${thread ? THREAD_ICON : ''}${COPY_ICON}</button>` : '')
const viewOf = (id, open, info) => (open.has(id) ? 'agents' : info.has(id) ? 'details' : '')

/**
 * The Agents and Details control of one row and the panels it opens. `scope` is `ticket`, `merged` or `pm`; `view` is `agents`, `details` or `` (closed).
 * `details` is the Details body html, `null` for a disabled Details segment, `false` for none. Agents is disabled (`Agents 0`) with no panel when the Gantt has no tasks.
 * One panel is open at most; a view whose segment is disabled comes back closed.
 */
function panelSwitch(scope, id, { gantt, view = '', details = false }) {
  const n = gantt ? taskCount(gantt) : 0
  const attr = `data-${scope}="${esc(id)}"`
  const segs = [{ v: 'agents', label: `Agents <span class="pill">${n}</span>`, body: n ? `<div class="chart-body" ${attr}></div>` : null, off: 'No agent sessions recorded' }]
  if (details !== false) segs.push({ v: 'details', label: 'Details', body: details === null ? null : `<div class="info-body" ${attr}>${details}</div>`, off: 'No ticket yet' })
  const shown = segs.find((s) => s.v === view && s.body !== null)?.v
  const key = (s) => esc(`${scope}-${id}-${s.v}`)
  const buttons = segs.map((s) => `<button type="button" class="seg" ${attr} data-view="${s.v}" id="seg-${key(s)}" aria-expanded="${s.v === shown}"${s.body === null ? ` disabled title="${s.off}"` : ` aria-controls="pan-${key(s)}"`}>${s.label}</button>`)
  const panels = segs.filter((s) => s.body !== null).map((s) => `<div class="panel" id="pan-${key(s)}" role="region" aria-labelledby="seg-${key(s)}"${s.v === shown ? '' : ' hidden'}>${s.body}</div>`)
  return { control: `<div class="switch" role="group" aria-label="${esc(id)} panels">${buttons.join('')}</div>`, panels: panels.join('') }
}
const prSpan = (url) => (isHttp(url) ? `<span class="pr">${link(url, 'PR')}</span>` : '')
const specSpan = (url) => (isHttp(url) ? `<span class="spec">${link(url, 'Spec')}</span>` : '')
/** The first line of every row: the ticket number, then the title (left out when empty, so the id is not shown twice), then `extra`. */
const rowHead = (idHtml, title, extra = '') => `<div class="head"><span class="id">${idHtml}</span>${title ? `<span class="title">${esc(title)}</span>` : ''}${extra}</div>`
const metaLine = (parts) => parts.filter(Boolean).join(' \u00b7 ')

/** `41m 05s · $2.10` from the Gantt data; parts that are missing are left out, and nothing without a Gantt. */
export const summaryLine = (gantt, now) => {
  const g = ganttSummary(gantt, now)
  if (!g) return ''
  return metaLine([duration(g.ms), typeof g.cost === 'number' ? dollars(g.cost) : ''])
}

/** `approve 402` (or `changes 402: ` with `kind` `changes`) for a ticket waiting on the user to approve a merge or a build; null for any other stage or an id with no number. */
export function approveCommand(r, kind = 'approve') {
  if (r?.stage !== 'awaiting-merge' && r?.stage !== 'awaiting-build') return null
  const n = /-(\d+)$/.exec(String(r.id))?.[1]
  return n ? (kind === 'changes' ? `changes ${n}: ` : `approve ${n}`) : null
}

const THREAD_LINK = /^<t3-thread:\/\/v2\/([A-Za-z0-9:._%-]+)\/([A-Za-z0-9:._%-]+)>$/

/** `t3code://threads/ENV/THREAD?prompt=TEXT`, which T3 opens as an unsent draft in that thread; built from the dashboard's `<t3-thread://v2/ENV/THREAD>` link. Null when the link is missing or not that shape. */
export function promptLink(chiefLink, text) {
  const m = typeof chiefLink === 'string' ? THREAD_LINK.exec(chiefLink) : null
  return m ? `t3code://threads/${m[1]}/${m[2]}?prompt=${encodeURIComponent(text)}` : null
}

/** The Approve and Changes controls: a link that opens the Chief of Staff thread with the command typed in, or, with no thread link, a button that copies the command. */
function approveControls(r, chiefLink) {
  return [['approve', 'Approve'], ['changes', 'Changes']]
    .map(([kind, label]) => {
      const text = approveCommand(r, kind)
      if (text === null) return ''
      const href = promptLink(chiefLink, text)
      return href ? `<a class="approve" href="${esc(href)}">${label}</a>` : `<button type="button" class="approve" data-copy="${esc(text)}">${label}</button>`
    })
    .join('')
}

/** `mark 419 todo` for a Backlog ticket; null for an id with no trailing number. */
export function todoCommand(r) {
  const n = /-(\d+)$/.exec(String(r?.id))?.[1]
  return n ? `mark ${n} todo` : null
}

/** The Mark todo control: a link that opens the Chief of Staff thread with the command typed in, or, with no usable thread link, a button that copies it; empty with no ticket number. */
function todoControl(r, chiefLink) {
  const text = todoCommand(r)
  if (text === null) return ''
  const href = promptLink(chiefLink, text)
  return href ? `<a class="todo" href="${esc(href)}">Mark todo</a>` : `<button type="button" class="todo" data-copy="${esc(text)}">Mark todo</button>`
}

/**
 * One ticket as a card (`li.ticket`), the same three rows for every card. Classes: `attn` (Your turn), `compact` (a flat row that is not blocked), `blocked` (a blocked flat row).
 * Top row: the ticket number, the title and the thread copy button. Middle row (only when it has something): the `Open PR` or `Open spec` link and the Approve and Changes controls.
 * Bottom row: the Agents and Details control, the Mark todo control (`markTodo`, the Backlog tab only), then one meta line: risk badge, `Spec`, `PR`, time and cost, and (in the Waiting to spec or Other group) the stage in words. A Todo row has no risk or stage.
 * A running ticket helper (`helper: true`) is a placeholder: `Ticket helper` for the id, the request for the title, the copy button and the chart, no issue link and a disabled Details.
 */
function ticket(r, { flat, attn, group, open, info, chiefLink, markTodo = false }) {
  const blocked = r.stage === 'blocked'
  const risk = riskText(r.risk)
  const action = actionFor(r)
  const compact = flat && !blocked
  const phrase = r.stage && (group === 'Waiting to spec' || group === 'Other') ? stageSentence(r.stage) : ''
  const summary = summaryLine(r.gantt, Date.now())
  const meta = metaLine([
    risk && (risk.level ? `<span class="badge risk risk-${risk.level}">${esc(risk.text)}</span>` : `<span class="risk-none">${esc(risk.text)}</span>`),
    r.helper ? '' : specSpan(r.specUrl),
    r.helper ? '' : prSpan(r.prUrl),
    summary && `<span class="summary" data-ticket="${esc(r.id)}">${esc(summary)}</span>`,
    phrase && esc(phrase),
  ])
  const sw = panelSwitch('ticket', r.id, { gantt: r.gantt, view: viewOf(r.id, open, info), details: r.helper ? null : renderDetails(r, Date.now()) })
  const cls = `ticket${attn ? ' attn' : ''}${compact ? ' compact' : ''}${blocked && flat ? ' blocked' : ''}${r.stale ? ' stale' : ''}`
  const head = rowHead(r.helper ? 'Ticket helper' : link(r.issueUrl, r.id), r.title, copyButton(r.threadLink, { thread: true }))
  const actions = (action ? `<a class="action" href="${esc(action.url)}" target="_blank" rel="noopener noreferrer">${esc(action.label)}</a>` : '') + approveControls(r, chiefLink)
  return `<li class="${cls}">\n  ${head}\n  ${actions ? `<div class="actions">${actions}</div>\n  ` : ''}<div class="foot">${sw.control}${markTodo ? todoControl(r, chiefLink) : ''}<span class="meta">${meta}</span></div>${sw.panels}\n</li>`
}

/** Page count and the clamped 0-based page `at` for a list of `length` rows; a non-number page is 0. */
export function pageOf(length, page, size) {
  const pages = Math.max(1, Math.ceil(length / size))
  return { at: Math.min(Math.max(0, Math.trunc(page) || 0), pages - 1), pages }
}

const BACKLOG_PAGE = 10

/** `open` holds the ids of tickets whose `Agents` panel is open, `info` those whose `Details` is open (Agents wins when an id is in both). `chiefLink` is the Chief of Staff thread link the Approve controls open. The Backlog group is not drawn here; `renderBacklog` draws it on its own tab. */
export function renderStatus(groups, open = new Set(), collapsed = new Set(), info = new Set(), chiefLink = '') {
  if (!groups || groups.length === 0) return '<p class="quiet">No state yet</p>'
  const html = BANDS.map((band) => {
    const mine = groups.filter((g) => band.has(g.name))
    if (mine.length === 0) return ''
    const flat = band.flat === true
    const sections = mine
      .map((g) => {
        const rows = g.rows.map((r) => ticket(r, { flat, attn: band.slug === 'needs', group: g.name, open, info, chiefLink })).join('\n')
        // A Todo list read from the tracker over an hour ago says how old it is; its rows carry `stale` and grey themselves.
        const age = g.stale === true && Number.isFinite(g.readAt) ? `<p class="read-age">Read from the tracker ${esc(ageWords(g.readAt, Date.now()))} ago</p>` : ''
        return `<details class="group${GROUP_CLASS.get(g.name) ?? ''}" data-group="${esc(g.name)}"${collapsed.has(g.name) ? '' : ' open'}><summary><h3>${esc(groupLabel(g.name))} <span class="pill">${esc(g.count)}</span></h3></summary>${age}<ul class="cards">${rows}</ul></details>`
      })
      .join('\n')
    const key = bandKey(band.slug)
    return `<details class="band band-${band.slug}" data-band="${key}"${collapsed.has(key) ? '' : ' open'}><summary class="band-head"><h2>${band.name}</h2></summary>${sections}</details>`
  }).filter(Boolean).join('\n')
  // Only the Backlog group, which has its own tab: nothing to draw here.
  return html || '<p class="quiet">No state yet</p>'
}

/** The Backlog tab: the `Backlog` group drawn 10 rows at a time with a pager, its read-age note when the saved list is old, and the Full backlog link; `backlogPage` is the 0-based page; `open`, `info` and `chiefLink` are as in `renderStatus`; each card gets a Mark todo control. */
export function renderBacklog(groups, collapsed = new Set(), backlogPage = 0, open = new Set(), info = new Set(), chiefLink = '') {
  const g = list(groups).find((x) => x.name === BACKLOG)
  if (!g) return '<p class="quiet">Nothing in the Backlog</p>'
  const { at, pages } = pageOf(g.rows.length, backlogPage, BACKLOG_PAGE)
  const rows = g.rows.slice(at * BACKLOG_PAGE, (at + 1) * BACKLOG_PAGE).map((r) => ticket(r, { flat: true, attn: false, group: g.name, open, info, chiefLink, markTodo: true })).join('\n')
  const pager =
    pages > 1
      ? `<nav class="pager"><button type="button" data-backlog-page="${at - 1}"${at === 0 ? ' disabled' : ''}>Previous</button> <span>Page ${at + 1} of ${pages}</span> <button type="button" data-backlog-page="${at + 1}"${at === pages - 1 ? ' disabled' : ''}>Next</button></nav>`
      : ''
  // A saved Backlog list read from the tracker over an hour ago says how old it is and greys its rows.
  const stale = g.stale === true && Number.isFinite(g.readAt)
  const age = stale ? `<p class="read-age">Read from the tracker ${esc(ageWords(g.readAt, Date.now()))} ago</p>` : ''
  return `<details class="group${stale ? ' stale' : ''}" data-group="${esc(g.name)}"${collapsed.has(g.name) ? '' : ' open'}><summary><h3>${esc(groupLabel(g.name))} <span class="pill">${esc(g.count)}</span></h3></summary>${age}<ul class="cards">${rows}</ul>${pager}${isHttp(g.moreUrl) ? `<p class="more">${link(g.moreUrl, 'Full backlog')}</p>` : ''}</details>`
}

/** The sum of the group `count`s that fall in `band`; a count that is not a number is 0. */
const bandSum = (groups, band) => groups.filter((g) => band.has(g.name)).reduce((n, g) => n + (Number(g.count) || 0), 0)

/** Ticket counts for the tab labels: `ship` sums group `count` over the Your turn, In progress and Up next bands, `done` is the merged list length, `backlog` is the Backlog group's `count` (0 when missing or not a number). */
export function tabCounts(status, merged) {
  const groups = Array.isArray(status) ? status : []
  return { ship: BANDS.slice(0, 3).reduce((n, band) => n + bandSum(groups, band), 0), done: Array.isArray(merged) ? merged.length : 0, backlog: bandSum(groups, new Set([BACKLOG])) }
}

/** The header: one sentence counting the bands (the Backlog is not counted). A blocked ticket (stage `blocked`) is counted apart from the waiting ones. */
export function renderBadges(groups) {
  if (!Array.isArray(groups)) return ''
  const sum = (band) => bandSum(groups, band)
  const [needs, progress, queued] = BANDS
  const blocked = groups.filter((g) => queued.has(g.name)).flatMap((g) => list(g.rows)).filter((r) => r.stage === 'blocked').length
  const need = sum(needs)
  const waiting = Math.max(0, sum(queued) - blocked)
  const parts = [need > 0 ? `<span class="hs-need">${need} ${need === 1 ? 'needs' : 'need'} you</span>` : 'Nothing needs you']
  if (sum(progress) > 0) parts.push(`${sum(progress)} in progress`)
  if (waiting > 0) parts.push(`${waiting} waiting`)
  if (blocked > 0) parts.push(`<span class="hs-blocked">${blocked} blocked</span>`)
  return `<span class="hs">${parts.join(' \u00b7 ')}</span>`
}

const stamp = (ms) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())} ${clock(ms)}`
}

/** One page of the merged list as compact cards plus a pager. `page` is 0-based and comes back clamped; `open` holds the ids of merged Agents panels to keep open, `info` those of Details panels (whose body is filled here only when open, else by the shell). */
export function renderMerged(list, page, size = 10, open = new Set(), info = new Set()) {
  if (!list || list.length === 0) return { html: '<p class="quiet">Nothing merged yet</p>', page: 0 }
  const { at, pages } = pageOf(list.length, page, size)
  const rows = list
    .slice(at * size, (at + 1) * size)
    .map((e) => {
      const day = dayWords(e.mergedAt, Date.now())
      const meta = metaLine([
        day && esc(`merged ${day} ${clock(e.mergedAt)}`),
        typeof e.spend?.cost === 'number' && esc(dollars(e.spend.cost)),
        e.spend && esc(`${tokens(e.spend.tokens)} tokens`),
        specSpan(e.specUrl),
        prSpan(e.prUrl),
      ])
      const view = viewOf(e.id, open, info)
      const sw = panelSwitch('merged', e.id, { gantt: e.gantt, view, details: view === 'details' ? renderDetails(e, Date.now()) : '' })
      return `<li class="ticket compact">
  ${rowHead(link(e.issueUrl, e.id), e.title)}
  <div class="foot">${sw.control}<span class="meta">${meta}</span></div>${sw.panels}
</li>`
    })
    .join('\n')
  const pager =
    pages > 1
      ? `<nav class="pager"><button type="button" data-page="${at - 1}"${at === 0 ? ' disabled' : ''}>Newer</button> <span>Page ${at + 1} of ${pages}</span> <button type="button" data-page="${at + 1}"${at === pages - 1 ? ' disabled' : ''}>Older</button></nav>`
      : ''
  return { html: `<ul class="cards">${rows}</ul>${pager}`, page: at }
}

const ROLE_LABELS = new Map([['ranking', 'Backlog ranking'], ['hygiene', 'Hygiene']])
const STATES = ['running', 'idle', 'paused', 'finished']
/** The state as a coloured dot (drawn in CSS) and its word. */
const stateBadge = (state) => `<span class="state state-${STATES.includes(state) ? state : 'idle'}">${esc(state)}</span>`

/** One page of project manager thread rows with a pager. */
function teamList(rows, page, size, open, empty) {
  const { at, pages } = pageOf(rows.length, page, size)
  const items = rows
    .slice(at * size, (at + 1) * size)
    .map((p) => {
      const updated = list(p.gantt)[0]?.updatedAt
      const sw = panelSwitch('pm', p.sessionId, { gantt: list(p.gantt), view: open.has(p.sessionId) ? 'agents' : '' })
      return `<li class="ticket compact">
  <div class="head"><span class="title">${esc(ROLE_LABELS.get(p.role) ?? p.role)}</span>${copyButton(p.threadLink)}</div>
  <div class="foot">${sw.control}<span class="meta">${stateBadge(p.state)}${typeof updated === 'number' ? ` \u00b7 ${esc(`updated ${dayWords(updated, Date.now())} ${clock(updated)}`)}` : ''}</span></div>${sw.panels}
</li>`
    })
    .join('\n')
  const pager =
    pages > 1
      ? `<nav class="pager"><button type="button" data-pm-page="${at - 1}"${at === 0 ? ' disabled' : ''}>Newer</button> <span>Page ${at + 1} of ${pages}</span> <button type="button" data-pm-page="${at + 1}"${at === pages - 1 ? ' disabled' : ''}>Older</button></nav>`
      : ''
  return { html: rows.length ? `<ul class="cards">${items}</ul>${pager}` : `<p class="quiet">${empty}</p>`, page: at }
}

/** The Chief of Staff tab: the Chief of Staff card, then one page of project manager threads with a pager. `page` is 0-based and comes back clamped; `open` holds the session ids whose chart is open. */
export function renderChief(api, page = 0, open = new Set(), size = 10, collapsed = new Set()) {
  const chief = api?.chief ?? {}
  const body = list(chief.gantt).length > 0 ? '<div class="chart-body" data-chief></div>' : '<p class="quiet">No Chief of Staff session in the last 24 hours.</p>'
  const card = `<section class="cos-card"><div class="head"><span class="title">Chief of Staff</span>${copyButton(chief.threadLink)}</div><div class="meta">${stateBadge(chief.state ?? 'idle')}</div>${body}</section>`
  const pm = teamList(list(api?.pm), page, size, open, 'No project manager threads yet.')
  const key = bandKey('pm')
  return { html: `${card}<details class="band band-pm" data-band="${key}"${collapsed.has(key) ? '' : ' open'}><summary class="band-head"><h2>Project manager</h2></summary>${pm.html}</details>`, page: pm.page }
}

/** The tab to open from the saved value: `cos`, `done` or `backlog`, else `ship` for anything unknown or missing. */
export const tabFromStorage = (value) => (value === 'cos' || value === 'done' || value === 'backlog' ? value : 'ship')

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

/** How many agents the chart draws (tasks and their subagents), for the `Agents` pill. */
export const taskCount = (sessions) => ganttTasks(sessions, 0).reduce((n, i) => n + 1 + i.kids.length, 0)

/** The bar categories in legend order. */
export const CATEGORIES = [
  ['planning', 'Planning'],
  ['building', 'Building'],
  ['review', 'Review'],
  ['docs', 'Docs and cleanup'],
  ['ci', 'CI wait'],
  ['merge', 'Merge and ship'],
  ['other', 'Other'],
]
const CATEGORY_LABEL = new Map(CATEGORIES)

// First match wins, so a name that mentions a PR can still be review or docs work, and a plan can still be built.
const CATEGORY_RULES = [
  ['review', /\b(?:review|security|changes)\b|^fix\b/i],
  ['docs', /\b(?:docs?|documenter|compact|compacter|slop|cleanup)\b/i],
  ['building', /\b(?:build|implement|implementer|code)\b/i],
  ['merge', /\b(?:merge|open-pr|pr|ship|autopilot)\b/i],
  ['planning', /\b(?:spec|kickoff|tickets?|plan|chief of staff|approve|start|take over|status|backlog|ranking|hygiene|explore|research|general-purpose)\b/i],
]

/**
 * The category key for a row name, from the start of the name: a stage row's name is cut before its ticket id's colon (`Spec CW-385: title` reads `Spec CW-385`), so title words never pick it.
 * A non-string or an unmatched name is `other`. CI bars are `ci` without asking.
 */
export function barCategory(name) {
  if (typeof name !== 'string') return 'other'
  const lead = /^(.*?\b[A-Z][A-Z0-9]*-\d+)\s*:/.exec(name.trim())?.[1] ?? name.trim()
  return CATEGORY_RULES.find(([, re]) => re.test(lead))?.[0] ?? 'other'
}

const rowTitle = ({ r, s, clockNow }) => {
  const running = (r.end === null || r.end === undefined) && !s.stale
  const range = running ? `${clock(r.start)}, running` : `${clock(r.start)} to ${clock(r.end ?? clockNow)}`
  const meta = [r.repo, range, `${tokens(r.tokens)} tokens`, r.model, r.harness].filter((p) => p !== null && p !== undefined && p !== '')
  return [r.name, meta.join(' · '), s.cwd].join('\n')
}

/** The PR's CI spans [start, end, open] with an open end running to `now`; bad entries are dropped. */
const ciSpansOf = (ci, now) =>
  (Array.isArray(ci) ? ci : [])
    .filter((p) => Array.isArray(p) && Number.isFinite(p[0]))
    .map(([a, b]) => [a, b === null || b === undefined ? Math.max(a, now) : b, b === null || b === undefined])

/**
 * For each CI span [start, end, open], the index in `items` of the top-level task that waited for it: the one whose latest finished working span ends at or before the span's start (ties to the earlier task, so the earliest index).
 * Only a task's own spans count, not its subagents', and a span still running does not (a stale session's open span is closed at its last update, so it does). With no such task the earliest one (index 0) owns the span.
 */
export const ciOwner = (items, spans) =>
  spans.map(([start]) => {
    let owner = 0
    let latest = -Infinity
    items.forEach((i, n) => {
      for (const [, end, open] of i.spans) {
        if ((!open || i.s?.stale) && end <= start && end > latest) [owner, latest] = [n, end]
      }
    })
    return owner
  })

const activeSpans = (items) => union(items.flatMap((i) => [...i.spans, ...i.kids.flatMap((k) => k.spans)]))

/** What a card's footer says about its sessions: the active time and the cost (null when any row is unpriced); null when nothing is drawn. */
export function ganttSummary(sessions, now) {
  const items = ganttTasks(sessions, now)
  if (items.length === 0) return null
  return { ms: activeSpans(items).reduce((n, [a, b]) => n + (b - a), 0), cost: ganttCost(items) }
}

export function renderGantt(sessions, now, ci) {
  if (!sessions || sessions.length === 0) return '<p class="quiet">No sessions yet</p>'
  const items = ganttTasks(sessions, now)
  if (items.length === 0) return '<p class="quiet">No tasks yet</p>'
  const ciSpans = ciSpansOf(ci, now)
  // The axis is active time: the union of every working span and CI span, so a time maps to the axis ms before it and gaps with neither take no width. The total counts working spans only.
  const active = activeSpans(items)
  const total = active.reduce((n, [a, b]) => n + (b - a), 0)
  const axis = ciSpans.length ? union([...active, ...ciSpans]) : active
  const scale = Math.max(1, axis.reduce((n, [a, b]) => n + (b - a), 0))
  const pos = (t) => {
    let before = 0
    for (const [a, b] of axis) {
      if (t >= b) before += b - a
      else {
        if (t > a) before += t - a
        break
      }
    }
    return before
  }
  const place = (a, b) => {
    const left = Math.min(99, (pos(a) / scale) * 100)
    return { left, width: Math.min(100 - left, Math.max(0.5, ((pos(b) - pos(a)) / scale) * 100)) }
  }
  const owners = ciOwner(items, ciSpans)
  const drawn = new Set()
  // A task's CI wait: its CI spans merged, one bar each, drawn before its working bars so work done during the wait stays on top.
  const ciBars = (n) =>
    union(ciSpans.filter((_, k) => owners[k] === n))
      .map(([a, b, open]) => {
        const { left, width } = place(a, b)
        const tip = esc(`CI wait\n${open ? `${clock(a)}, running` : `${clock(a)} to ${clock(b)}`} · ${duration(b - a)}`)
        drawn.add('ci')
        return `<span class="bar cat-ci" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%" title="${tip}"></span>`
      })
      .join('')
  const bars = (row, spans) => {
    const cat = barCategory(row.r.name)
    return union(spans)
      .map(([a, b, open]) => {
        const { left, width } = place(a, b)
        const running = open && !row.s.stale
        const range = running ? `${clock(a)}, running` : `${clock(a)} to ${clock(b)}`
        const meta = [range, running ? '' : duration(b - a), row.r.model].filter((p) => p !== null && p !== undefined && p !== '')
        const title = esc(`${row.r.name}\n${[CATEGORY_LABEL.get(cat), ...meta].join(' · ')}`)
        drawn.add(cat)
        return `<span class="bar cat-${cat}${running ? ' running' : ''}" style="left:${left.toFixed(2)}%;width:${width.toFixed(2)}%" title="${title}"></span>`
      })
      .join('')
  }
  const length = (spans) => union(spans).reduce((n, [a, b]) => n + (b - a), 0)
  const line = (row, spans, cost, depth, ci = '') => `<div class="grow${depth > 0 ? ' sub' : ''}${row.s.stale ? ' stale' : ''}" title="${esc(rowTitle(row))}">
  <span class="name" style="padding-left:${depth * 1.2}em">${esc(row.r.name)}${row.s.stale ? ' <span class="pill">stale</span>' : ''}</span>
  <span class="track">${ci}${bars(row, spans)}</span>
  <span class="num dur">${duration(length(spans))}</span>
  <span class="num cost">${dollars(cost)}</span>
</div>`
  const rows = items.map((i, n) => {
    return [line(i, i.spans, itemCost(i), 0, ciBars(n)), ...i.kids.map((k) => line(k, k.spans, k.r.cost, Math.max(1, k.r.depth - i.r.depth)))].join('\n')
  })
  const legend = CATEGORIES.filter(([key]) => drawn.has(key))
  const legendHtml = legend.length ? `\n<ul class="legend" aria-label="Bar colors">${legend.map(([key, label]) => `<li><span class="swatch cat-${key}"></span>${label}</li>`).join('')}</ul>` : ''
  const sum = ganttCost(items)
  const reported = sessions.every((s) => typeof s.total === 'number') ? sessions.reduce((n, s) => n + s.total, 0) : null
  const note =
    sum !== null && reported !== null && Math.abs(reported - sum) >= 0.01 - 1e-9
      ? `<p class="gnote">Claude Code reports ${dollars(reported)} for these sessions. Row costs use prices.json.</p>`
      : ''
  const isOld = sessions.some((s) => s.pricing !== 2)
  const oldNote = isOld ? '<p class="gnote">Some rows were priced before the token rate fix and keep their old costs.</p>' : ''
  return `<div class="gantt">
${rows.join('\n')}
<div class="grow gtotal"><span class="name">Total</span><span class="num dur">${duration(total)}</span><span class="num cost">${dollars(sum)}</span></div>
${note}
${oldNote}${legendHtml}
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
    const html = renderGantt(entry.gantt, now, entry.ci)
    if (shownCharts.get(body) === html) return
    apply(body, html)
    shownCharts.set(body, html)
  }
  for (const body of root.querySelectorAll('.chart-body[data-ticket]')) draw(body, rows.get(body.dataset.ticket))
  for (const body of root.querySelectorAll('.chart-body[data-merged]')) draw(body, merged.get(body.dataset.merged))
  const pm = new Map((Array.isArray(data.pm) ? data.pm : []).map((p) => [p.sessionId, p]))
  for (const body of root.querySelectorAll('.chart-body[data-pm]')) draw(body, pm.get(body.dataset.pm))
  for (const body of root.querySelectorAll('.chart-body[data-chief]')) draw(body, data.chief)
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
  let backlogPage = 0
  const shownInfo = new Map()
  const shownMergedInfo = new Map()
  const draw = () => {
    if (!last) return
    const now = Date.now()
    drawCharts(document, last, now, patchChart)
    // Rewrite a details body only when its html changed, so a selection inside an open one survives the tick.
    const rows = new Map(last.status.flatMap((g) => g.rows).map((r) => [r.id, r]))
    const fill = (selector, entries, shown) => {
      for (const body of document.querySelectorAll(selector)) {
        const entry = entries.get(body.dataset.ticket ?? body.dataset.merged)
        if (!entry) continue
        const html = renderDetails(entry, now)
        if (shown.get(entry.id) !== html) {
          shown.set(entry.id, html)
          body.innerHTML = html
        }
      }
    }
    fill('.info-body[data-ticket]', rows, shownInfo)
    // The footer summary counts time and cost up to now, and the card is not rebuilt when only those numbers move, so refresh its text here.
    for (const span of document.querySelectorAll('.summary[data-ticket]')) {
      const text = summaryLine(rows.get(span.dataset.ticket)?.gantt, now)
      if (text && span.textContent !== text) span.textContent = text
    }
    fill('.info-body[data-merged]', new Map(last.merged.map((e) => [e.id, e])), shownMergedInfo)
  }
  // The merged list is redrawn only when its html changed (compared with every chart and Details closed, so opening one is not a change), so a poll keeps the page and any selection.
  let mergedPage = 0
  let shownMerged = null
  const drawMerged = () => {
    if (!last) return
    const r = renderMerged(last.merged, mergedPage)
    mergedPage = r.page
    if (r.html !== shownMerged) {
      shownMerged = r.html
      const opened = (view) => new Set([...document.querySelectorAll(`.seg[data-merged][data-view="${view}"][aria-expanded="true"]`)].map((d) => d.dataset.merged))
      shownMergedInfo.clear()
      document.getElementById('merged').innerHTML = renderMerged(last.merged, mergedPage, 10, opened('agents'), opened('details')).html
      draw()
    }
  }
  // Same for the Chief of Staff tab: redrawn only when its html changed with every chart closed.
  let pmPage = 0
  let shownCos = null
  const drawCos = () => {
    if (!last) return
    const collapsed = readCollapsed()
    const r = renderChief(last, pmPage, new Set(), 10, collapsed)
    pmPage = r.page
    if (r.html === shownCos) return
    shownCos = r.html
    const opened = new Set([...document.querySelectorAll('.seg[data-pm][data-view="agents"][aria-expanded="true"]')].map((d) => d.dataset.pm))
    document.getElementById('cos').innerHTML = renderChief(last, pmPage, opened, 10, collapsed).html
    draw()
  }
  const TAB_KEY = 'dashboard-tab'
  const tabs = [...document.querySelectorAll('button[role="tab"]')]
  const selectTab = (name, { save = true, focus = false } = {}) => {
    for (const tab of tabs) {
      const on = tab.dataset.tab === name
      tab.setAttribute('aria-selected', String(on))
      tab.tabIndex = on ? 0 : -1
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !on
      if (on && focus) tab.focus()
    }
    if (!save) return
    try {
      localStorage.setItem(TAB_KEY, name)
    } catch {}
  }
  let saved = null
  try {
    saved = localStorage.getItem(TAB_KEY)
  } catch {}
  selectTab(tabFromStorage(saved), { save: false })
  document.querySelector('.tabs').addEventListener('keydown', (ev) => {
    const at = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true')
    const to = { ArrowLeft: (at + tabs.length - 1) % tabs.length, ArrowRight: (at + 1) % tabs.length, Home: 0, End: tabs.length - 1 }[ev.key]
    if (to === undefined) return
    ev.preventDefault()
    selectTab(tabs[to].dataset.tab, { focus: true })
  })
  // The status and the Backlog tab are rebuilt only when the status or the Backlog page changed (the page is clamped first, so a shrunk list shows its last page).
  // Charts count by session id and task count (the pill), so new snapshot numbers alone do not rebuild the cards.
  const drawStatus = () => {
    if (!last) return
    backlogPage = pageOf(last.status.find((g) => g.name === 'Backlog')?.rows.length ?? 0, backlogPage, BACKLOG_PAGE).at
    const json = JSON.stringify([last.status, backlogPage, last.chief?.threadLink], (k, v) => (k === 'gantt' ? [v.map((s) => s.sessionId), taskCount(v)] : v))
    if (json === shownStatus) return
    shownStatus = json
    const opened = (view) => new Set([...document.querySelectorAll(`.seg[data-ticket][data-view="${view}"][aria-expanded="true"]`)].map((d) => d.dataset.ticket))
    const open = opened('agents')
    const info = opened('details')
    shownInfo.clear()
    const collapsed = readCollapsed()
    document.getElementById('status').innerHTML = renderStatus(last.status, open, collapsed, info, last.chief?.threadLink)
    document.getElementById('backlog').innerHTML = renderBacklog(last.status, collapsed, backlogPage, open, info, last.chief?.threadLink)
    document.getElementById('cta').innerHTML = renderBadges(last.status)
  }
  // The Ship loop, Backlog and Done tab pills show a ticket count; the button's aria-label carries it too. Written only when changed.
  const TAB_LABELS = { ship: 'Ship loop', done: 'Done', backlog: 'Backlog' }
  const drawTabCounts = () => {
    if (!last) return
    const counts = tabCounts(last.status, last.merged)
    for (const pill of document.querySelectorAll('[data-count]')) {
      const n = String(counts[pill.dataset.count] ?? 0)
      if (pill.textContent !== n) pill.textContent = n
      const label = `${TAB_LABELS[pill.dataset.count]}, ${n}`
      if (pill.parentElement.getAttribute('aria-label') !== label) pill.parentElement.setAttribute('aria-label', label)
    }
  }
  const seen = versionWatch()
  const poll = async () => {
    const err = document.getElementById('error')
    try {
      const res = await fetch(`/api?mergedPage=${mergedPage}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      last = await res.json()
      if (last.theme === 'dark' || last.theme === 'light') document.documentElement.dataset.theme = last.theme
      else delete document.documentElement.dataset.theme
      if (seen(last.version)) {
        location.reload()
        return
      }
      err.textContent = [last.restartError, last.trackerError].filter(Boolean).join(' ')
      drawStatus()
      draw()
      drawMerged()
      drawCos()
      drawTabCounts()
    } catch (e) {
      err.textContent = `Could not refresh: ${e.message}`
    }
  }
  // Opens or closes one segment's panel in place and closes the row's other one, so nothing is rebuilt.
  const setPanel = (seg, on) => {
    for (const s of seg.closest('.switch').querySelectorAll('.seg')) {
      const mine = on && s === seg
      s.setAttribute('aria-expanded', String(mine))
      const panel = document.getElementById(s.getAttribute('aria-controls') ?? '')
      if (panel) panel.hidden = !mine
    }
  }
  document.addEventListener('keydown', (ev) => {
    const host = ev.key === 'Escape' && ev.target instanceof Element ? ev.target.closest('.seg, .panel') : null
    const seg = host?.matches('.seg') ? host : host && document.getElementById(host.getAttribute('aria-labelledby'))
    if (!seg || seg.getAttribute('aria-expanded') !== 'true') return
    setPanel(seg, false)
    seg.focus()
  })
  document.addEventListener('click', (ev) => {
    const target = ev.target instanceof Element ? ev.target : null
    const tab = target?.closest('button[data-tab]')
    if (tab) {
      selectTab(tab.dataset.tab)
      return
    }
    const seg = target?.closest('button.seg')
    if (seg && !seg.disabled) {
      setPanel(seg, seg.getAttribute('aria-expanded') !== 'true')
      draw()
      return
    }
    const backlogPager = target?.closest('button[data-backlog-page]')
    if (backlogPager) {
      backlogPage = Number(backlogPager.dataset.backlogPage)
      drawStatus()
      draw()
      return
    }
    const pmPager = target?.closest('button[data-pm-page]')
    if (pmPager) {
      pmPage = Number(pmPager.dataset.pmPage)
      drawCos()
      return
    }
    const pager = target?.closest('button[data-page]')
    if (pager) {
      mergedPage = Number(pager.dataset.page)
      drawMerged()
      poll()
      return
    }
    const btn = target?.closest('button[data-copy]')
    if (!btn) return
    const icon = btn.classList.contains('copy-icon')
    const label = btn.textContent
    // An icon button keeps its glyph: the state colors it and the label and title carry the words.
    const show = (state, text) => {
      if (icon) {
        btn.dataset.state = state
        btn.setAttribute('aria-label', text)
        btn.title = text
      } else btn.textContent = text
      setTimeout(() => {
        if (icon) {
          delete btn.dataset.state
          btn.setAttribute('aria-label', 'Copy thread link')
          btn.title = 'Copy thread link'
        } else btn.textContent = label
      }, 1500)
    }
    navigator.clipboard.writeText(btn.dataset.copy).then(
      () => show('copied', 'Copied'),
      () => show('failed', 'Copy failed'),
    )
  })
  // toggle does not bubble, so listen in the capture phase.
  document.addEventListener(
    'toggle',
    (ev) => {
      const d = ev.target
      if (!(d instanceof Element) || !d.matches('details.group, details[data-band]')) return
      const key = d.dataset.group ?? d.dataset.band
      const names = readCollapsed()
      if (d.open) names.delete(key)
      else names.add(key)
      writeCollapsed(names)
    },
    true,
  )
  poll()
  setInterval(poll, 5000)
  setInterval(draw, 1000)
}

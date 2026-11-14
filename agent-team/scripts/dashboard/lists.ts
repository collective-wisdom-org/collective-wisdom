import type { BacklogItem, Priority } from './backlog.ts'

const REFRESH_MS = 10_000
const BAD = /[\x00-\x1f\x7f-\x9f\u2028\u2029]+/g
const NAMES: Record<string, Priority> = { urgent: 'urgent', highest: 'urgent', high: 'high', medium: 'medium', low: 'low', lowest: 'low' }
const NUMBERS: (Priority | null)[] = [null, 'urgent', 'high', 'medium', 'low']
const RANK: Priority[] = ['urgent', 'high', 'medium', 'low']

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)

function nameOf(x: unknown): Priority | null {
  if (typeof x === 'string') return NAMES[x.trim().toLowerCase()] ?? null
  if (typeof x === 'number') return Number.isInteger(x) ? (NUMBERS[x] ?? null) : null
  if (isObj(x)) return nameOf(x.name) ?? nameOf(x.value)
  return null
}

/** Label names from a list of strings or `{ name }` objects, or Linear's `{ nodes: [...] }`. */
function labelNames(x: unknown): string[] {
  const list = isObj(x) ? x.nodes : x
  return Array.isArray(list) ? list.map((l) => (typeof l === 'string' ? l : isObj(l) ? l.name : null)).filter((n): n is string => typeof n === 'string') : []
}

function priorityOf(e: Record<string, unknown>, fields: Record<string, unknown>): Priority | null {
  const fromLabels = [...labelNames(e.labels), ...labelNames(fields.labels)].filter((n) => n.startsWith('priority:')).map((n) => nameOf(n.slice(9)))
  return RANK.find((p) => fromLabels.includes(p)) ?? nameOf(e.priority) ?? nameOf(fields.priority)
}

function createdOf(x: unknown): number | null {
  if (typeof x === 'number') return Number.isFinite(x) ? x : null
  if (typeof x !== 'string') return null
  const t = Date.parse(x.replace(/([+-]\d{2})(\d{2})$/, '$1:$2'))
  return Number.isNaN(t) ? null : t
}

/** The items of one saved list, or `undefined` when the value is not `{ list: [...] }`. An entry with no id of this prefix, or an id already taken, is dropped. */
function parseList(value: unknown, state: BacklogItem['state'], prefix: string): BacklogItem[] | undefined {
  if (!isObj(value) || !Array.isArray(value.list)) return undefined
  const idRe = new RegExp(`^${prefix}-\\d+$`)
  const seen = new Set<string>()
  const items: BacklogItem[] = []
  for (const e of value.list) {
    if (!isObj(e)) continue
    const id = [e.identifier, e.id, e.key].find((v): v is string => typeof v === 'string' && idRe.test(v))
    if (!id || seen.has(id)) continue
    seen.add(id)
    const fields = isObj(e.fields) ? e.fields : {}
    const title = typeof e.title === 'string' ? e.title : typeof fields.summary === 'string' ? fields.summary : ''
    items.push({ id, title: title.replace(BAD, ' ').trim().slice(0, 200), state, priority: priorityOf(e, fields), createdAt: createdOf(e.createdAt ?? fields.created) })
  }
  return items
}

/** The Todo and Backlog tickets of a Linear or Jira repo, from the file the Chief of Staff saves (`.agent-team/tracker-lists.json`), re-read at most every 10 seconds. The last good list of each kind stays when a read or a key is bad. */
export function createTrackerLists(opts: { read: () => string | undefined; now?: () => number }) {
  const now = opts.now ?? Date.now
  let prefix: string | null = null
  let readAt = -Infinity
  let todo: BacklogItem[] = []
  let backlog: BacklogItem[] = []

  function load(p: string) {
    let file: unknown
    try {
      const text = opts.read()
      file = text === undefined ? undefined : JSON.parse(text)
    } catch {}
    if (!isObj(file)) return
    todo = parseList(file.todo, 'Todo', p) ?? todo
    backlog = parseList(file.backlog, 'Backlog', p) ?? backlog
  }

  return {
    want(p: string | null) {
      if (p !== prefix) {
        prefix = p
        todo = backlog = []
        readAt = -Infinity
      }
      if (!p || now() - readAt < REFRESH_MS) return
      readAt = now()
      load(p)
    },
    get: (): BacklogItem[] => {
      if (!prefix) return []
      const taken = new Set(todo.map((t) => t.id))
      return [...todo, ...backlog.filter((b) => !taken.has(b.id))]
    },
  }
}

import type { BacklogItem, Priority } from './backlog.ts'
import { prefixesPattern } from './titles.ts'
import type { Retired } from './titles.ts'

const REFRESH_MS = 1_000
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

/** The items of one saved list, or `undefined` when the value is not `{ list: [...] }`. Each item carries the list's `at` as `readAt` (ms) when it parses. An entry with no id of this prefix or a retired one, or an id already taken, is dropped. */
function parseList(value: unknown, state: BacklogItem['state'], prefix: string, retired: Retired): BacklogItem[] | undefined {
  const readAt = isObj(value) ? createdOf(value.at) : null
  if (!isObj(value) || !Array.isArray(value.list)) return undefined
  const idRe = new RegExp(`^${prefixesPattern(prefix, retired)}-\\d+$`)
  const seen = new Set<string>()
  const items: BacklogItem[] = []
  for (const e of value.list) {
    if (!isObj(e)) continue
    const id = [e.identifier, e.id, e.key].find((v): v is string => typeof v === 'string' && idRe.test(v))
    if (!id || seen.has(id)) continue
    seen.add(id)
    const fields = isObj(e.fields) ? e.fields : {}
    const title = typeof e.title === 'string' ? e.title : typeof fields.summary === 'string' ? fields.summary : ''
    items.push({ id, title: title.replace(BAD, ' ').trim().slice(0, 200), state, priority: priorityOf(e, fields), createdAt: createdOf(e.createdAt ?? fields.created), ...(readAt === null ? {} : { readAt }) })
  }
  return items
}

const message = (why: string | null) => (why ? `Could not read the saved Todo and Backlog lists: ${why}. Showing the last list read.` : null)

/** The Todo and Backlog tickets of a Linear or Jira repo, from the file the Chief of Staff saves (`.agent-team/tracker-lists.json`), re-read at most every second. The last good list of each kind stays when a read or a key is bad, and `error()` says why. `changed()` is the file's change stamp, which GitHub repos read too, with no lists. */
export function createTrackerLists(opts: { read: () => string | undefined; now?: () => number }) {
  const now = opts.now ?? Date.now
  let prefix: string | null = null
  let retiredKey = ''
  let retired: Retired = []
  let keep = true
  let readAt = -Infinity
  let todo: BacklogItem[] = []
  let backlog: BacklogItem[] = []
  let stamp: string | null = null
  let error: string | null = null

  function load(p: string, r: Retired) {
    let file: unknown
    let bad: string | null = null
    try {
      const text = opts.read()
      file = text === undefined ? undefined : JSON.parse(text)
    } catch {
      bad = 'the file is not valid JSON'
    }
    if (!bad && file !== undefined && !isObj(file)) bad = 'the file is not a JSON object'
    if (!isObj(file)) {
      error = keep ? message(bad) : null
      return
    }
    if (typeof file.changed === 'string') stamp = file.changed
    if (!keep) return
    for (const key of ['todo', 'backlog'] as const) {
      const items = parseList(file[key], key === 'todo' ? 'Todo' : 'Backlog', p, r)
      if (items) key === 'todo' ? (todo = items) : (backlog = items)
      else if (file[key] !== undefined) bad = `${key} is not a list`
    }
    error = message(bad)
  }

  return {
    /** `lists` false (GitHub) reads the file for the change stamp only and keeps no lists. */
    want(p: string | null, lists = true, r: Retired = []) {
      const key = JSON.stringify(r)
      if (p !== prefix || lists !== keep || key !== retiredKey) {
        prefix = p
        retiredKey = key
        retired = r
        keep = lists
        todo = backlog = []
        stamp = error = null
        readAt = -Infinity
      }
      if (!p || now() - readAt < REFRESH_MS) return
      readAt = now()
      load(p, retired)
    },
    get: (): BacklogItem[] => {
      if (!prefix || !keep) return []
      const taken = new Set(todo.map((t) => t.id))
      return [...todo, ...backlog.filter((b) => !taken.has(b.id))]
    },
    changed: (): string | null => stamp,
    error: (): string | null => error,
  }
}

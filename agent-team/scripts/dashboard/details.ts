import { execFile } from 'node:child_process'

type Run = (args: string[]) => Promise<string>

export type Detail = {
  kind: 'spec' | 'changes'
  url?: string
  sections: { name: string; text: string }[]
  files?: { path: string; add: number; del: number }[]
  moreFiles?: number
  reviews?: { name: string; verdict: string; url?: string }[]
}
type Parsed = Pick<Detail, 'sections' | 'files' | 'moreFiles' | 'reviews'> & { specPaths: string[]; mergeSha?: string }
/** A detail as `get()` returns it. For a merged ticket, `spec` is the spec the PR added and the commit that holds it. */
export type Found = Detail & { spec?: { path: string; sha: string } }

const REFRESH_MS = 60_000
const TEXT_MAX = 2000
const FILES_MAX = 30
const SPEC_HEADINGS = ['goal', 'builds', 'leaves out', 'non-goals', 'out of scope', 'calls i made', 'touches']
const CONTROL = /[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029\u202a-\u202e\u2066-\u2069]/g
/** Only a comment from someone with write access counts as a review; anyone can comment on a public PR. */
const WRITERS = ['OWNER', 'MEMBER', 'COLLABORATOR']

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === 'object' && x !== null && !Array.isArray(x)
const clean = (s: string) => s.replace(/\r\n?/g, '\n').replace(CONTROL, ' ').trim()
const cap = (s: string) => (s.length > TEXT_MAX ? `${s.slice(0, TEXT_MAX)}…` : s)

/** The spec path rule of `cos_handoff.py`: the only kind of path the dashboard will hand to git or put in a link. */
export const validSpecPath = (p: unknown): p is string => typeof p === 'string' && /^docs\/superpowers\/specs\/[A-Za-z0-9._-]+\.md$/.test(p) && !p.includes('..')
/** A commit id of 7 to 40 hex characters, the `cos_handoff.py` rule; `git show` takes a short one. */
export const validSha = (s: unknown): s is string => typeof s === 'string' && /^[0-9a-f]{7,40}$/.test(s)

/** The link to a spec at a commit, or undefined when the repo url, the path or the sha is not usable. */
export function specUrlOf(repoUrl: string | undefined, specPath: unknown, specSha: unknown): string | undefined {
  return repoUrl && validSpecPath(specPath) && validSha(specSha) ? `${repoUrl}/blob/${specSha}/${specPath}` : undefined
}

/** The one spec a merged PR added for a ticket: of the PR's spec paths, those whose name holds `-<prefix>-<n>-`. None, or more than one, gives undefined. */
export function specOfMerged(paths: string[], id: string, mergeSha: string | undefined): { path: string; sha: string } | undefined {
  const mark = `-${id.toLowerCase()}-`
  const hits = paths.filter((p) => validSpecPath(p) && p.slice(p.lastIndexOf('/') + 1).includes(mark))
  return hits.length === 1 && typeof mergeSha === 'string' && /^[0-9a-f]{40}$/.test(mergeSha) ? { path: hits[0], sha: mergeSha } : undefined
}

/** The `## ` sections of a markdown text, in order. A `###` heading, or a `## ` line inside a code fence, stays inside its section. */
function sectionsOf(markdown: string): { name: string; text: string }[] {
  const out: { name: string; lines: string[] }[] = []
  let fenced = false
  for (const line of clean(markdown).split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced
    const h = fenced ? null : line.match(/^## +(\S.*?)\s*#*\s*$/)
    if (h) out.push({ name: h[1], lines: [] })
    else out[out.length - 1]?.lines.push(line)
  }
  return out.map((s) => ({ name: s.name, text: s.lines.join('\n').trim() }))
}

/** The spec sections worth showing (Goal, Builds, Leaves out, Non-goals, Out of scope, Calls I made, Touches), in the spec's order. */
export function specDetail(markdown: string): Detail['sections'] {
  return sectionsOf(markdown)
    .filter((s) => s.text && SPEC_HEADINGS.includes(s.name.toLowerCase()))
    .map((s) => ({ name: s.name, text: cap(s.text) }))
}

/** The `Not proven` line of a PR body and the `- ` lines under it, up to the first blank line that is followed by something else. */
function notProven(body: string): string {
  const lines = clean(body).split('\n')
  const at = lines.findIndex((l) => /^Not proven/i.test(l))
  if (at < 0) return ''
  const out = [lines[at].replace(/^Not proven\s*:?\s*/i, '')]
  for (let i = at + 1; i < lines.length; i++) {
    const l = lines[i]
    if (l.startsWith('- ')) out.push(l)
    else if (l.trim() === '') {
      const next = lines.slice(i + 1).find((x) => x.trim() !== '')
      if (next === undefined || !next.startsWith('- ')) break
    } else if (/^\s/.test(l)) out.push(l.trim())
    else break
  }
  return out.filter(Boolean).join('\n')
}

/** The newest comment by a writer whose body starts with `## <name>`, as a review line; null when there is none or it names no verdict. */
function review(comments: unknown[], name: string): NonNullable<Detail['reviews']>[number] | null {
  const mine = comments.filter((c): c is Record<string, unknown> => isObj(c) && typeof c.body === 'string' && WRITERS.includes(c.authorAssociation as string) && c.body.startsWith(`## ${name}`))
  const c = mine[mine.length - 1]
  if (!c) return null
  const verdicts = [...String(c.body).matchAll(/Verdict:[\s*]*(CHANGES NEEDED|[A-Za-z]+)/gi)]
  const verdict = verdicts[verdicts.length - 1]?.[1].toUpperCase()
  if (!verdict) return null
  return typeof c.url === 'string' && c.url.startsWith('https://') ? { name, verdict, url: c.url } : { name, verdict }
}

/** Turns `gh pr view --json body,files,comments,mergeCommit` output into the changes detail. Bad JSON gives null. */
export function prDetail(json: string): Parsed | null {
  let data: unknown
  try {
    data = JSON.parse(json)
  } catch {
    return null
  }
  if (!isObj(data)) return null
  const body = typeof data.body === 'string' ? data.body : ''
  const found = sectionsOf(body)
  const pick = (name: string) => found.find((s) => s.name.toLowerCase() === name && s.text)
  const wanted: [string, string | undefined][] = [
    ['Summary', (pick('summary') ?? pick('changes'))?.text],
    ['Release note', pick('release note')?.text],
    ['Not proven', notProven(pick('proof')?.text ?? '')],
  ]
  const sections = wanted.filter((w): w is [string, string] => !!w[1]).map(([name, text]) => ({ name, text: cap(text) }))
  const all = (Array.isArray(data.files) ? data.files : []).filter((f): f is Record<string, unknown> => isObj(f) && typeof f.path === 'string')
  const count = (x: unknown) => (Number.isInteger(x) && (x as number) >= 0 ? (x as number) : 0)
  const files = all.slice(0, FILES_MAX).map((f) => ({ path: clean(f.path as string).slice(0, 300), add: count(f.additions), del: count(f.deletions) }))
  const comments = Array.isArray(data.comments) ? data.comments : []
  const reviews = [review(comments, 'Code review'), review(comments, 'Security review')].filter((r): r is NonNullable<typeof r> => r !== null)
  const specPaths = all.map((f) => f.path as string).filter(validSpecPath)
  const oid = isObj(data.mergeCommit) ? data.mergeCommit.oid : undefined
  return { sections, files, moreFiles: Math.max(0, all.length - FILES_MAX), reviews, specPaths, ...(typeof oid === 'string' ? { mergeSha: oid } : {}) }
}

/** git runs with no shell, in the root checkout. */
export function gitRunner(root: string): Run {
  return (args) =>
    new Promise((resolve, reject) => {
      execFile('git', ['-C', root, ...args], { timeout: 5000, maxBuffer: 1 << 20 }, (err, out) => (err ? reject(err) : resolve(out)))
    })
}

const SPEC_STAGES = ['awaiting-build', 'build', 'build-queued']
const PR_STAGES = ['awaiting-merge', 'merge', 'merge-queued']

/** `merged: true` asks for the PR text of a merged ticket by its PR number; the stage is then ignored. */
export type DetailWant = { id: string; stage: string; specPath?: unknown; specSha?: unknown; pr?: unknown; merged?: boolean }

/**
 * Per-stage detail read in the background: a spec once per commit and path while a ticket waits for build approval or builds, the PR at most once a minute from merge approval on, and the PR of a merged ticket the same way.
 * A failed read keeps the last good result (a failed spec read is retried after a minute). Entries for tickets no longer wanted are dropped.
 */
export function createDetails(opts: { run: Run; git: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  const specs = new Map<string, { sections?: Detail['sections']; failedAt?: number }>()
  const prs = new Map<string, { startedAt: number; parsed?: Parsed }>()
  const reading = new Set<Promise<void>>()
  let wanted = new Map<string, { kind: 'spec' | 'changes' | 'merged'; key: string }>()

  const start = (job: () => Promise<void>) => {
    const p: Promise<void> = job().then(() => {
      reading.delete(p)
    })
    reading.add(p)
  }

  return {
    want(wants: DetailWant[], cfg: { slug: string } | null) {
      wanted = new Map()
      const goodPr = (w: DetailWant) => !!cfg && Number.isInteger(w.pr) && (w.pr as number) > 0
      for (const w of wants) {
        if (w.merged) continue
        if (SPEC_STAGES.includes(w.stage) && validSha(w.specSha) && validSpecPath(w.specPath)) wanted.set(w.id, { kind: 'spec', key: `${w.specSha}:${w.specPath}` })
        else if (PR_STAGES.includes(w.stage) && goodPr(w)) wanted.set(w.id, { kind: 'changes', key: String(w.pr) })
      }
      // An id still on the board keeps its own detail; a merged want for it is ignored.
      for (const w of wants) if (w.merged && !wanted.has(w.id) && goodPr(w)) wanted.set(w.id, { kind: 'merged', key: String(w.pr) })
      const keys = (spec: boolean) => new Set([...wanted.values()].filter((v) => (v.kind === 'spec') === spec).map((v) => v.key))
      for (const k of specs.keys()) if (!keys(true).has(k)) specs.delete(k)
      for (const k of prs.keys()) if (!keys(false).has(k)) prs.delete(k)

      for (const target of wanted.values()) {
        const t = now()
        if (target.kind === 'spec') {
          const rev = target.key
          const have = specs.get(rev)
          if (have && (have.sections || t - (have.failedAt ?? 0) < REFRESH_MS)) continue
          specs.set(rev, { failedAt: t })
          start(async () => {
            try {
              const text = await opts.git(['show', rev])
              if (specs.has(rev)) specs.set(rev, { sections: specDetail(text) })
            } catch {}
          })
        } else {
          const n = target.key
          const have = prs.get(n)
          if (have && t - have.startedAt < REFRESH_MS) continue
          prs.set(n, { startedAt: t, parsed: have?.parsed })
          start(async () => {
            try {
              const parsed = prDetail(await opts.run(['pr', 'view', n, '--repo', cfg!.slug, '--json', 'body,files,comments,mergeCommit']))
              const cur = prs.get(n)
              if (parsed && cur) cur.parsed = parsed
            } catch {}
          })
        }
      }
    },
    get(): Record<string, Found> {
      const out: Record<string, Found> = {}
      for (const [id, { kind, key }] of wanted) {
        if (kind === 'spec') {
          const sections = specs.get(key)?.sections
          if (sections?.length) out[id] = { kind: 'spec', sections }
        } else {
          const parsed = prs.get(key)?.parsed
          if (!parsed) continue
          const { specPaths, mergeSha, ...detail } = parsed
          const spec = kind === 'merged' ? specOfMerged(specPaths, id, mergeSha) : undefined
          if (detail.sections.length || detail.files?.length || detail.reviews?.length || spec) out[id] = { kind: 'changes', ...detail, ...(spec ? { spec } : {}) }
        }
      }
      return out
    },
    idle: async () => {
      while (reading.size) await Promise.all([...reading])
    },
  }
}

import type { Row } from './rows.ts'

const SAFE_ID = /^[A-Za-z0-9_-]{1,80}$/

/** The snapshot file name for a session id, or null when the id could climb out of the folder. */
export function snapshotName(sessionId: string): string | null {
  return SAFE_ID.test(sessionId) ? `${sessionId}.json` : null
}

const HEADING = /^[A-Z][A-Z ]{2,38}[A-Z]\./
const HEADING_LINES = 5

/** The capital-letter heading in the first lines of a prompt (`BACKLOG RANKING.` gives `BACKLOG RANKING`), or null. */
export function pickHeading(text: string): string | null {
  for (const raw of text.split('\n').slice(0, HEADING_LINES)) {
    const line = raw.replace(/\s+/g, ' ').trim()
    if (HEADING.test(line)) return line.slice(0, line.indexOf('.'))
  }
  return null
}

const KEY_LINE = /^[A-Z][A-Za-z' ]*:/
const FILED = /^(?:[-*]\s*)?([A-Z][A-Z0-9]*-\d+)\b/

/** The ticket a ticket helper filed: the first `<PREFIX>-N` at the start of a line under `Tickets:` in its `TICKET HELPER DONE` block, up to the next `Key:` line. Null for `Tickets: none` or no block. */
export function pickFiledTicket(answer: string): string | null {
  const lines = answer.split('\n')
  const start = lines.findIndex(line => line.trim() === 'TICKET HELPER DONE')
  if (start === -1) return null
  const first = lines.findIndex((line, i) => i > start && line.startsWith('Tickets:'))
  if (first === -1) return null
  const found = FILED.exec(lines[first].slice('Tickets:'.length).trim())
  if (found) return found[1]
  for (const raw of lines.slice(first + 1)) {
    const line = raw.trim()
    if (KEY_LINE.test(line)) break
    const next = FILED.exec(line)
    if (next) return next[1]
  }
  return null
}

const REQUEST_MARKER = /^The (?:user['\u2019]s request, verbatim|Chief of Staff['\u2019]s observation):/
const REQUEST_LENGTH = 80

/** The first non-empty line after the request marker of a ticket helper's task prompt, whitespace collapsed and cut to 80 characters, or null. */
export function pickRequest(text: string): string | null {
  const lines = text.split('\n')
  const marker = lines.findIndex(line => REQUEST_MARKER.test(line.trim()))
  if (marker === -1) return null
  for (const raw of lines.slice(marker + 1)) {
    const line = raw.replace(/\s+/g, ' ').trim()
    if (line !== '') return line.slice(0, REQUEST_LENGTH)
  }
  return null
}

/** The JSON text the local dashboard reads for one session. `pricing: 2` marks rows priced after the CW-220 rate fix. `threadId`, `heading`, `ticket` and `request` are null when unknown. */
export function buildSnapshot(args: { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: Row[]; threadId: string | null; heading: string | null; ticket?: string | null; request?: string | null }): string {
  const { sessionId, cwd, updatedAt, total, rows, threadId, heading, ticket = null, request = null } = args
  return JSON.stringify({ sessionId, cwd, updatedAt, total, pricing: 2, threadId, heading, ticket, request, rows })
}

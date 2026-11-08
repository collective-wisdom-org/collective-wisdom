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

/** The JSON text the local dashboard reads for one session. `pricing: 2` marks rows priced after the CW-220 rate fix. `threadId` and `heading` are null when unknown. */
export function buildSnapshot(args: { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: Row[]; threadId: string | null; heading: string | null }): string {
  const { sessionId, cwd, updatedAt, total, rows, threadId, heading } = args
  return JSON.stringify({ sessionId, cwd, updatedAt, total, pricing: 2, threadId, heading, rows })
}

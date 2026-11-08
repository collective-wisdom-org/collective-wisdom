import type { Row } from './rows.ts'

const SAFE_ID = /^[A-Za-z0-9_-]{1,80}$/

/** The snapshot file name for a session id, or null when the id could climb out of the folder. */
export function snapshotName(sessionId: string): string | null {
  return SAFE_ID.test(sessionId) ? `${sessionId}.json` : null
}

/** The JSON text the local dashboard reads for one session. `pricing: 2` marks rows priced after the CW-220 rate fix. */
export function buildSnapshot(args: { sessionId: string; cwd: string; updatedAt: number; total: number | null; rows: Row[] }): string {
  const { sessionId, cwd, updatedAt, total, rows } = args
  return JSON.stringify({ sessionId, cwd, updatedAt, total, pricing: 2, rows })
}

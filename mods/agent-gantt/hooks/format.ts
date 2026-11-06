// Text helpers for the pane. Pure, so nothing here needs the engine.

const two = (n: number) => String(n).padStart(2, '0')

/** Local HH:MM. */
export const clock = (ms: number) => {
  const d = new Date(ms)
  return `${two(d.getHours())}:${two(d.getMinutes())}`
}

/** 950, 12.3k, 1.2M. */
export const tokens = (n: number) => {
  if (n >= 999_950) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1e3).toFixed(1)}k`
  return String(n)
}

/** $0.42, or a dash when the cost is unknown. */
export const dollars = (c: number | null | undefined) =>
  c === null || c === undefined ? '–' : `$${c.toFixed(2)}`

/** Pads or cuts to exactly `width` cells. */
export const fit = (s: string, width: number) =>
  s.length > width ? `${s.slice(0, Math.max(0, width - 1))}…` : s.padEnd(width)

/** A bar `width` cells wide on the axis t0..t1: spaces up to `start`, then blocks to `end`. At least one block. */
export const bar = (start: number, end: number, t0: number, t1: number, width: number) => {
  const span = Math.max(1, t1 - t0)
  const from = Math.min(width - 1, Math.max(0, Math.floor(((start - t0) / span) * width)))
  const to = Math.min(width, Math.max(from + 1, Math.ceil(((end - t0) / span) * width)))
  return ' '.repeat(from) + '█'.repeat(to - from)
}

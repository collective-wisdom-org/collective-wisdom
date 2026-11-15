import { loginOf } from './titles.ts'

type Run = (args: string[]) => Promise<string>

const RETRY_MS = 5 * 60 * 1000

/** The GitHub login of the person running the dashboard, read once in the background and kept. A failed read, or an answer that is not a login, is tried again at most every 5 minutes. */
export function createViewer(opts: { run: Run; now?: () => number }) {
  const now = opts.now ?? Date.now
  let login: string | null = null
  let failedAt = -Infinity
  let reading: Promise<void> | null = null

  async function read() {
    try {
      const got = loginOf((await opts.run(['api', 'user', '--jq', '.login'])).trim())
      if (got) login = got
      else failedAt = now()
    } catch {
      failedAt = now()
    }
    reading = null
  }

  return {
    want() {
      if (login || reading || now() - failedAt < RETRY_MS) return
      reading = read()
    },
    get: (): string | null => login,
    idle: async () => {
      while (reading) await reading
    },
  }
}

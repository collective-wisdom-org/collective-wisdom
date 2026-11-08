# CW-242 plan: dashboard follows the system dark mode

Spec: `docs/superpowers/specs/2026-11-08-cw-242-dashboard-dark-mode-design.md`

All paths are under `agent-team/scripts/dashboard/` unless noted.

## Task 1: server (`server.ts`, `server.test.ts`)

1. Export `systemScheme(platform: string, result: { code: number | null; out: string } | null): 'dark' | 'light' | null`. `darwin` + exit 0 + trimmed output `Dark` gives `dark`; `darwin` + non-zero exit gives `light`; `darwin` + `null` result (could not run or timed out) gives `null`; any other platform gives `null`.
2. Add an optional `scheme?: () => Promise<'dark' | 'light' | null>` to the `startServer` options. The default runs `execFile('defaults', ['read', '-g', 'AppleInterfaceStyle'], { timeout: 2000 })` on darwin only (no shell) and feeds the result to `systemScheme`. A non-zero exit from the command is a `{ code, out }` result; a spawn error or timeout is `null`.
3. Keep `let theme: 'dark' | 'light' | null`. Refresh it once at start (do not block startup on it beyond the first await being optional; requests never wait on it) and inside the existing 5 second `codeTimer` loop. Guard against overlapping runs. A throw keeps the last answer.
4. `/api` adds `theme`. `/` replaces the `<html lang="en">` opening with `<html lang="en" data-theme="dark|light">` when `theme` is not null; the value is one of two fixed strings.
5. One table-driven test for `systemScheme` (cases in the spec) and one started-server test using the injected `scheme`: `/` carries `data-theme` and `/api` reports the same `theme`; with `null`, `/` has no `data-theme` and `/api` has `theme: null`.

## Task 2: page (`page/index.html`, `page/app.js`)

1. Replace the dark `@media (prefers-color-scheme: dark)` block with `light-dark(<light>, <dark>)` on each color variable, using today's values. Keep `color-scheme: light dark` on `:root`; add `:root[data-theme="dark"] { color-scheme: dark; }` and `:root[data-theme="light"] { color-scheme: light; }`. No color value changes. Check the file for any other `prefers-color-scheme` use.
2. In `poll()`, after `last = await res.json()`: set `document.documentElement.dataset.theme` to `last.theme` when it is `dark` or `light`, else delete the attribute.

## Task 3: docs (`README.md`)

Add one sentence to § Local dashboard: the page follows the macOS light or dark setting, read by the server, because the T3 browser does not pass it through.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` (use `uvx pytest -q agent-team/scripts` if pytest is missing).

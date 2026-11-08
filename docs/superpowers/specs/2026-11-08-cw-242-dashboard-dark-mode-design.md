# CW-242: Make the dashboard follow the system dark mode setting

**Status:** Shipped
**Shipped:** in PR #246, as specified
**Ticket:** [#242](https://github.com/collective-wisdom-org/collective-wisdom/issues/242)

## Goal

With macOS in dark mode, the dashboard opens dark in a new T3 preview tab with no manual appearance step, and opens light when macOS is light. It keeps doing so after the tab is closed and reopened and after the dashboard server restarts.

## Cause (reproduced)

Checked on this machine on 2026-11-08, against the root checkout's dashboard on port 47060 (`main` at `59a7c70`).

- macOS: `defaults read -g AppleInterfaceStyle` prints `Dark`.
- T3: the app theme (`t3code:theme-appearance-mode` in T3's local storage) is `system`, and the browser default appearance (`browserDefaultAppearance` in `~/.t3/userdata/client-settings.json`) is `system`.
- A new preview tab on the dashboard reports `matchMedia('(prefers-color-scheme: dark)').matches === false` and a white body. Setting the tab's appearance to `system` (clearing any override) changes nothing.
- Setting the tab's appearance to `dark` makes the page dark after a reload. A second new tab opened next to it is light again.

So the page's CSS is right: it follows `prefers-color-scheme`. The T3 preview browser (Electron 44, Chrome 152) reports `light` to every tab whatever macOS says, and the only thing that makes a tab dark is a per-tab override that a new tab does not have. That override is the fix that was applied and then lost. Nothing in the dashboard server or a restart is involved; a reopened tab is enough to lose it.

The page cannot read the real setting from inside that browser. The dashboard server runs on the same machine and can.

## Design

1. **Server reads the system setting.** `server.ts` exports `systemScheme(platform, result)`, a pure function that turns the result of `defaults read -g AppleInterfaceStyle` into `'dark'`, `'light'` or `null`:
   - `darwin`, exit 0, output `Dark` (trimmed): `'dark'`.
   - `darwin`, non-zero exit (the key is absent in light mode): `'light'`.
   - `darwin`, the command could not run or timed out: `null`.
   - Any other platform: `null` (the command is not run).

   The server runs the command with `execFile` (2 second timeout, no shell) at start and then every 5 seconds in the loop CW-239 added, and keeps the last answer. Requests never wait on it.
2. **First paint.** When the server serves `/`, it puts the last answer on the root element: `<html lang="en" data-theme="dark">` or `"light"`. With `null` it leaves `index.html` as is. The value is one of two fixed strings, never text from a request.
3. **CSS.** `index.html` keeps one list of colors, each written as `light-dark(<light>, <dark>)` with today's values, and picks the scheme with `color-scheme`:
   - `:root { color-scheme: light dark; }` (no `data-theme`: the browser's `prefers-color-scheme` decides, as today).
   - `:root[data-theme="dark"] { color-scheme: dark; }` and `:root[data-theme="light"] { color-scheme: light; }`.

   The `@media (prefers-color-scheme: dark)` block goes away; `light-dark()` covers it. No color value changes.
4. **Live change.** `/api` adds `theme: 'dark' | 'light' | null`. `poll()` sets `document.documentElement.dataset.theme` to it, or removes the attribute on `null`, so switching macOS while the tab is open takes effect within about 10 seconds with no reload.
5. **Restart and reopen.** The answer is computed by whichever server is running, on every request, so a restarted server (CW-239 swap or a fresh `start.ts`) and a reopened tab both get it with nothing stored anywhere.

## Calls I made (surprising first)

- **The system setting wins over a per-tab override.** With `data-theme` set, a tab the user forced to the other scheme with T3's appearance control still shows the system scheme. The page cannot tell a user's override from the browser's wrong default, and the wrong default is the case the ticket is about.
- **The T3 app theme is not read, only macOS.** T3 keeps its theme in Electron local storage (leveldb), which is not a stable place to read from. With T3 on `system`, which is how it is set here, this is the same answer. If someone sets T3 to an explicit `light` or `dark` that differs from macOS, the dashboard follows macOS.
- **macOS only.** On Linux and Windows the server sends no theme and the page falls back to `prefers-color-scheme` as today. The team runs on macOS.
- **`light-dark()` over a second copy of the dark colors.** It keeps one color list. It needs Chrome 123, Safari 17.5 or Firefox 120; the T3 browser is Chrome 152. An older browser would show unstyled colors, which is an acceptable floor for a localhost tool.
- The check reuses the existing 5 second server loop instead of adding a timer.

## Tests

- `server.test.ts`, one table-driven case for `systemScheme`: `darwin` with `Dark` gives `dark`, with `Dark\n` gives `dark`, with a non-zero exit gives `light`, with a spawn error gives `null`, and `linux` gives `null`.
- `server.test.ts`, one case on a started server: `/` carries `data-theme` when the scheme is known and `/api` reports the same `theme`. The scheme source is injectable in `startServer` options so the test does not depend on the test machine's setting.
- `app.test.js` is unchanged: the `poll()` change is a one-line attribute set.

Proved by hand in the PR: with macOS dark, a new T3 preview tab on a dashboard run from the worktree is dark with no appearance step; close and reopen the tab, still dark; restart the server, still dark; switch macOS to light, the open tab turns light within about 10 seconds and a new tab opens light.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes, and so does `python3 -I -m pytest -q agent-team/scripts`.

## Docs

- `README.md` § Local dashboard gains one sentence: the page follows the macOS light or dark setting, read by the server, because the T3 browser does not pass it through.

## Non-goals

- Restyling the light or dark colors.
- A theme switch on the page.
- Reading T3's own theme setting.
- Fixing the T3 preview browser's `prefers-color-scheme`; that is T3's code, not this repo's.

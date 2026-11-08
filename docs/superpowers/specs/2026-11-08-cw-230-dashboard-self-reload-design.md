# CW-230: Reload the open dashboard page when its files change

**Status:** Draft
**Ticket:** [#230](https://github.com/collective-wisdom-org/collective-wisdom/issues/230)
**Related:** CW-227 (#227, also edits `page/app.js`).

## Goal

A dashboard tab that is already open picks up a new `index.html` or `app.js` by itself, within one poll, with no hard refresh.

## Today

Facts from `main` at `d918a2b`.

- `agent-team/scripts/dashboard/server.ts` serves `/` and `/app.js` from the `PAGES` map, reading `page/index.html` and `page/app.js` from disk on every request with `Cache-Control: no-store`. A fresh load always gets the current files.
- `/api` returns `buildApi(...)` from `api.ts`: `{ generatedAt, status, merged }`. There is no version field.
- `poll()` in `page/app.js` fetches `/api` every 5 seconds and redraws. The page never reloads itself.
- `start.ts` reuses a healthy server, so server module changes need a restart. That stays out of scope.

## Design

1. **Page version on the server.** `server.ts` exports `pageVersion(dir: string): string | null`. It reads every file named in `PAGES` from `dir` and returns the first 16 hex characters of a SHA-256 over their contents, in `PAGES` order with a separator between files. If any file can't be read it returns `null`.
2. **`/api` carries it.** The `/api` handler adds `version: pageVersion(<page dir>)` to the object `buildApi` returns. The hash is computed on every `/api` request; the two files are small and `/` already reads them on every load. `api.ts` and `buildApi` don't change.
3. **The page compares.** `app.js` exports a small pure helper, `versionWatch()`, returning a function `seen(version) -> boolean` that answers "reload now?":
   - A value that is not a non-empty string (missing, `null`, an older server) returns `false` and changes nothing.
   - The first string seen becomes the baseline and returns `false`.
   - A later string equal to the baseline returns `false`; a different one returns `true`.
4. **Reload.** In `poll()`, after a successful `/api` response, `if (seen(last.version)) location.reload()` runs before any redraw. A failed fetch or a non-OK response never reaches it. Open `Agents` charts and the merged page number reset on reload; collapsed groups already persist in `localStorage`.

## Tests

- `server.test.ts`, one table-driven case for `pageVersion` on a temp folder: the same files give the same version twice; changing either file changes it; a missing file gives `null`. Plus one check that `/api` has a `version` equal to `pageVersion` of the real page folder.
- `app.test.js`, one table-driven case for `versionWatch`: sequences such as `[undefined, 'a', 'a', 'b']` give `[false, false, false, true]`, and `[null, 'a']`, `['a', null, 'a']` never return `true`.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes, and so does `python3 -I -m pytest -q agent-team/scripts`.

## Non-goals

- Restarting the server when `server.ts`, `api.ts` or other server modules change.
- Carrying page state (open charts, merged page) across the reload.
- Tabs opened before this ships: they need one hard refresh after the merge.

## Calls I made

- **Version is added in `server.ts`, not `buildApi`.** It is about the files the server serves, not the team's state, and it keeps `api.ts` free of file reads.
- **Hash on every `/api` request, no mtime cache.** The two files are a few dozen KB and read only every 5 seconds per tab; a cache adds code and a way to miss a change that keeps the mtime.
- **`version` is a 16-character SHA-256 prefix,** short enough to read in devtools; collisions don't matter for this use.
- **An unreadable page file makes `version` `null`,** which the page ignores, so a file missing for a moment during a checkout does not reload into a 404. If a poll lands mid-write and the page reloads into a broken file, the next change to the files reloads it again; a manual refresh also fixes it.
- **Reload runs before the redraw** of that poll, so the old code does not paint data the new code might lay out differently.
- **The helper is a factory exported from `app.js`** so the rule is testable without a DOM; `poll()` holds one instance.

# CW-175: Fit the dashboard to a narrow side pane and show a title on every ticket row

**Status:** Draft
**Ticket:** [#175](https://github.com/collective-wisdom-org/collective-wisdom/issues/175)
**Follows:** CW-173 (#174), which added the local dashboard.

## Goals

- The dashboard reads well in a side pane 300 to 400px wide: nothing is cut off and nothing needs sideways scrolling, in the Status view or the Agents (Gantt) view.
- Wide windows still look right, and the page looks less plain in both.
- Every Status row shows a title. A title missing from state comes from the tracker; the ID shows alone only when that read fails.
- New state stops having blank titles: every `start` op carries one.

## Today

Facts from `main` at `c077df6`.

- The page is `agent-team/scripts/dashboard/page/index.html` (inline styles) and `page/app.js` (`renderStatus`, `renderGantt`, tested by `page/app.test.js`).
- A Status row (`.ticket`) is a six-column grid of about 45rem. A Gantt row (`.grow`) is an eight-column grid of about 50rem. Both run off the right edge in a narrow pane.
- `api.ts` `buildApi` takes each row's `title` from `groupTickets` (`.claude/mods/status-pane/hooks/groups.ts`), which reads `title` from state with no fallback. The server (`server.ts`) calls `buildApi` synchronously on every `/api` poll (every 5 seconds).
- `cos_state.py` `op_start` takes `title` as optional and stores `""` when it is missing. The new-ticket start (`chief-of-staff/SKILL.md` § Readiness check and start, step 3) passes it. The state rebuild (`startup.md` § State rebuild) and `adopt N` (`SKILL.md` § Adopt, step 3) write `start` with no title. The rebuild reads the tickets with `list-tickets`, so it has the titles; adopt works from the sweep's `untracked` line, which carries no title.
- In the current state, CW-97, CW-98 and CW-94 have `""`, CW-69 and CW-60 have no `title` key, and only CW-91 has one.
- The page's CSP is `default-src 'self'; style-src 'self' 'unsafe-inline'`.

## Builds

### 1. Layout and styling (`index.html`, `app.js`)

CSS only plus small markup changes; no new data.

- **Status rows become cards.** Each ticket is a card with three lines:
  1. the ID (issue link), a stage badge, a risk badge, the PR link and the Copy thread link button, wrapping onto a second line when they don't fit;
  2. the title, wrapping;
  3. the next step, muted, wrapping.
  
  Cards sit in a grid of `repeat(auto-fill, minmax(min(100%, 22rem), 1fr))`, so a narrow pane gets one column and a wide window gets two or three. Long words break (`overflow-wrap: anywhere`).
- **Risk badge.** The colour comes from the first word of the risk text: `low` green, `medium` amber, `high` red, anything else (including `not rated yet`) grey. The badge shows the whole risk text and wraps inside itself when it is long, so nothing is hidden behind a hover.
- **Stage badge.** Shows the stage name (`build`, `awaiting-spec` and so on) in a neutral style.
- **Group headers.** Larger and bolder, with the count as a pill.
- **Gantt rows stack in a narrow pane.** Each agent row is: line 1 the name (indented by depth, cut off with an ellipsis) and the cost on the right; line 2 the timeline bar at full width; line 3 a muted line `repo · 14:02–running · 12.3k tokens · 2 kids`. The column header row hides. A container query (`@container (min-width: 48rem)` on the session card) brings back today's column layout and header in a wide window.
- **Spacing and type.** `body` padding `.75rem` under 30rem and `1.25rem` above; the page caps at `80rem` and centres. A slightly larger heading scale. Light and dark keep working through the existing colour variables (badge colours get a light and a dark value).
- Links, the Copy thread link button and its `data-copy` contract stay as they are. Escaping stays with `esc`.

### 2. Title fallback from the tracker (`api.ts`, `server.ts`, new `titles.ts`)

- `buildApi` takes a new input `titles: Record<string, string>`. A row's title is the state title when it is non-empty, else `titles[id]`, else `""`. The page shows the ID alone for `""` (it already does: the title line is just empty, so the card drops that line).
- A new `agent-team/scripts/dashboard/titles.ts` keeps a per-server cache of tracker titles:
  - `want(ids)` takes the row IDs whose state title is empty. For each one not cached and not tried in the last 5 minutes, it queues a read. Reads run one at a time in the background, so `/api` never waits on the tracker; the next poll shows the title.
  - A read runs `gh.sh issue view <N> --repo <owner>/<repo> --json title` with `execFile` (no shell), `cwd` the root checkout (so `gh.sh` picks the repo's account), a 10-second timeout, and `gh.sh` found next to the dashboard (`join(import.meta.dirname, '..', 'gh.sh')`, which is `~/.collective-wisdom/scripts/gh.sh` on the machine).
  - Only IDs of the form `<PREFIX>-<digits>`, with the prefix from `project.md` § Identity, are read. Any other ID is never sent to `gh`.
  - A title is cleaned the way `cos_state.py` `clean_title` does: control characters become spaces, trimmed, 200 characters at most. An empty or failed read is cached as a failure and retried after 5 minutes.
  - Reads happen only when the tracker is `github` (the server already checks `Tickets are GitHub issues` for the issue links). Linear and Jira have no script-side adapter: their rows with no state title show the ID alone.
- `server.ts` builds one cache per server, calls `want` with the empty-title IDs from state on each `/api`, and passes the cache's titles to `buildApi`.

### 3. Every `start` carries a title (`cos_state.py`, chief-of-staff docs)

- `op_start` makes `title` required and refuses an empty one after cleaning (`Reject("title must be a non-empty string")`), so no new ticket enters state without one. `set` keeps today's rules (a string, cleaned).
- `startup.md` § State rebuild: the `start` op passes the title from the `list-tickets` read the rebuild already makes.
- `SKILL.md` § Adopt step 3: run `get-ticket` for the ticket (on Linear and Jira the sweep already ran it for this line; reuse that read) and pass its title in `start`. If the read fails, write nothing and say the ticket can't be adopted until the tracker answers.
- `state-keys.md` `title`: says `start` requires it.
- Tickets already in state with a blank title stay as they are; the dashboard fallback covers them.

### 4. Tests and proof

- `api.test.ts`: one table-driven test for the title rule: state title wins; empty or missing state title takes `titles[id]`; neither gives `""`.
- `titles.test.ts` (new, same Node test run): one table-driven test with a fake runner: an ID with the right prefix is read once and cached; a wrong-prefix ID is never read; a failure is not retried inside 5 minutes and is retried after; a title with control characters is cleaned.
- `test_cos.py` `test_ticket_title`: add rows for a `start` with no title and with a blank title (`"  "`), both rejected. Update the shared `START` fixture (and any other test's `start` op) to carry a title.
- No CSS tests. `app.test.js` keeps its escaping, link and copy-button tests passing against the new markup.
- Proof: screenshots of the page at 320px, 400px and 1280px wide with the current state, plus a browser check at 320 and 400px that `document.documentElement.scrollWidth <= innerWidth` and no Status card or Gantt row is wider than its container. The 320px shot shows titles for CW-69, CW-60, CW-97, CW-98 and CW-94.

## Leaves out

- New dashboard data or controls.
- Any change to how Gantt snapshots are collected.
- A tracker title fallback for Linear and Jira (no script-side adapter exists).
- Backfilling titles into the existing state file. The dashboard fallback shows them without a write.
- The status pane mod's own rendering. It reads the same `title` key, so it gains titles for new and rebuilt tickets from part 3, but its blank rows already in state stay blank.

## Calls I made

- **`title` becomes required on `start`.** The ticket asked the rebuild and adopt paths to pass it; making the script refuse a start without one is what makes "state stops having empty titles" true and testable. A start op without a title now fails instead of writing a blank.
- **`adopt N` gains a `get-ticket` on GitHub** to read the title, and writes nothing when that read fails.
- **The tracker read is GitHub only.** Linear and Jira rows with no state title show the ID alone.
- **Tracker reads run in the background**, one at a time, cached for the server's life, failures retried after 5 minutes. The first poll after start-up shows the ID alone for a few seconds.
- **The dashboard writes nothing to state.** The fallback titles live in the server's memory only.
- **Cards at every width**, in a responsive grid, instead of a table on wide screens. The Gantt keeps its table layout on wide screens through a container query, since the timeline columns read better side by side there.
- **Risk badge colour from the first word** of the risk text (`low`, `medium`, `high`, else grey), showing the whole risk text.
- Breakpoints: the Gantt table returns at a 48rem wide session card; body padding shrinks under 30rem.

## Touches

None of these: data, money, auth, user email, migrations. It changes the state file's `start` contract (a required field) and runs one more `gh` read per untitled ticket from the dashboard server.

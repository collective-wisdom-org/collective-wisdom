# CW-188: Tighten the dashboard header and add call-to-action badges

**Status:** Shipped
**Shipped:** in PR #192, as specified
**Ticket:** [#188](https://github.com/collective-wisdom-org/collective-wisdom/issues/188)
**Runs beside:** CW-187 (#187, merged as #189 before this PR) edited the same `page/index.html` and `page/app.js`. It removes the `Agents` `<h2>` and `#gantt` and adds a Merged list. I expect a small conflict in the body markup of `index.html` and rebase after it merges.

## Goal

The dashboard should waste less space under the `Agent team` heading and tell the user, at the top right, what needs them: merges and builds waiting for approval, and whether the build queue is empty.

## Today

Facts from `main` at `500408a`.

- `agent-team/scripts/dashboard/page/index.html` body: `<h1>Agent team</h1>`, `<p id="error" role="status">`, `<h2>Status</h2>`, `<div id="status">`, then `<h2>Agents</h2>` and `<div id="gantt">`.
- The gap under the heading is the `h1` bottom margin (`.75rem`), the empty error line (`#error { min-height:1.2em }`) and the `h2` top margin (`1.5rem`) plus its border and padding.
- `renderStatus(groups, open)` in `page/app.js` draws one section per group. `poll()` fetches `/api` every 5 seconds and rebuilds `#status` only when the status JSON changed.
- `/api` returns `status: { name, count, rows }[]` from `groupTickets` (`agent-team/.claude/mods/status-pane/hooks/groups.ts`). A group with no tickets is left out. The names this ticket reads: `Awaiting merge approval` (`awaiting-merge`), `Awaiting build approval` (`awaiting-build`, renamed by CW-177; the group name did not change) and `Queued to build` (`build-queued`).
- `index.html` defines `--b-high`/`--b-high-fg` (red), `--b-medium`/`--b-medium-fg` (yellow) and `--b-neutral`/`--b-neutral-fg`, each with a dark-mode value, and a `.badge` class with `risk-*` color variants.

## Builds

1. **Header row in `index.html`.** `<h1>` and a new `<div id="cta" aria-live="polite">` sit in a `<header>` that is a wrapping flex row: heading on the left, badges pushed right (`margin-left:auto`), `gap` between them. On a narrow pane the badges wrap onto the next line under the heading, still aligned right.
2. **Less space.** The `Status` `<h2>` goes. `#error` loses its `min-height` and hides when empty (`#error:empty { display:none }`), so an empty error line takes no space. The header's bottom margin is about `.5rem`, and the first group's `h3` top margin is trimmed so the first group sits right under the header.
3. **`renderBadges(groups)` in `app.js`**, a pure function next to `renderStatus`, exported for the test. It looks up each group by name and reads its `count` (a missing group is 0) and returns:
   - red (`badge cta-high`): `X threads awaiting merge approval`, only when X > 0;
   - yellow (`badge cta-medium`): `Y threads awaiting build approval`, only when Y > 0;
   - neutral (`badge`): `Z tickets in the build queue`, or `No tickets in the build queue` when Z is 0.
   One gives the singular: `1 thread awaiting merge approval`, `1 ticket in the build queue`. The order is red, yellow, neutral. The two new classes reuse the existing color variables, so dark mode follows.
4. **Poll.** `poll()` sets `#cta` from `renderBadges(last.status)` in the same branch that rebuilds `#status`, so the badges change on the next poll after the state changes, without a reload. On a failed fetch the last badges stay, as the cards do.
5. **Test.** One table-driven test in `page/app.test.js` covers 0, 1 and many for each badge, including a missing group, and checks the singular. It runs in the dashboard test command from `AGENTS.md`.

## Leaves out

- Clickable badges or scrolling to a group.
- Badges for other groups (Speccing, Building, Awaiting teammate review).
- Removing the `Agents` sub header (CW-187 does that).
- Any change to `api.ts` or the group definitions.

## Calls I made

- **The badges hide while the page loads and when `/api` has no state yet.** With no `status` list there is nothing to count, so `renderBadges` returns an empty string rather than `No tickets in the build queue`, which would be a guess. Once `/api` answers with a list, even an empty one, the queue badge shows.
- **Counts come from the group's `count`, looked up by group name**, not by counting row stages. That is what the ticket's Today section points at, and it keeps the badge equal to the pill next to the group heading.
- **The error line hides when empty** instead of keeping its reserved line. That is most of the saved space. The cost is that the content shifts down one line while a refresh error shows.
- **New classes `cta-high` and `cta-medium`** instead of reusing `risk-high` and `risk-medium`, so a future change to risk badges does not recolor the header. They use the same color variables.
- **`aria-live="polite"` on the badge container**, so a screen reader hears a count change. The ticket did not ask for it; it costs one attribute.
- **Badges render with the status block, not on every poll.** They are derived from the same JSON, so rebuilding them only when the status changed gives the same result.
- **Rebase on CW-187.** If it merges first, I keep its removal of the `Agents` heading and `#gantt`, its Merged list, and my header and removed `Status` heading.

## Touches

None of these: data, money, auth, user email, migrations.

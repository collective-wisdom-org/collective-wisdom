# CW-260: Show ticket helpers on the dashboard Chief of Staff tab

**Status:** Spec
**Ticket:** [#260](https://github.com/collective-wisdom-org/collective-wisdom/issues/260)

## Goal

The dashboard's Chief of Staff tab gets a second list, **Ticket helpers**, under the project manager list. Each row is one ticket helper thread (the one-shot `write-ticket` threads, observation helpers included) with its state, thread link and gantt, newest first. Finished helpers stay in the list the way finished project manager threads do.

## Today

- `teamRole` (`agent-team/scripts/dashboard/api.ts`) matches the Chief of Staff by state and project manager children by heading through `HEADINGS` (`BACKLOG RANKING`, `PROJECT MANAGER HYGIENE`). `TeamRole` is `'ranking' | 'hygiene'`. Any other root-checkout session is dropped.
- `buildApi` returns `pm`: project manager rows, live snapshots and history merged by `sessionId`, newest first.
- `history.ts` keeps role entries only for `ranking` and `hygiene` (`ROLES`), capped at 50 apart from the 500 ticket sessions.
- `renderChief` (`page/app.js`) draws the Chief of Staff card, a `Project manager` heading and ten rows per page with a pager (`data-pm-page`).
- A ticket helper is started by `delegate_task` with `isolation: "shared"`, so it runs in the root checkout. Its task's first line starts `TICKET HELPER.` (`agent-team/.claude/skills/chief-of-staff/ticket-helper.md`), and the mod's heading pick (`pickHeading`, `^[A-Z][A-Z ]{2,38}[A-Z]\.`) records `TICKET HELPER`. The observation helper's first line starts the same way.

## Design

### 1. Matching (`api.ts`)

- `TeamRole` becomes `'ranking' | 'hygiene' | 'helper'`, and `HEADINGS` gets `'TICKET HELPER': 'helper'`. The order of the role rule is unchanged: the Chief of Staff match comes first, so a Chief of Staff session is never a helper.
- `cleanTeamSnapshot` already keeps only root-checkout sessions, so a session in a ticket's worktree stays on the Ship loop tab whatever its heading.

### 2. API

- `buildApi` adds a third key, `helpers`, with the same row shape as `pm`: `{ sessionId, role: 'helper', state: 'running' | 'finished', threadLink?, gantt }`. Same merge of live and history by `sessionId`, same running test, newest `updatedAt` first.
- `pm` keeps only `ranking` and `hygiene` rows, so it reads exactly as today.

### 3. History (`history.ts`)

- `ROLES` gets `helper`, so a `{ role: 'helper', session }` entry parses and records like a project manager entry.
- Helpers get their own cap of 50, apart from the 50 project manager sessions and the 500 ticket sessions. A day of many helpers can then never push a project manager thread off the tab, or the other way round.
- `teamHistory` returns helper entries too, shown as finished. The server's loop already records whatever `teamSessions` returns, so it needs no change.

### 4. Page (`page/app.js`)

- `ROLE_LABELS` gets `['helper', 'Ticket helper']`.
- After the `Project manager` list, `renderChief` adds a `Ticket helpers` heading and the `helpers` rows, built by the same row code: role label, state badge, updated time, `Thread` button, gantt in a `<details>`. Ten per page with its own pager (`data-helper-page`), so paging one list does not move the other. Empty list: `No ticket helper threads yet.`
- Helper charts use `data-helper` on the `<details>` and chart body, are drawn from `helpers`, and stay open across polls the way project manager charts do.
- `renderChief` takes a second page number for the helper list and returns both clamped pages.

## Leaves out

- Telling an observation helper from a user-requested helper. Both show as `Ticket helper`.
- The helper's thread title or the ticket it wrote. The snapshot carries neither, and adding them means a mod change.
- The `Running` section of the Chief of Staff report.
- Any change to the agent-gantt mod, to how the Chief of Staff starts helpers, or to state.

## Calls I made (surprising first)

- **A second list, not one mixed list.** Project manager rows stay exactly as they are, and helpers, which run far more often, get their own heading, empty message and pager instead of crowding the project manager rows onto later pages.
- **A separate `helpers` key in the API**, not helper rows inside `pm`. The page then needs no filtering, and `pm` stays the same for anything that reads it.
- **Helpers get their own history cap of 50**, rather than sharing the project manager cap of 50.
- **The label is `Ticket helper`** for every helper, observation helpers included (the ticket puts telling them apart out of scope).
- Helper rows show no title. The page has no title for them without a mod change, which the ticket rules out.
- Sessions already on disk from before the mod recorded headings stay unmatched; nothing is backfilled.

## Tests

- `api.test.ts`: the CW-247 role table gets two rows, a root snapshot with heading `TICKET HELPER` (lands in `helpers`, not `pm`) and a worktree snapshot with that heading (stays off the tab). One check that `helpers` is newest first with a live snapshot and its older history copy merged.
- `history.test.ts`: the existing parse test gets a `helper` entry that survives; recording 51 helper sessions keeps 50 and drops no project manager or ticket session.
- `app.test.js`: the Chief of Staff tab test renders a helper row with the `Ticket helper` label and escaped fields, and the empty `No ticket helper threads yet.` message.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.

Proved by hand in the PR: a dashboard run from the worktree shows a ticket helper on the Chief of Staff tab while it runs, with a running badge, thread link and gantt, and it stays in the list as finished after it ends.

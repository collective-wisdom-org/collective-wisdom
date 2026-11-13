# CW-286 plan: ticket helpers on the Ship loop tab

Spec: `docs/superpowers/specs/2026-11-13-cw-286-helpers-on-ship-loop-design.md` (approved). Tests follow `AGENTS.md` § Testing: one table-driven test per rule.

## API contract (shared by tasks 2 and 3)

`/api` `status` gets these extra groups, after the state groups, in this order:

- `Writing tickets`: rows `{ id: 'helper:<sessionId>', title: <request or ''>, helper: true, risk: '', next: '', stage: '', threadLink?, gantt: [Session] }`, newest first.
- `Todo`, then `Backlog`: rows `{ id: '<PREFIX>-N', title, issueUrl, risk: '', next: '', stage: '' }`, tracker order.
- `Api.helpers` is removed. A snapshot may carry `ticket` (string|null) and `request` (string|null); `Session` gets `ticket?` and `request?`.

## Task 1: mod (`mods/agent-gantt/hooks/`: `snapshot.ts`, `snapshot.test.ts`, `register.tsx`)

- `snapshot.ts`: pure `pickFiledTicket(answer: string): string | null` (first `<PREFIX>-N` at the start of a line under `Tickets:` in a `TICKET HELPER DONE` block, stopping at the next `Key:` line; `none` gives null) and `pickRequest(text: string): string | null` (first non-empty line after `The user's request, verbatim:` or `The Chief of Staff's observation:`, whitespace collapsed, 80 chars). `buildSnapshot` takes and writes `ticket` and `request` (null when unknown).
- `register.tsx`: two atoms like `heading` (`ticket`, `request`). Set `request` in `prompt.submit` beside the heading, only when the heading is `TICKET HELPER` and not yet set. In `turn.complete` for the main loop (`e.agentId` absent), when the heading is `TICKET HELPER` and `ticket` is unset, `pickFiledTicket(e.answer)`; set once. Pass both to `buildSnapshot`.
- Test: one table for both parsers (one ticket, several, none, no block, text before the block).

## Task 2: dashboard data (`agent-team/scripts/dashboard/`: `api.ts`, `history.ts`, new `backlog.ts`, `server.ts` and their tests)

- `api.ts`: `cleanTeamSnapshot` reads `ticket` and `request`; add `prefix` check where used. `ledgerSessions` also returns a root-checkout `TICKET HELPER` session that has a `ticket` (as `{ ticket, session }`). `buildApi`: drop `helpers`; build the `Writing tickets` group from running helper sessions with no ticket; attach helper sessions (live and from history, merged by `sessionId`, live wins) to every ticket row they name, in `gantt` sorted oldest first; add `Todo` and `Backlog` groups from a new `backlog` input, skipping ids already in state or `merged`. `Api.pm` stays ranking and hygiene only.
- `history.ts`: drop the `helper` role and the helper cap; a helper session with a ticket is a ticket entry. Old `{ role: 'helper' }` entries are dropped on parse. Provide a way for `historyByTicket` to hand helper sessions to `buildApi`.
- `backlog.ts`: like `titles.ts`: `createBacklog({ run, now })` reads `issue list --repo <slug> --state open --limit 200 --json number,title,labels,author` through `gh.sh` at most once a minute in the background; `status:todo` is Todo, no `status:` label is Backlog, others skipped; author kept only when `api repos/<slug>/collaborators/<login>/permission --jq .role_name` is `triage|write|maintain|admin` (cached per login); a failed read keeps the last list; titles cleaned like `titles.ts`. GitHub tracker only.
- `server.ts`: wire it (only when the tracker is github and the slug is known), pass `backlog` into `buildApi`.
- Tests: `api.test.ts` one table for where a helper snapshot lands; `backlog.test.ts` parse, untrusted author, failed read; `history.test.ts` old helper entry dropped, replacing the helper-cap test.

## Task 3: page and README (`agent-team/scripts/dashboard/page/app.js`, `page/app.test.js`, `README.md`, any `page/*.html|css`)

- `renderChief`: drop the Ticket helpers heading, pager, `helperPage`, `data-helper` charts and the `helper` role label. Fix the callers.
- `ticket()`: a row with `helper: true` draws `Ticket helper` as its id, the request as its title, the copy button and the `Agents` chart; no issue link, no Details. Its chart key is its id.
- `BANDS`: add `Not started` after Queued, holding `Todo` then `Backlog` as flat rows; `Writing tickets` stays in In progress. `renderBadges` and the empty state keep working.
- README § Local dashboard: replace the Ticket helpers paragraph per the spec (§ 7).
- Tests: placeholder card and the Not started band (escaped fields); Chief of Staff tab has no helpers list.

## Verify

`python3 -I -m pytest -q agent-team/scripts` and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` (Node 24+).

# CW-387: Move the dashboard Backlog to its own tab and show a spec queue under Up next

**Status:** Draft
**Ticket:** [#387](https://github.com/collective-wisdom-org/collective-wisdom/issues/387)
**Related:** #369 (collapsible headers, merged), #370 (row cards), #371 (same page), #388 (tab count pills). Builds on #349 (Backlog paging) and #350 (Done tab).

## Goal

The spec queue gets a name, "Waiting to spec", in the Chief of Staff docs and on the dashboard. It lists the `spec-queued` tickets first, then the Todo tickets, under Up next. The Backlog moves to its own tab, so the Ship loop tab shows only work the team has taken on or will take next. No ticket changes state: a Todo ticket stays Todo while it waits.

## Today

Facts from main at `fa0f78e`.

- `groups.ts` puts `spec-queued` and `blocked` in one `Other` group, labelled "Blocked or waiting" by `GROUP_LABELS` in `app.js`.
- `buildApi` in `api.ts` appends a `Todo` group (tracker order) and a `Backlog` group (priority, then newest first) built from `BacklogItem`s, skipping any ticket in state or in the merged list. Each carries `readAt` and `stale` when read from the saved list file. Backlog carries `moreUrl`.
- `app.js` `BANDS`: Your turn, In progress, Up next (`QUEUED` = Queued to merge, Queued to build, Other), Not started (`NOT_STARTED` = Todo, Backlog). In progress takes every group name that is in none of the other lists.
- `renderStatus(groups, open, collapsed, info, backlogPage)` pages the `Backlog` group 10 rows at a time with Previous and Next buttons (`data-backlog-page`). `drawStatus` clamps `backlogPage` and redraws `#status` only when the status JSON or the page changed.
- `index.html` has three tabs: `tab-ship`, `tab-cos`, `tab-done`. `tabFromStorage` returns `cos`, `done` or `ship`. Arrow, Home and End keys move between `tabs` (every `[role=tab]`).
- `renderBadges` counts Up next as waiting, minus blocked rows. Not started is not counted.
- `cos_todo.py` tries Todo tickets by priority (Urgent, High, Medium, Low, none), then oldest `createdAt`, then list order, and drops `agent-skip` and tickets with an open blocker.
- Chief of Staff docs: `SKILL.md` § Lanes lists the Spec queue as "`spec-queued`, then Todo tickets". `status.md` § Status layout puts `spec-queued` under `Other`. `state-keys.md` says a Todo ticket stays in the tracker's Todo with no stage.

## Design

### The spec queue (Chief of Staff docs)

- `SKILL.md` § Lanes: the Spec row's Queue cell becomes "the spec queue: `spec-queued`, then Todo tickets", and one sentence under the table defines it: the tickets waiting for a spec slot, `spec-queued` in `queuedAt` order, then Todo tickets in `cos_todo.py` order. A Todo ticket in the queue stays in the tracker's Todo; joining the queue is not a stage or a state change.
- `status.md` § Status layout: a new group row `Waiting to spec | spec-queued (in queue spec: order)`, placed after Queued to build, and `Other` becomes `blocked` only. A rule line says the dashboard's Waiting to spec also lists the Todo tickets after these, and a `status` answer leaves them out (it makes no Todo read). The `Other` row rule drops "waiting for a spec slot"; a Waiting to spec row says `[changes requested, ]waiting for a spec slot`.
- `state-keys.md`: the `queuedAt` line's last sentence names the spec queue: a Todo ticket has no child yet, so it waits in the spec queue from the tracker's Todo, with no stage.

### API (`groups.ts`, `api.ts`)

- `groups.ts`: a new `{ name: 'Waiting to spec', stages: ['spec-queued'] }` after Queued to build. `Other` keeps `['blocked']`.
- `api.ts`: the Todo items no longer make a `Todo` group. They are sorted like `cos_todo.py` (priority rank, then oldest `createdAt`, no date last, then tracker order) and appended to the Waiting to spec group's rows, after its `spec-queued` rows. When no ticket is `spec-queued`, the group is created and placed where `groups.ts` would put it (after Queued to build, else after the last group before it in that order). Its `count` is all its rows. The Todo list's `readAt` and `stale` go on the group as today, and a stale note greys only the Todo rows (a `stale` flag on each Todo row, so the state rows stay black).
- The Backlog group is unchanged: same order, rows, `moreUrl`, `readAt` and `stale`.
- Status order now ends: … Queued to build, Waiting to spec, Other, Writing tickets, Backlog.

### Page (`app.js`, `index.html`)

- `QUEUED` = Queued to merge, Queued to build, Waiting to spec, Other. `NOT_STARTED` and the Not started band go. In progress still skips `Backlog` (it is in no band on the Ship loop tab).
- `GROUP_LABELS`: `Todo` goes; `Waiting to spec` needs no entry (the API name is the label).
- `renderStatus` keeps its signature but no longer draws the Backlog group or a pager. A new exported `renderBacklog(groups, collapsed, backlogPage)` draws the Backlog group exactly as `renderStatus` draws it today (the same `details.group[data-group="Backlog"]`, pill, rows, pager, stale note and "Full backlog" link), or `<p class="quiet">Nothing in the Backlog</p>` when there is none.
- `index.html`: a fourth tab after Done, `<button role="tab" id="tab-backlog" data-tab="backlog" aria-controls="panel-backlog" …>Backlog</button>`, and `<div id="panel-backlog" role="tabpanel" aria-labelledby="tab-backlog" hidden><div id="backlog">…</div></div>`. The existing keydown handler reaches it with no change.
- `tabFromStorage` returns `backlog` for a saved `backlog`.
- `drawStatus` writes `#status` from `renderStatus` and `#backlog` from `renderBacklog`, with the same clamp of `backlogPage` and the same "changed?" check. The pager click handler is unchanged, so the page number survives the 5-second poll.
- `renderBadges` is unchanged in code; because Waiting to spec is in Up next, its Todo rows now count as waiting in the header.
- A Todo row in Up next is drawn as a flat row like any Up next row (it has no stage, risk or next), with its issue link.

### Tests

One table-driven test per rule (`AGENTS.md` § Testing):

- `groups.test.ts`: a `spec-queued` ticket lands in Waiting to spec in `queuedAt` order, never in Other; a `blocked` one lands in Other.
- `api.test.ts`: the existing Todo and Backlog test becomes: Todo items join Waiting to spec after the `spec-queued` rows, in priority then oldest order; with no `spec-queued` ticket the group sits after Queued to build; no group is named `Todo`; Backlog is as before. The stale test reads the Waiting to spec group and checks only Todo rows carry `stale`.
- `app.test.js`: the bands table has no Not started band and the Ship loop html has no Backlog rows; a Todo row (no stage) shows only under Waiting to spec; `renderBacklog` draws the paged group with its pager and link (the existing Backlog paging cases move to it); `tabFromStorage('backlog')` is `backlog`. The badges case drops the `Todo` and `Backlog` groups it passes.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/groups.ts` | Waiting to spec group; Other is blocked only. |
| `agent-team/scripts/dashboard/api.ts` | Todo rows join Waiting to spec in `cos_todo.py` order; no Todo group. |
| `agent-team/scripts/dashboard/page/app.js` | Bands, labels, `renderBacklog`, `tabFromStorage`, `drawStatus`. |
| `agent-team/scripts/dashboard/page/index.html` | Backlog tab and panel. |
| `agent-team/scripts/dashboard/*.test.ts`, `page/app.test.js` | The tests above. |
| `agent-team/.claude/skills/chief-of-staff/SKILL.md`, `status.md`, `state-keys.md` | Name the spec queue. |

Proof: screenshots of the Ship loop tab with Waiting to spec holding a `spec-queued` and a Todo ticket and no Not started section, and the Backlog tab on page 2 of a long Backlog, light and dark, desktop and phone width.

## Non-goals

- How the Chief of Staff ranks, picks or starts Todo tickets, or the Spec lane limit.
- A new stage or `cos_state.py` rule.
- The Backlog's order, page size or row content.
- Row cards (#370) and tab count pills (#388).

## Calls I made

- **Todo rows now count in the header's "N waiting".** They sit in Up next, and `renderBadges` counts Up next. A team with a long Todo shows a bigger waiting number than today.
- **A `status` answer in the Chief of Staff thread shows Waiting to spec with the `spec-queued` tickets only.** Listing Todo there would add a tracker read to every `status`; `status.md` says the dashboard also lists the Todo tickets.
- **The dashboard lists every Todo ticket, including `agent-skip` ones and ones with an open blocker,** which `cos_todo.py` would skip. The dashboard does not read labels beyond status and priority or read relations; the order matches `cos_todo.py` otherwise.
- **Todo is ordered like `cos_todo.py` (priority, then oldest first),** not tracker order as today, so the list reads as the start order.
- **The Backlog tab is the fourth tab, after Done,** and has no count pill (#388 adds pills to tab labels).
- **The Backlog tab shows the same collapsible group block as today,** with its "Backlog" heading and pill, not a new band heading.
- **An empty Backlog shows "Nothing in the Backlog"** instead of an empty panel.
- **The Todo list's stale note stays on the Waiting to spec group** and greys only the Todo rows.
- **The saved collapsed key `band:not-started` and a saved `Todo` group key are left in storage unused;** nothing cleans them.

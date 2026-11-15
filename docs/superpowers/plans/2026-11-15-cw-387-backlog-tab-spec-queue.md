# CW-387 plan: Backlog tab and the spec queue

Spec: `docs/superpowers/specs/2026-11-15-cw-387-backlog-tab-spec-queue-design.md`

## Task 1: `agent-team/scripts/dashboard/groups.ts`

1. Add `{ name: 'Waiting to spec', stages: ['spec-queued'] }` after Queued to build; `Other` is `['blocked']`.
2. Export the group order so `api.ts` can place the group.

## Task 2: `agent-team/scripts/dashboard/api.ts`

1. Todo items no longer make a `Todo` group. Sort them like `cos_todo.py` (priority rank, oldest `createdAt` first, no date last, then tracker order).
2. Append them to the Waiting to spec rows after the `spec-queued` rows. With no `spec-queued` ticket, create the group after the last group that precedes it in the status layout.
3. `count` is all rows. The Todo list's `readAt` and `stale` go on the group; each Todo row gets `stale` when the list is stale, so the state rows stay black.
4. The Backlog group is unchanged. Update the `StatusRow` type.

## Task 3: `agent-team/scripts/dashboard/page/app.js` and `index.html`

1. `QUEUED` gains Waiting to spec. Remove `NOT_STARTED`, the Not started band, the `slim` flag and the `Todo` label. The Backlog group is in no band.
2. `renderStatus` no longer draws Backlog or its pager. New exported `renderBacklog(groups, collapsed, backlogPage)` draws the group as before, or `Nothing in the Backlog`. It takes optional `open` and `info` sets so a Backlog row keeps an open Agents panel.
3. `ticket` adds `stale` to a row's class. The row phrase for a `spec-queued` row now keys on the Waiting to spec group.
4. `tabFromStorage` accepts `backlog`. `drawStatus` writes `#status` and `#backlog` under the same clamp and changed check.
5. `index.html`: the Backlog tab and panel; `li.row.stale` greys like a stale group; the Backlog group's top margin sits flush in the panel.

## Task 4: Chief of Staff docs and README

1. `chief-of-staff/SKILL.md` § Lanes names the spec queue. `status.md` § Status layout gets the Waiting to spec row and the rule line. `state-keys.md` `queuedAt` line names the spec queue.
2. `README.md` § Local dashboard: three bands, the spec queue, four tabs.

## Task 5: tests, one table-driven test per rule

- `groups.test.ts`: `spec-queued` to Waiting to spec in `queuedAt` order; `blocked` to Other.
- `api.test.ts`: Todo joins Waiting to spec in priority then oldest order, group placement, no `Todo` group; stale reads the Waiting to spec group and only Todo rows carry `stale`; the helper-session case reads Waiting to spec.
- `server.test.ts`: the Linear case reads Waiting to spec.
- `app.test.js`: no Not started band, no Backlog on the Ship loop tab, a Todo row only under Waiting to spec, `renderBacklog` paging and link, `tabFromStorage('backlog')`, badges and labels without Todo.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `uvx pytest -q agent-team/scripts`.

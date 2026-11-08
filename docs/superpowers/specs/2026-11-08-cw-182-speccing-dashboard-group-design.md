# CW-182: Show tickets in the spec stage in their own dashboard group

**Status:** Draft
**Ticket:** [#182](https://github.com/collective-wisdom-org/collective-wisdom/issues/182)
**Runs beside:** CW-177 (#177) renames the `awaiting-spec` stage and touches the same files. This change does not depend on it.

## Goal

A ticket whose spec is being written shows under "Other" in the dashboard and the status pane. It should show under its own group, "Speccing", placed before "Awaiting build approval".

## Today

Facts from `main` at `84987a1`.

- `GROUPS` in `agent-team/.claude/mods/status-pane/hooks/groups.ts` puts `spec`, `spec-queued` and `blocked` in `Other`, the last group.
- The dashboard reuses `groupTickets` from that file (`agent-team/scripts/dashboard/api.ts`), and `page/app.js` prints each group's name as its heading. Neither the dashboard nor its tests name a group, so neither changes.
- `chief-of-staff/status.md` § Status layout lists the same groups in a table. Its `Other` row lists `spec`, `spec-queued` and `blocked`. Its sample block shows a spec-stage ticket under `**Other (1)**`, and its rules give `spec stage` as one reason an `Other` row can show.
- `groups.test.ts` expects `['Other', 2, ['CW-6', 'CW-5']]`, where CW-6 is in `spec` and CW-5 is `blocked`.

## Builds

1. **`groups.ts`**: a new group `{ name: 'Speccing', stages: ['spec'] }` right before `Awaiting build approval`. `Other` keeps `spec-queued` and `blocked`.
2. **`status.md` § Status layout**:
   - The group table gets a `Speccing | spec` row before `Awaiting build approval`. The `Other` row becomes `spec-queued` (in `queue spec:` order), `blocked`.
   - The sample block's spec-stage ticket moves from `**Other (1)**` to a `**Speccing (1)**` table, in the place the group order puts it. Its Next cell stays `Spec stage since 14:05, no SPEC READY yet.`
   - The `Other` reasons rule drops `spec stage` and keeps `blocked: <reason>` and `changes requested, waiting for a spec slot`, and adds `queued for a spec slot` for a `spec-queued` row.
3. **`groups.test.ts`**: the expected view gets `['Speccing', 1, ['CW-6']]` before `Building`, and `Other` becomes `['Other', 1, ['CW-5']]`. No new test: the existing table-driven test covers the group order and the stage mapping.

## Leaves out

- Renaming the `awaiting-spec` stage or its group (#177).
- How the Chief of Staff sets stages.
- A group for `spec-queued`. It stays in `Other`.
- The dashboard code and its tests. They take groups from `groupTickets` and need no change.

## Calls I made

- **`spec-queued` stays in `Other`.** The ticket allowed moving it if the name fits. "Speccing" says the spec is being written, and a queued ticket has no child yet, so it doesn't fit. A "Queued to spec" group would fit, but the ticket didn't ask for it.
- **The sample block in `status.md` changes too**, not just the table, so the example the Chief of Staff copies matches the new grouping. Its spec-stage row moves to a "Speccing" table.
- **The `Other` reasons rule changes.** `spec stage` no longer happens in `Other`, so it goes, and `queued for a spec slot` covers the `spec-queued` case that stays.
- **Rebase on CW-177.** If CW-177 merges first, the conflict is in neighbouring lines of `GROUPS`, the status table and the test. I keep both changes: their renamed group and stage, plus the new `Speccing` group before it.

## Touches

None of these: data, money, auth, user email, migrations.

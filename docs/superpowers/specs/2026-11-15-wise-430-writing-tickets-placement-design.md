# WISE-430: Writing tickets at the top of the Backlog tab, titled by the ticket

**Status:** Draft
**Ticket:** [#430](https://github.com/collective-wisdom-org/collective-wisdom/issues/430)

## Goal

A running ticket helper shows on the dashboard's Backlog tab, in a Writing tickets section above the Backlog list, and no longer on the Ship loop tab. Each entry is titled with a short description of the ticket the helper is writing, not the first line of the user's message.

## Today

Facts from main at `a1ab8ed`.

- `buildApi` in `agent-team/scripts/dashboard/api.ts` pushes a `Writing tickets` group (one `helper: true` row per running helper with no filed ticket) with `title: i.session.request ?? ''`.
- In `page/app.js`, that group name is in no `NEEDS_YOU` or `QUEUED` list and is not `Backlog`, so the In progress band of `renderStatus` draws it. `renderBacklog` draws only the `Backlog` group, and returns `Nothing in the Backlog` when there is none. `tabCounts` counts it in `ship`; `renderBadges` counts it in `in progress`.
- `pickRequest` in `mods/agent-gantt/hooks/snapshot.ts` returns the first non-empty line after `The user's request, verbatim:` or `The Chief of Staff's observation:`, whitespace collapsed, cut to 80 characters. Both hook paths call it on the helper's first prompt: `register.tsx` (Claude Code) and `cursor.ts` (Cursor). The snapshot stores it as `request`; `cleanTeamSnapshot` passes it through when it is 80 characters or fewer (`REQUEST_MAX`).
- `chief-of-staff/ticket-helper.md` titles the helper thread `Ticket: <3 to 6 words from the user's message>`, and its template has no line describing the ticket.

## Design

### Helper template (`agent-team/.claude/skills/chief-of-staff/ticket-helper.md`)

- The template gets one new line right after `Run /write-ticket ...`: `Writing ticket: <a short description of the ticket, under 80 characters>`. The Chief of Staff writes it from the user's message, describing the ticket (for example `Move Writing tickets to the Backlog tab`), not quoting the message.
- The thread title becomes `Ticket: <3 to 6 words describing the ticket>`.
- Observation helpers carry the same line (their template differs only as listed in § Observation tickets, so nothing changes there). Their `Observed: <3 to 6 words>` title stays.

### Hook (`mods/agent-gantt/hooks/snapshot.ts`)

- `pickRequest` first looks for a line starting `Writing ticket:` **above** the request marker. When it has text after the colon, it returns that text, whitespace collapsed and cut to 80 characters. Otherwise it returns the request line, as today.
- Only lines above the marker count, so a `Writing ticket:` line inside the user's own message cannot set the title.
- The snapshot field stays `request`, and `api.ts` and `cleanTeamSnapshot` do not change: the row title is still `session.request`, which now holds the description when there is one.
- Bump `mods/agent-gantt/.claude-plugin/plugin.json` from `0.1.13` to `0.1.14`.

### Page (`agent-team/scripts/dashboard/page/app.js`)

- The In progress band no longer takes `Writing tickets`: `renderStatus` never draws it, and `tabCounts.ship` and the header sentence no longer count it.
- `renderBacklog` draws the `Writing tickets` group first, as its own collapsible section with its own count pill, then the Backlog section as today. The Writing tickets section is not paged and its cards get no Mark todo button.
- With helpers running and no Backlog group, the tab shows the Writing tickets section and then `Nothing in the Backlog`.
- `tabCounts.backlog` stays the Backlog group's count only.

### Docs

- `README.md` and `docs/compatibility.md`: the helper card sits in a Writing tickets section at the top of the Backlog tab and is titled with the ticket description, or the request line when the task has none.

### Tests

- `snapshot.test.ts`: extend the `pickRequest` table: a description line wins; an empty description line falls back to the request line; a `Writing ticket:` line below the marker is ignored; the description is collapsed and cut to 80.
- `page/app.test.js`: one table-driven test: `renderStatus` with a Writing tickets group draws no helper card; `renderBacklog` draws the Writing tickets section before the Backlog section, and alone with `Nothing in the Backlog` when there is no Backlog group; `tabCounts` leaves the helper count out of `ship` and `backlog`. Update the existing tests that expect the card on the Ship loop tab.
- `api.test.ts` needs no change: the API shape is the same.

## Leaves out

- Showing finished helpers, or how a helper's session joins the ticket it filed.
- A new snapshot field: the description reuses `request`.
- Cursor and Claude Code helpers that were already running when this ships keep their request-line title.

## Calls I made

- **The Ship loop tab's count and header sentence drop helpers.** Today a running helper adds 1 to the Ship loop count and to `N in progress`; after this it adds to neither, and the Backlog count stays the Backlog list only (the ticket says keep it off both).
- **The description reuses the `request` field instead of a new one.** `pickRequest` prefers the description, so `api.ts`, `cleanTeamSnapshot` and the snapshot shape stay as they are. A new field would touch the hook, the API and the page for the same result.
- **The line reads `Writing ticket: <description>` and sits above the request block.** It is matched only above the marker, so text in the user's message cannot fake it.
- **Observation helpers get the description too**, since they use the same template; their `Observed:` thread title stays.
- **Writing tickets is a separate collapsible section on the Backlog tab**, with its own count, unpaged and with no Mark todo button (a helper has no ticket number).

## Touches

None of: data, money, auth, user email, migrations.

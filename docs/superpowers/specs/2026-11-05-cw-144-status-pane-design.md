# CW-144: status pane

**Status:** Shipped
**Shipped:** in PR #146, with differences: [as-built](../as-built/2026-11-05-cw-144-status-pane-as-built.md)
**Ticket:** [#144](https://github.com/collective-wisdom-org/collective-wisdom/issues/144)

## Goal

A pane beside the chat that shows what the Chief of Staff `status` answer shows, redraws when state changes, and links every ticket row to its child thread and every listed subagent to its transcript.

## Today

- `status` is an answer in the Chief of Staff thread only (`agent-team/.claude/skills/chief-of-staff/status.md`). To see it again you ask again.
- The data is `.agent-team/state.json` (`scripts/cos_state.py show`). A ticket holds `stage`, `childThreadId`, `status` (its `Risk: ...` tail is the risk), `pr` and the queues.
- State stores a thread ID, not a link. T3 links look like `t3-thread://v2/<environment id>/<thread id>`; the environment ID is not in state.
- `install.sh` `shipped()` syncs `.claude/skills`, `.claude/agents`, `scripts` and `docs/agents`. Nothing ships a Claude Code mod.

## Design

### The mod

A Claude Code mod named `status-pane`, shipped at `agent-team/.claude/mods/status-pane/` with the standard layout (`.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/register.tsx`). It registers a `/status-pane` command that opens a `Pane` and opens it on `session.start` only when the option `autoOpen` is on (default off).

### Reading state

A pure function `groupTickets(state)` in `hooks/groups.ts` turns the parsed state into the groups of `status.md` § Status layout, in that order, with empty groups dropped and the count in each header. Queued groups follow the `queue` order in state. Each row has ticket ID, title (the ID alone when no title is known), risk (the text after `Risk:` in `status`, else `not rated yet`), Next (the `status` text before the `Risk:` tail) and `childThreadId`.

The pane reads the state file with `$.fs` every 5 seconds (`$.clock.every`) and redraws only when the file's `mtimeMs` changed. A missing, empty or half-written file shows `No state yet.` and keeps the last good view; it never throws out of the hook.

### Links

- Ticket cell: `**CW-N** title`, then a `Link` whose `href` is `t3-thread://v2/<environmentId>/<childThreadId>` built from the `environmentId` option. A row with no `childThreadId`, or no `environmentId` set, shows no link.
- Subagents: every entry of `$.agent.list()` that belongs to this session is listed under the table as `Subagents (n)`, each row a `Button` whose `onPress` calls `$.ui.view({ agentId })`, which puts that subagent's transcript in the main view. A final `Back to main` button calls `$.ui.view({})`.

### Install

`install.sh` `shipped()` adds `.claude/mods` to its list, so `--update` copies and drift-checks the mod like skills. `agent-team/docs/agents/status-pane.md` says how to turn it on and how to find the environment ID (it is the middle part of any thread link T3 prints).

## Tests

- `agent-team/scripts/test_status_pane.py` asserts the install copy rule only: a fresh `install.sh` install and an `--update` both carry `.claude/mods/status-pane/`.
- `groups.test.ts`, run with `claude plugin test`, one table for the grouping: stages in several groups, queue order, empty groups dropped, missing `childThreadId`, a `status` with no `Risk:` tail, malformed input.

## Leaves out

- Pending-approval blocks, the sweep and the idle check: the pane shows state as the Chief of Staff last wrote it.
- Acting from the pane (approve, cancel).
- Cost (`$X so far`) and tracker titles on the first version if they need a call per refresh; titles come from `state` when present, else the ID alone.

## Calls I made

- **Thread links need the T3 environment ID.** State has none, so it is a mod option (`environmentId`), not read from T3. Without it the rows show IDs and no links. The alternative is for the Chief of Staff to store a `link` per ticket in state, which changes `cos_state.py` and its skill; I left that out.
- **The mod ships under `agent-team/.claude/mods/`**, which is a new directory, so `install.sh` changes.
- **It is off by default** (`/status-pane` opens it) so installing the team does not change anyone's screen.
- **Subagents link through `$.ui.view`**, not a URL: that is how the mod API opens a subagent.
- **Tracker titles and cost are skipped** to keep the pane free of network calls on a timer.
- **Poll every 5 seconds** with an `mtimeMs` check rather than a file watcher.

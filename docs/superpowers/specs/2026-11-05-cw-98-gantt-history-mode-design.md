# CW-98: A history mode for the Gantt pane, from saved transcripts

**Ticket:** [CW-98](https://github.com/collective-wisdom-org/collective-wisdom/issues/98)
**Status:** Draft
**Related:** #96 (the live pane, shipped in PR #149), #97 (open an agent from its row)

## Goal

The Gantt pane from #96 shows only this session's agents, from the moment the mod loaded. History mode shows past threads too: every saved Claude Code session of this repo in the last 7 days, its subagents under it, and the cost of each ticket. A Live / History toggle in the pane switches between the two, and `/gantt` opens the pane straight in History.

## Today

Facts from `main` at `e91b9a4`, checked 2026-11-06. Nothing under `mods/agent-gantt/` or `agent_usage.py` changed between `58db4e8` and `e91b9a4`.

- `agent-team/scripts/agent_usage.py` reads every session under `~/.claude/projects` whose dir name contains the main checkout's name (`PROJECT`), plus the subagent transcripts in `<session>/subagents/agent-*.jsonl`. `read_session()` returns the branch, first user text, relays, priced requests and the session's first and last event times. `costs()` prices each request from `PRICES` (loaded from `prices.json`), with the 1h/5m cache split when the transcript has it.
- `ticket_line()` gives the `--ticket CW-N` line: all-time cost, tokens, spec/build/merge split, child run count and wall time, over worktree sessions whose transcript has a line with `"gitBranch":"feat/cw-N-` (or `feat/cw-N"`), plus their subagents. `cos_brief.py` calls it through the command line. Output is text only.
- Each subagent has an `agent-<id>.meta.json` beside its transcript with `agentType`, `description` and `spawnDepth`. It names no parent agent, so a nested subagent can't be placed under the agent that started it.
- On a full machine (323 project dirs, 1.3 GB of transcripts) the default report over this repo runs in about 2.5 s; `--ticket` in 0.2 s.
- The mod (`mods/agent-gantt/`, version `0.1.0`) keeps per-agent records in `$.state` atoms and draws them with `buildRows()` from `rows.ts`, using the `Row` type #96 made for this ticket. It registers `/agent-gantt`, which opens the pane. The header is one line of column names; there are no buttons.
- Mod API, from this build's types:
  - `$.process.run(argv, { cwd, timeoutMs })` runs a host command (no shell) in the session's working directory and returns `{ exitCode, stdout, stderr }`, each cut at 4 MiB. Timeout is 30 s by default, ten minutes at most. CLI only.
  - `$.fs.read` and `$.fs.list` take absolute paths too, so the mod could read `~/.claude/projects` itself. It would then have to price and group in TypeScript.
  - `$.store.get/set` keep JSON across sessions, 4 MiB in all for the mod.
  - `$.ui.copy({ text, surface })` puts text on the clipboard of the surface a Button press came from (`press.surface`).

## Design

### One place computes cost: `agent_usage.py --json`

> ⚠️ The mod runs the Python script; it does not read transcripts itself. See Calls I made.

New flag `--json` prints one JSON object and exits. It honours `--since`, `--until` and `--projects`.

```json
{
  "version": 1,
  "repo": "collective-wisdom",
  "since": "2026-10-29T12:00:00Z",
  "until": "2026-11-05T12:00:00Z",
  "rows": [
    {
      "id": "a0889adc-…", "parentId": null, "sessionId": "a0889adc-…",
      "name": "feat/cw-96-agent-gantt-pane", "repo": "collective-wisdom",
      "branch": "feat/cw-96-agent-gantt-pane", "ticket": "CW-96",
      "start": 1762340000000, "end": 1762342340000,
      "tokens": 12900000, "cost": 6.48, "childCount": 3
    },
    {
      "id": "a08e5e74516f8f317", "parentId": "a0889adc-…", "sessionId": "a0889adc-…",
      "name": "Apply pass 2 fixes", "repo": "collective-wisdom",
      "branch": "feat/cw-96-agent-gantt-pane", "ticket": "CW-96",
      "start": 1762341000000, "end": 1762341200000,
      "tokens": 800000, "cost": 0.41, "childCount": 0
    }
  ],
  "tickets": [
    { "ticket": "CW-96", "cost": 6.48, "tokens": 12900000,
      "spec": 1.10, "build": 5.10, "merge": 0.27, "runs": 2, "wallMinutes": 39 }
  ]
}
```

Rules:

- **Which sessions.** Every session `agent_usage.py` already reads (root checkout and worktree dirs of `PROJECT`) whose first-to-last event span overlaps the window. A session with no priced request gets no row.
- **One row per session**, `parentId` null. `id` and `sessionId` are the session's file stem. `name` is the branch for a worktree session, else `root ` plus the first user message cut to 40 characters, as the text report labels them. `childCount` is its number of subagent transcripts.
- **One row per subagent**, `parentId` the session's id, `id` the `agent-` file stem without the prefix, `name` its meta `description` (else its `agentType`, else the id). All subagents sit one level under their session, since the meta names no parent agent. `childCount` is 0.
- `start` and `end` are the first and last event times in ms since epoch. `tokens` and `cost` cover the whole session or subagent, not just the part inside the window. `cost` is the sum of `costs()` over its requests, so the 1h/5m split applies. A session row's own tokens and cost exclude its subagents' (they have their own rows).
- `repo` is `PROJECT` on every row: the script reads only this repo's transcripts.
- `ticket` is the upper-cased `<prefix>-N` from the session's branch when it matches `feat/<prefix>-N` or `feat/<prefix>-N-...`, else null. A subagent takes its session's.
- **`tickets`** lists each ticket that appears on any row, with its all-time totals. They come from the same function `ticket_line()` now formats: `ticket_line()` is split into `ticket_totals(projects, ticket)`, which returns the numbers, and the formatting of its line. So the History totals and `--ticket CW-N` can't differ. `--ticket` output doesn't change.
- **Errors.** When the `--projects` folder is missing or can't be listed, `--json` (and only `--json`, so the text report keeps working as today) prints `agent_usage: no readable transcript folder at <path>` to stderr and exits 2. An unreadable single transcript is skipped, as today.

### The pane: Live and History

- **Header.** A row of Buttons above the column names: `Live`, `History`, and, in History, `Refresh`. The current mode is marked. In History the header also says when the data was read (`read 14:02`) and the window (`last 7 days`).
- **Mode** is a `$.state` atom, `mode: 'live' | 'history'`, default `live`. Live draws exactly what it draws today.
- **History run.** Opening History (the Button or `/gantt`) and `Refresh` run `python3 scripts/agent_usage.py --json --since <now − 7 days>` with `$.process.run`, `timeoutMs` 120 s. The result is kept in `$.store` under `history`: `{ at, payload }` on success, `{ at, error }` on failure. The pane draws the stored value at once, so a reopen shows the last read while the new one runs, with `reading…` in the header.
- **Failure.** A missing `scripts/agent_usage.py`, an exit other than 0 (with the last stderr line), output that doesn't parse or has a `version` other than 1, or `$.process` being unavailable each show one line in History, such as `History unavailable: agent_usage: no readable transcript folder at /Users/x/.claude/projects`. The Live atoms are separate, so Live keeps working.
- **Ticket totals.** Above the rows in History, one line per ticket, newest first: `CW-96  $6.48  12.9M tok  2 runs  spec $1.10 / build $5.10 / merge $0.27`.
- **Rows.** A new pure `historyRows(payload)` in `rows.ts` turns the payload into `Row[]` plus each top-level row's session id. Order: sessions newest first; each followed by its subagents by start. Depth 0 for sessions, 1 for subagents. The same drawing code draws them, with one change: in History the start column shows date and time (`11-05 14:02`), since the rows span days. The time axis runs from the earliest start to the latest end.
- **Session id.** Under each top-level History row, a dim line with the full session id and a `Copy` Button that calls `$.ui.copy({ text: sessionId, surface: press.surface })` and shows `Copied` or the reason it didn't take via `$.ui.toast`.
- **`/gantt`** is a new command: it sets the mode to History, opens the pane and starts a History run. `/agent-gantt` stays and opens the pane in whatever mode it was left in.
- `plugin.json` version goes to `0.2.0`, or to `0.3.0` if #97 merges first (it also bumps to `0.2.0`).
- The README's Agent pane section gets a short paragraph: the Live / History toggle, `/gantt`, the 7 day window, and that History needs `python3` and the agent team's `scripts/` in the repo.

### Tests

- `test_agent_usage.py`: one table-driven test of `--json` over a fixture `--projects` folder: a worktree session on `feat/cw-7-x` with one subagent lands under ticket `CW-7` with the subagent's `parentId` set to the session; a root-checkout session and a worktree session on a non-ticket branch each still get a row with `ticket` null; the `tickets` entry's cost equals the dollars in `ticket_line()` for `CW-7`; a missing `--projects` folder exits 2 with the message.
- `rows.test.ts`: one table-driven test of `historyRows`: order and depth, and the error for output that isn't JSON or has the wrong `version`.
- The buttons, the copy and the `$.process` call get no automated test; they are checked by hand (see Proof).

### Proof

The PR's Proof section shows History in a real session: a screenshot with ticket totals, a session with subagents under it, and the session id line; the CW-N total next to the output of `scripts/agent_usage.py --ticket CW-N`; and a screenshot of the message with `--projects` pointed at a missing folder (by a temporary edit, not shipped), with Live still drawing after it.

## Out of scope

- Jumping to another T3 Code thread from a row.
- Changing how cost is priced.
- Opening an agent's transcript from a row (#97). History rows are past sessions, not agents of this session, so #97's row press doesn't apply to them.
- Nesting a subagent under the subagent that started it (the transcripts don't say which).
- A window picker; History always shows 7 days.
- Other repos' sessions in one view.

## Calls I made

- ⚠️ **The mod runs `agent_usage.py --json` through `$.process.run`** instead of reading `~/.claude/projects` with `$.fs` and pricing in TypeScript. This keeps cost in one place, as the ticket asks, and gets the 1h/5m cache split the live pane can't. The cost: History needs `python3` and the agent team's `scripts/` in the session's repo, and it doesn't work where `$.process` doesn't (CLI only); there it shows the unavailable message.
- ⚠️ **Overlap with #97** (its spec is on `feat/cw-97-open-agent-from-gantt-row`, not yet built). Both change `mods/agent-gantt/hooks/register.tsx`, the `plugin.json` version and the README's Agent pane section. #97 makes each row's info columns a `plain` Button that calls `$.ui.view`, draws a `← main` Button as the pane's first line only while an agent is in view, and bolds the row in view; this adds the Live / History / Refresh Buttons, the History rows and the session id line. Whichever merges second rebases onto the other and takes the next version (`0.3.0`). #97's row press, `← main` line and bold row stay on Live rows only; History rows are plain text, since they are past sessions with no agent to view.
- ⚠️ **History shows the last 7 days, fixed.** The ticket gives no window; all time would mean thousands of rows on a busy machine. Ticket totals are still all-time, so they match `--ticket`.
- A session's row cost covers the whole session, even the part before the window.
- A session row's cost excludes its subagents; the ticket line includes them.
- All subagents sit one level under their session, since the meta files name no parent agent.
- `/gantt` is added beside `/agent-gantt` rather than renaming it.
- The History result is kept in `$.store` (across sessions), so a new session shows the last read at once; the mode is per session in `$.state`.
- The session id line shows the full id under each top-level row rather than a cut id in the row, so it can be read and checked against the copy.
- A missing transcript folder is an error only for `--json`; the text report keeps printing an empty report as today.

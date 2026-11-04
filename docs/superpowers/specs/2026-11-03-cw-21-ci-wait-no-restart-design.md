# Stop the Chief of Staff restarting children that are only waiting on CI (design)

**Status:** Shipped
**Ticket:** [CW-21](https://github.com/dbeallor/collective-wisdom/issues/21)
**Shipped:** in PR #34
**Branch:** `feat/cw-21-ci-wait-no-restart`

## Intent

T3 shows a child's run as `completed` while the child is only waiting on a background command. The Chief of Staff's stuck check reads that as a stall, restarts the child, and on a second "stall" marks the ticket `blocked`. In fathom on 2026-11-03, all four restarts (GUY-320, 317, 296, 297) were false alarms, and GUY-296 was blocked while its child was alive and waiting on CI. Fathom fixed this in GUY-328 (dbeallor/fathom#273). This ports that fix into `agent-team/`.

Source: fathom's `docs/superpowers/specs/2026-11-03-ci-wait-restarts-design.md` and `scripts/cos_idle_check.py`, read at the #273 merge commit `1a0581dca5120b39aca13ae63d90044f3e81e391`. The fathom names (`ihag-chief-of-staff`, `ihag-ship-loop`, GUY-N) become `chief-of-staff`, `ship-loop` and `<PREFIX>-N`.

## What is here today

Checked on `main` at 388dab1 (CW-11 has merged):

- `agent-team/scripts/cos_idle_check.py` has only the list-of-small-reads mode. No `--wait`.
- `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Full pass step 3 says a `completed` run with no marker is stuck, and "Text about waiting is no exception: a finished run without a marker is always a stall."
- `agent-team/docs/agents/chief-of-staff.md` § Done when: "A child whose run ends without a marker is restarted in the turn its notice arrives."
- `agent-team/.claude/skills/ship-loop/SKILL.md` § Team mode tells a child to call `t3_background_wait` and says ending the turn after it is fine ("Run endings", "CI waits"). It has none of the three child rules below.

CW-11 added nothing that overlaps this ticket, so the whole fathom fix is ported.

## How T3 behaves (from the fathom investigation)

The child starts `wait-for-ci.sh` as a background command, calls `t3_background_wait` (the output lists the task ID under `matched`), and ends its turn. T3 sets the run to `completed` at that moment. When the command exits, T3 posts a notification item and starts a new run. Between the two runs, nothing in `recentRuns` or the thread status shows that a wake is pending. The only sign is the `t3_background_wait` call among the last run's items.

If the command was started with `&` inside the shell command instead of the tool's background option, the harness has no task to track, and `t3_background_wait` returns the ID under `unmatched`. Nothing will ever wake that child.

## Design

### 1. `cos_idle_check.py --wait`

```
python3 scripts/cos_idle_check.py --wait <PREFIX>-N [--now ISO] < read.json
```

Reads one raw `t3_thread_read` result (activity view) on stdin. Does not read state.

- **`waiting`, exit 0:** `recentRuns[0].status` is `completed`, the items of that run (`runId` equal to `recentRuns[0].runId`) include a `dynamic_tool` item for a tool whose name ends in `t3_background_wait` with at least one ID under `matched`, and `recentRuns[0].completedAt` is at most 45 minutes before `--now`. Prints `waiting <PREFIX>-N on <ids>, run ended HH:MM`.
- **`stalled <reason>`, exit 1:** any other readable input. Reasons: `no-wait` (no wait call in that run, including a wait only in an earlier run), `unmatched` (wait calls, none with a matched ID), `wait-expired Nm` (matched, but the run ended more than 45 minutes ago).
- **Exit 2:** can't judge. Unparseable stdin, no `recentRuns`, no run ID, run not `completed`, no `completedAt`, or a wait call whose text was cut off before the `matched` list. Prints `cos_idle_check: <reason>`.

Item shape, as fathom's as-built parses it: the item's `text` is the JSON of the call (`toolName`, `output`). Matched IDs come from `output.structuredContent.matched`, or from `output.content` parsed as JSON. When `text` is cut off (not valid JSON) but shows the tool name, a visible `"matched": ["…` (plain or escaped) counts as matched, and no visible match is "can't tell" (exit 2), not `unmatched`.

The 45 minutes is the script's existing `IDLE_AFTER`. The existing mode (no `--wait`) does not change.

### 2. `chief-of-staff` SKILL.md § Full pass step 3 (Stuck check)

Sections touched: § Full pass step 3 only, the second stuck bullet and the "For a stuck child" list. Nothing in § Lean turns, § Sweep, § Slot fill or § Approval requests changes.

The `completed`-with-no-marker bullet becomes: stuck unless the wait check says `waiting`. Before treating it as stuck:

- Read the child's last 10 items: `t3_thread_read` with `view: activity`, `afterPosition: max(0, itemCount - 10)`, `limit: 10`, `runLimit: 1`, `maxCharsPerItem: 1500`. Pass the result to `python3 scripts/cos_idle_check.py --wait <PREFIX>-N` on stdin through a quoted heredoc.
- `waiting` (exit 0): not stuck. No restart, `restarts` unchanged, no report line. Its next run-finished notice or the next idle check looks again.
- `stalled` (exit 1): stuck under the current rule. Restart if `restarts[stage]` is 0, otherwise `blocked`. The `blocked` status quotes the `stalled` line.
- Exit 2: read once more. Still 2: restart when `restarts[stage]` is 0, but never mark `blocked` on it, and add the Cleanup line `<PREFIX>-N wait check unreadable; not blocked`.

The sentence "Text about waiting is no exception: a finished run without a marker is always a stall." is removed. A ticket is blocked for a stall only on a `stalled` line (or a `failed`/`interrupted` run, or a `running` child idle over 45 minutes, which don't change).

The § Lean turns idle check already sends a `completed` child to a full read (`full … not-running`), and that runs step 3, so a child that stays waiting is checked again on each pass. Cost: one activity read per waiting child per pass.

### 3. `agent-team/docs/agents/chief-of-staff.md` § Done when

The line becomes: "A child whose run ends without a marker is restarted in the turn its notice arrives, unless it is waiting on a background command."

### 4. `ship-loop` SKILL.md § Team mode

Sections touched: the "Run endings" and "CI waits" bullets only.

- "Run endings": after `t3_background_wait`, T3 shows the run as `completed`, and the Chief of Staff tells a waiting child from a stalled one by that call. Make the wait one of the last few tool calls before ending the turn, because the Chief of Staff reads only the last 10 items. Start the background command with the tool's background option, never with `&` in the command. If `t3_background_wait` lists the ID under `unmatched`, nothing will wake you: start the command again and wait again, and never end a turn on an unmatched wait.
- "CI waits": add "If `t3_background_wait` lists the task ID under `unmatched`, start the script again and wait again."

### Tests

One table-driven test for `--wait` in `agent-team/scripts/test_cos_idle_check.py`, from trimmed copies of real read shapes:

| Case | Exit | Line starts |
|---|---|---|
| completed run, matched wait, ended 5 min ago | 0 | `waiting` |
| completed run, matched wait, ended 50 min ago | 1 | `stalled … wait-expired` |
| completed run, wait with only `unmatched` | 1 | `stalled … unmatched` |
| completed run, no wait call | 1 | `stalled … no-wait` |
| matched wait in an earlier run only | 1 | `stalled … no-wait` |
| unparseable stdin | 2 | `cos_idle_check:` |

The builder may add a row for the cut-off text case if the parser handles it, since that is the path that keeps a truncated read from blocking a ticket.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- The Chief of Staff skill, `chief-of-staff.md` and the ship-loop skill say the same thing about a waiting child (manual read).

## Leaves out

- The 45-minute limit for a `running` child with no thread activity.
- Lost finish notices (done in CW-11).
- Any change to T3.
- The install PR in apps, which follows once this merges.
- Undoing any `restarts` counts or blocks already in an app's state.

## Calls I made (surprising first)

- **I port fathom's as-built parser, not only its spec.** The merged fathom script also handles a wait call whose text was cut off by `maxCharsPerItem`: a visible match counts, and no visible match is exit 2 instead of `unmatched`. The ticket doesn't list this case. Without it, a long wait output cut off at 1500 characters would read as `unmatched` and could block a ticket that is fine.
- **The § Lean turns run-finished sentence is left alone.** It says step 3 runs "so a run that ended without a marker is restarted in that turn". That stays true in effect (step 3 now decides), and leaving it keeps this diff away from a paragraph PR #26 and CW-12 also touch. The role doc line is the one the ticket names, and it gets the "unless" clause.
- **An unreadable wait check allows a restart but never a block.** A restart is the cheaper mistake; without it, a child whose reads keep failing would sit forever.
- **Any matched wait in the last run counts**, not only a wait on `wait-for-ci.sh`. A review or other background command wakes the child the same way.
- **A matched wait counts as waiting for 45 minutes after the run ends,** reusing `IDLE_AFTER`. CI waits take 5 to 7 minutes in fathom.
- **`--wait` is a flag on `cos_idle_check.py`, not a new script.** It reuses the time parsing and the 45-minute constant, and the ticket names this file.
- **The child rule says "one of the last few tool calls", not "the last".** That matches the ticket and fathom's merged wording; the Chief of Staff reads 10 items and the wait was within the last 4 in every fathom case.

## Overlap with other open work

PR #26 (CW-17), CW-12, CW-14, CW-15 and CW-16 also edit `chief-of-staff/SKILL.md` or `chief-of-staff.md`. This change touches only: SKILL.md § Full pass step 3 (second stuck bullet and the "For a stuck child" list), `chief-of-staff.md` § Done when (one line), and ship-loop SKILL.md § Team mode "Run endings" and "CI waits" bullets.

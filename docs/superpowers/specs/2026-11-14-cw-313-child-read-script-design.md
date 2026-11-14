# CW-313: Read child threads through a script that prints a short result

**Status:** Shipped
**Shipped:** in PR #320, with differences: [as-built](../as-built/2026-11-14-cw-313-child-read-script-as-built.md)
**Ticket:** [#313](https://github.com/collective-wisdom-org/collective-wisdom/issues/313)
**Related:** #314 (thread-start load)

## Goal

A Chief of Staff turn that reads a child takes a few short lines into its context instead of whole messages. A new script reads the child's newest assistant message and run status from T3's local store and prints the marker, the fields the stage op needs and the next position. The idle check, the `Running` list and the wait check read the same store. Every path falls back to today's `t3_thread_read` when the store can't be read.

## Today

Facts from `main` at `bb4bd36`.

- `cos_tick.py` `read_line()` prints `read <T> <child> afterPosition=<p> limit=5 runLimit=1 maxCharsPerItem=2000` once per active child on a full pass and for the notice's own child. That is up to 10,000 characters a read.
- `idle_lines()` prints one `idle-read <T> <child>` per other active child (a `t3_thread_read` with `limit: 1`), and the model passes the results as JSON on stdin to `cos_idle_check.py`.
- The wait check (`SKILL.md` § Child path, Stuck check) reads 10 activity items at 1,500 characters each and pipes them into `cos_idle_check.py --wait`.
- Every report that ran the idle check makes a `t3_thread_list` call with `limit: 100` for the `Running` sub-lines (§ Report format).
- `cos_sweep.py` prints every part's lines and then its summary line.
- `cos_user_check.py`, `cos_peer.py`, `no_hands.py` and `cos_approve_pr.py` read `~/.t3/userdata/statev2.sqlite` with `mode=ro` and exit 2 with `schema changed` on any `sqlite3.Error`.
- The store has what the reads use: `orchestration_v2_projection_threads` (`updated_at`, `provider_instance_id`, `payload_json.lineage.parentThreadId` and `relationshipToParent`, `title`), `orchestration_v2_projection_runs` (`status`, `completed_at`, `ordinal`, `payload_json.delegatedCompletion`), `orchestration_v2_projection_messages` (`role`, `streaming`, `run_id`, `payload_json.text`), `orchestration_v2_projection_turn_items` (`type`, `run_id`, `payload_json`, including `dynamic_tool` items) and `orchestration_v2_turn_item_positions` (`ordinal` per item).
- `t3_thread_read`'s own description says "Reading a child's final result marks it delivered". Runs carry `delegatedCompletion.disposition` (`open`, `disposed`) and subagent rows carry `completion_delivery_state` (`delivered`, `acknowledged`, `disposed`).
- A thread `link` is `<t3-thread://v2/<environment id>/<thread id>>`.

## Design

### 1. `cos_child_read.py`

New script in `agent-team/scripts/`, read-only, same `query()` shape as `cos_user_check.py` (`--db`, default `~/.t3/userdata/statev2.sqlite`, opened `mode=ro`).

```
cos_child_read.py [--db PATH] <PREFIX>-N <childThreadId> [--after POSITION]
```

It reads the thread row, its newest run, and the newest finished (`streaming = 0`) assistant message of that run, at a position after `--after`. Output, one fact per line:

```
child CW-5 run=completed updated=2026-11-14T10:02:00Z provider=claudeAgent next=84 item=turn-item:message:<id>
marker BUILD READY
field specPath=docs/superpowers/specs/x.md specSha=<40 hex> branch=feat/cw-5-x
block:
<the marker block>
```

- `marker` is `BUILD READY` (an old `SPEC READY` counts), `MERGE READY`, `BLOCKED`, `MERGED`, or `none`. It is looked for the way § Child path says: in the last assistant message of a finished run. A `running` run prints `marker none`. No new assistant message after `--after` prints `marker none new=0`.
- `field` lines carry what the stage op needs: `specPath`, `specSha` and `branch` (from `Spec:`, `Commit:` and the `Link:` url's `/blob/<branch>/` part) for `BUILD READY`; `pr` and `headSha` (from `PR:` and `Head:`) for `MERGE READY`; `pr` for `MERGED #N`. A field that fails its pattern (the `cos_handoff.py` patterns for path and SHA, `[A-Za-z0-9._/-]+` for a branch, digits for a PR) prints as `<name>=?`, and the Chief of Staff reads that item in full.
- `block:` is followed by the marker block only (the marker line to the end of the message), for `BUILD READY`, `MERGE READY` and `BLOCKED`. The approval request is built from it (approvals.md § Approval requests), so it can't be dropped. Each line is cut at 200 characters and the block at 1,500. Past that, a last line `cut <item> at <offset>` names the item and `textOffset` for a full read.
- `marker none` on a `completed` run prints `tail:` and the message's last 400 characters, enough for `cos_restart.py --step`. The Chief of Staff reads the whole item only when the tail doesn't say what step finished.
- `next` is the position a `t3_thread_read` would return as `nextPosition`, so `lastPosition` keeps the same meaning and a fallback read still pages from it. The build checks the script's number against one real read.
- Exit 0 with output. Exit 2 with `cos_child_read: schema changed` on any `sqlite3.Error` or a missing column, and `cos_child_read: thread not found` when the thread row is missing.

### 2. Tick lines

`cos_tick.py` `read_line()` prints `child-read <T> <child> afterPosition=<p>`. The plan line table in `SKILL.md` says: run `python3 ~/.collective-wisdom/scripts/cos_child_read.py <T> <child> --after <p>`, then § Child path from its lines. Exit 2: the old `t3_thread_read` with today's limits, and one Cleanup line, `Child read script unavailable; used thread read`.

§ Child path reads the marker, fields and block from the script's lines, saves `next` as `lastPosition` and `provider` when it differs. The full message is opened (`t3_thread_read` with `itemId`) only for a `BLOCKED` block that is cut, a `field …=?`, a `cut` line, or a tail that can't settle `--step`.

### 3. Delivered mark

`t3_thread_read` marks a child's final result delivered. The build checks what depends on that: it records a finished child's `delegatedCompletion` and `completion_delivery_state` before and after a script-only turn and looks for a repeat notice or an unsettled thread. If nothing changes or nothing depends on it, no read is kept. If something does, the `child-read` plan line keeps one `t3_thread_read` with `itemId: <item>` and `maxCharsPerItem: 1` on the item the script names, which sets the mark at one character.

### 4. Idle check from the store

`cos_idle_check.py --store [--db PATH] [--skip T ...]` reads each active ticket's `childThreadId` from state and its newest run status, the thread's `updated_at` and `provider_instance_id` from the store, and prints the same `ok` and `full` lines it prints today. A `provider <T> <provider>` line shows when the store's provider differs from the saved one, so the `set` op can follow.

Each `ok` line gets up to 5 sub-lines, newest first: `  sub <title> <link>` for threads whose `lineage.parentThreadId` is that child and whose `relationshipToParent` is `subagent`. The title has `[`, `]` and newlines dropped. This replaces the `t3_thread_list` call in § Report format. The `ok` line also ends with the child's link.

The link needs T3's environment id. The build looks for it in T3's local store or config. If it isn't there, the Chief of Staff saves it once to state as `t3EnvironmentId`, taken from the `link` of any read, and the script reads it from state; with no saved id the lines print the thread id and the report uses the old `t3_thread_list` call.

`cos_tick.py` `idle_lines()` prints the one `run … cos_idle_check.py --store [--skip T]` line and no `idle-read` lines. On exit 2 the model falls back to today's `idle-read` reads and the stdin form, which stays.

### 5. Wait check from the store

`cos_idle_check.py --wait <T> --store <childThreadId>` reads the last run and its last 10 `dynamic_tool` turn items from the store and judges them with today's `wait_calls()` and `check_wait()` rules. The activity read leaves the thread's context. Exit 2 from the store falls back to today's activity read on stdin.

### 6. Shorter sweep

`cos_sweep.py` prints only the lines that need action and its last line. A part's line needs action when its first word is one the Chief of Staff acts on in `each sweep line` or `each full: read` (`merged`, `ready`, `pushed`, `full`, `untracked`, and the review check's `approved`, `changes`, `moved` and `closed` lines), or when it is a part's own failure line (`cos_<name>…: …`). Summary and `ok` lines of the parts are dropped. `--verbose` prints everything, as today.

### 7. Docs

`SKILL.md` § Tick (plan line table: `child-read`, the idle check line), § Child path, § Lean turns Reads, § Report format (`Running` sub-lines) and § Sweep change to match. § Tools lists `cos_child_read.py`.

### 8. Tests

One table-driven test for `cos_child_read.py` against a small SQLite file built in the test with the store's columns: each marker, a bad field (`=?`), a cut block, `none` with a tail, a running run, nothing new after `--after`, a missing table (exit 2) and a missing thread (exit 2). One table-driven test for `--store` in `cos_idle_check.py` (an `ok` child with sub-lines, a `full` idle child, a store error exit 2). The tick and sweep tests change their expected lines. No test for prose.

## Leaves out

- When and how the Chief of Staff rotates.
- Splitting `SKILL.md` into a core and on-demand files (#314).
- The `pending` line (`t3_pending_request`): its result is already small.
- Other thread reads (the Moved-to check, the rebuild reads, the user-check fallbacks).

## Calls I made

- The marker block still reaches the context on `BUILD READY`, `MERGE READY` and `BLOCKED`, cut at 1,500 characters, because the approval request and the blocked report are built from it. Turns with no new marker or with `MERGED` add a few hundred characters; an approval turn adds up to 1,500, against up to 10,000 today.
- A `completed` run with no marker prints the last 400 characters of the message, not the whole message, for `--step`.
- The delivered mark is checked during the build; one 1-character read stays only if something depends on it.
- The idle check, `Running` list and wait check move into `cos_idle_check.py` (`--store`) rather than the new script, since their rules already live there.
- If T3's environment id isn't in its local files, the Chief of Staff saves it once to state as `t3EnvironmentId` from a read's link.
- `cos_sweep.py` gets `--verbose` for the full output, so tests and a hand run can still see every part.
- New script name: `cos_child_read.py`; tick line name: `child-read`.
- The stdin forms of `cos_idle_check.py` stay, as the fallback.

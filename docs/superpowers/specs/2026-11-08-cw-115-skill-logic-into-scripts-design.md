# CW-115: Move more skill logic into scripts to shrink the files agents load

**Ticket:** [CW-115](https://github.com/collective-wisdom-org/collective-wisdom/issues/115)
**Status:** Shipped
**Shipped:** in PR #190, with differences: [as-built](../as-built/2026-11-08-cw-115-skill-logic-into-scripts-as-built.md)

## Goal

Cut prose where an agent follows fixed steps to a fixed answer, and give it a script that prints the answer instead. The skill keeps one line per step ("run the script, act on its line") and keeps the prose where the agent has to judge. Scripts read and print. They make no T3 call and no tracker write.

## Today

Measured on `main` at `2309ea5`, 2026-11-08, with `wc -c` (bytes; the files are almost all ASCII, so bytes and characters differ by a few dozen at most).

| File | Bytes |
|---|---|
| `chief-of-staff/SKILL.md` | 85424 |
| `ship-loop/SKILL.md` | 23928 |
| `open-pr/SKILL.md` | 19456 |
| `project-manager/SKILL.md` | 16659 |
| `merge-pr/SKILL.md` | 10254 |
| Total | 155721 |

The Chief of Staff's ten sibling reference files add 82033 bytes (`rotation.md` 15382, `approvals.md` 12804, `setup.md` 11825 and seven smaller ones).

The ticket's numbers are from 2026-11-04. The Chief of Staff skill grew from 63 KB to 85 KB since.

### Overlap with CW-60 and CW-177

- **CW-60** (`cos_tick.py`, spec awaiting approval on `feat/cw-60-cos-tick-script`) replaces `chief-of-staff/SKILL.md` § Full pass, § Slot fill and § Lean turns' Notice turns and Idle check bullets, and moves the stuck check, the restart message and the rate-limit wake into new § Child path and § Rate limit sections. It also puts the lane limits in a script. Those sections hold about 22 KB of the skill's 85 KB, and they are where most of its computing prose lives.
- **CW-177** (rename `awaiting-spec` to `awaiting-build`, building on `feat/cw-177-rename-awaiting-spec`) changes the stage name in `cos_state.py`, `approval_policy.py`, `cos_ready_check.py`, the status-pane groups and lines across the Chief of Staff (21 lines), project-manager, ship-loop and kickoff-feature skills. On its branch it also renames the `SPEC READY` marker to `BUILD READY` in ship-loop § Phases 1 and § Run endings.

This ticket takes none of the CW-60 sections and none of the lines CW-177 renames. Where they meet:

- CW-60's plan line `head-check <PREFIX>-N pr=<N> head=<sha>` points at § Send or queue's head check. This ticket scripts that head check (pick 2). The bold label `**Head check for a merge approval**` stays, so CW-60's pointer still lands, and its plan line can call the new script.
- CW-60 keeps the `project-manager` § Backlog pick as the step `start-todo` runs. This ticket scripts the Dry ranking test inside it (pick 4) and leaves the step order alone.
- `project-manager/SKILL.md` § Backlog ranking step 4 names `awaiting-spec`, which CW-177 renames. This ticket doesn't edit that step.
- CW-177 edits ship-loop § Phases 1, § Run endings and § Approvals, not § Phases 4, where pick 1 cuts. In § Send or queue it edits the queued-relay paragraph and the caller table, not the head check paragraph pick 2 cuts.
- Whichever of the three merges last rebases; the overlap is neighbouring lines, not the same lines.

## Design

Five picks. Each gets a script (new or extended) with a table-driven test on fixture input, and a cut in the skill.

### 1. Pre-`MERGE READY` review check: `review_gate.py` (ship-loop)

Today `ship-loop` § Phases "4. Security review" has a 1586-byte paragraph that tells the child how to check, before `MERGE READY`, that the latest `## Code review` and `## Security review` comments both end in PASS with no push after them, when a head moved by a target merge keeps its reviews (find the head of the older review, run `pr_diff_delta.py`, post the reviews-stand note), and when to rerun both.

New `agent-team/scripts/review_gate.py <N>`, run from the worktree. It reads `pr view <N> --json comments,commits,headRefOid` and the `gh` login, and reuses `merge_pr.review()` and `merge_pr.stands()` so the child's check and the merge gate can't drift apart. One last line:

| Line | Meaning |
|---|---|
| `review-gate: pass head <sha> code <url> security <url>` | Both reviews stand at the head. Use the URLs in `MERGE READY`. |
| `review-gate: note head <sha> reviewed <sha>` then the note text on the line before | The head moved only by merging `<target>` and the PR diff is unchanged (`pr_diff_delta.py` says `same`). Post the printed note with `gh.sh pr comment`, then run the script again; it then prints `pass`. |
| `review-gate: rerun <code\|security\|both>: <why>` | A review is missing, not PASS, or stale. Run it on the current head. |
| `review-gate: ci` | `Review mode` is `ci`; the check doesn't apply. |
| exit 2, `review-gate: cannot <what>` | A read failed. Run it once more, then `BLOCKED:`. |

The note text is exactly the one `merge_pr.py`'s `NOTE` pattern accepts today. The conflict-resolution note stays in `open-pr` § Conflict resolution: it has its own setting and run, and `merge_pr.py` already checks it.

The paragraph becomes two sentences: after `wait-for-ci.sh` passes on the head, run `review_gate.py <N>` and act on its last line; `MERGE READY` needs `pass` at the current head. The rest of § Phases 4 (the conflict-resolution case, the `MERGE READY` block, `ci` mode) stays.

### 2. Merge approval head check: `cos_head_check.py` (chief-of-staff)

Today § Send or queue's **Head check for a merge approval** (1079 bytes) tells the Chief of Staff to read `headRefOid,mergeable`, read `Review after conflict resolution` from `origin/<target>` with a `python3 -c` line, compare with the stored `headSha`, and pick one of three relays.

New `agent-team/scripts/cos_head_check.py <PREFIX>-N [--no-approval]`. It reads the ticket's `pr` and `headSha` from state, `pr view <pr> --json headRefOid,mergeable` and the setting from `origin/<target>` (`project_config.review_after_conflict()`). It prints one action line, then the relay to send (exact text, with the full and short SHAs filled in):

| Line | Meaning |
|---|---|
| `head-check: ok` | Head unchanged and not conflicting. Go on. |
| `head-check: moved <old> <new>` | Withdraw (comment, Needs you) and send the printed head-moved relay to the build lane. |
| `head-check: conflict keep` | Setting `off`: keep the approval, send the printed conflict relay with the approval to the merge lane. |
| `head-check: conflict withdraw` | Setting `on`, or `--no-approval`: withdraw (when there was an approval) and send the printed conflict relay without one to the build lane. |
| exit 2, `head-check: cannot <what>` | State, `gh` or the setting couldn't be read. Don't send; tell the user under Needs you. |

`--no-approval` is the `approve N` on `awaiting-review` case in § Commands, which uses only the moved-head part and never carries an approval. The comments, the Needs you lines and the sends stay in the skill. The relay texts move from the paragraph into the script, which is now their one source; § Send or queue keeps the merge approval relay and the caller table.

### 3. Hygiene rules: `pm_hygiene.py` (project-manager)

Today `project-manager/SKILL.md` § Cleanup "Priority and labels" (801 bytes), § State drift (702) and § Stale tickets (955) spell out filters and comparisons the hygiene child works through by hand.

New `agent-team/scripts/pm_hygiene.py` with three subcommands. Each reads `.agent-team/state.json` (`tickets`, `merged`, `pm`) and JSON on stdin from the calls the child already makes, and prints one line per ticket to act on. None writes state or the tracker.

- `fill`: stdin is the change check's `list-tickets` result. For each ticket in Backlog, Todo, In Progress or In Review that is not in `tickets`, prints `<ID> fill: <fields>`, the empty fields among `priority`, `area` and `type` minus those in `pm.filled[<ID>]`. `area` is listed only when `project.md` § Areas and labels names area labels (not `none`). The child still picks the values and judges when the title doesn't settle them.
- `drift --since <pm.lastCheckAt>`: stdin is `{"prs": [...], "tickets": {...}}`. The first run passes the change check's PRs with `tickets` empty and gets a `get <ID> #<PR>` line for each PR that could move its ticket (merged after `--since`, or opened after it and still open), matched by `<prefix>-N` in `headRefName` or `(<PREFIX>-N)` in the title. The second run adds the `get-ticket` results (`state`, `labels`) and prints `move <ID> Done (PR #X merged)` or `move <ID> In Review (PR #X open)`, with the `agent` label rule (skipped unless in `merged`, and then only Done).
- `stale`: stdin is the In Progress and In Review lists. For each ticket not in `tickets` whose `updatedAt` is over 3 days old, it makes the PR search and branch commit reads itself (`gh.sh`, GET only, the branch name checked against `^[A-Za-z0-9._/-]+$`), takes the newest of the three times, and prints `stale <ID> <state> since <date>` when that is over 3 days old and differs from `pm.flaggedStale[<ID>]`.

The three sections shrink to the calls to make, the script line, the write per line, and the report line. "Read the description only when the title doesn't settle it", "add labels with `add-label`, never by rewriting the set" and "never Urgent" stay.

### 4. Dry ranking test: `cos_rank.py dry` (project-manager)

Today § Backlog pick step 4 (1822 bytes with its list) lists six conditions, from state and from two reads, that decide whether a pick that ran out of `ready` tickets runs a new ranking.

New subcommand `cos_rank.py dry [--out-of-date]`. `--out-of-date` is step 2's finding this turn (a ranked ticket that moved, got `agent-skip`, a blocker, or was held). It checks, in order: `pm.rankedAt` null or malformed, `pm.rankedReady`, `--out-of-date`, a `merged` entry after `pm.rankedAt`, and (only with a `held` entry and a well-formed `pm.rankedAt`) the closed-PR read, which it makes itself. It prints one line:

- `dry: rank (<reason>)`: run § Ranking child now.
- `dry: check backlog since <pm.rankedAt>`: make the one `list-tickets` (state Backlog, updated since that time, limit 1, fields `id`). A ticket back means rank; none means the Backlog is dry.

The tracker call stays with the agent, since it goes through the tracker adapter. Step 4 keeps "at most one ranking per turn" and the cost note, and drops the condition list.

### 5. Merge gate list: `merge_pr.py` docstring (merge-pr)

Today `merge-pr` § Pre-merge checks has a 1484-byte sentence listing every check `merge_pr.py` runs, followed by "Do not repeat them by hand". The agent never runs those checks; it only acts on the script's stop line.

Move the list into `merge_pr.py`'s docstring (which already says it runs "the checks list of the merge-pr skill") and cut the skill to: the script runs the gate and stops with one line naming the cause; act on that line; don't repeat the checks by hand; a non-mergeable PR or red checks sends you back to `open-pr`. The § Gate rules, the `ci` mode paragraph and "Closeout in PR" stay, because the agent acts on them before running the script. No check changes.

### Left in prose, and why

- **Stuck check, restart message, rate-limit wake delay and `rateLimitResumes`** (§ Full pass steps 3 and 4): CW-60 moves this text to § Child path and § Rate limit. Scripting it here would rewrite the same lines twice. A follow-up after CW-60 merges can script the wake delay (the 3-minute and 6-hour bounds).
- **§ Slot fill and the lane limits**: CW-60's `cos_tick.py`.
- **§ Commands, § Report format, § Sweep's line table**: they route a command or a line to an action. The routing is the judgment; the computing parts (`cos_user_check.py`, `cos_sweep.py`) are already scripts.
- **`open-pr`**: its one fixed computation, the review scope, is already `review_scope.py`. The rest (conflict answers, review findings, the docs check) needs judgment. It is measured, not cut.
- **§ Hygiene pass step 3's clean-up of finished tickets and § Duplicates**: the first needs a list of finished tickets that no call returns today; the second compares titles and descriptions, which is judgment.

### Size targets

Measured with `wc -c` after the build, in the PR body for every file touched plus the total:

| File | Smaller by at least |
|---|---|
| `chief-of-staff/SKILL.md` | 500 bytes |
| `ship-loop/SKILL.md` | 900 bytes |
| `project-manager/SKILL.md` | 2000 bytes |
| `merge-pr/SKILL.md` | 900 bytes |
| Those four together | 4500 bytes |

The Chief of Staff margin is small because the sections where most of its computing prose lives belong to CW-60.

### Tests

Per `AGENTS.md` § Testing, one table-driven test per script on fixture input, with `gh` reads stubbed the way `test_merge_pr.py` and `test_cos_review_check.py` stub them:

- `test_review_gate.py`: pass, rerun (missing, CHANGES NEEDED, pushed after), note on a target merge with an unchanged diff, rerun on a changed diff, reviews on different heads, `ci` mode.
- `test_cos_head_check.py`: ok, moved, conflict with `off`, conflict with `on`, `--no-approval`, unreadable state.
- `test_pm_hygiene.py`: `fill` (empty fields, `pm.filled`, ticket in `tickets`, no area labels), `drift` (both runs, the `agent` rule, an old merge), `stale` (fresh, old, already flagged, unsafe branch name).
- `cos_rank.py dry` rows added to `test_cos_rank.py`'s table (new rows only; no existing test edited).

`test_section_pointers.py`, `test_call_sites.py` and `test_agent_files.py` must still pass.

## Acceptance

- The PR body has the before and after size of every file it touched and the total, and meets the size targets above.
- Every new or extended script has a table-driven test on fixture input.
- `python3 -I -m pytest -q agent-team/scripts` and shellcheck pass. No existing test is edited to make it pass.
- Every approval gate, merge gate, repo invariant, state-file command and Chief of Staff user command is still stated in the skill or enforced by the script that replaced the prose.
- No script makes a T3 call or a tracker write.
- The PR says why each left-out candidate stayed prose.

## Calls I made

- Five picks, none in the sections CW-60 rewrites, so the Chief of Staff skill shrinks by only about 600 bytes. The stuck check and the rate-limit wake, which the ticket named, are left to a follow-up after CW-60, since CW-60 moves that text.
- Sizes are bytes from `wc -c`, not characters. The ticket said characters; for these files the difference is a few dozen.
- `review_gate.py` posts nothing. It prints the reviews-stand note and the child posts it, so the post stays a visible step in the child's run.
- `review_gate.py` reuses `merge_pr.py`'s review functions instead of writing its own, so it and the merge gate can't disagree.
- The head check's relay texts move into `cos_head_check.py`. The merge approval relay and the spec relays stay in § Send or queue.
- `pm_hygiene.py stale` and `cos_rank.py dry` make their GitHub reads themselves (GET only, as `cos_sweep.py` does). The Backlog `list-tickets` stays with the agent because it goes through the tracker adapter, which may be Linear or Jira.
- `pm_hygiene.py drift` runs twice, before and after the `get-ticket` reads, instead of taking a tracker call it can't make.
- The merge-pr check list moves into the `merge_pr.py` docstring instead of being deleted, so someone reading the gate can still find it in one place.
- `open-pr` is measured but not cut.
- Pointers stay put: no heading that another file names is renamed or removed.

## Leaves out

- Any change to a rule, gate, lane limit, model default or command.
- `cos_tick.py` and the sections it replaces (CW-60).
- The stage rename (CW-177).
- The compacter agent (CW-72) and the vendored security skills.
- The Chief of Staff reference files (`rotation.md`, `approvals.md` and the rest).

## Touches

None of data, money, auth, user email or migrations. It changes how the hygiene child, the ship-loop child and the Chief of Staff reach a few fixed answers. The merge gate in `merge_pr.py` is unchanged; only its docstring grows.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.
- `wc -c` on the touched files meets the size targets.
- Each script run by hand against a copy of a real state file or a real PR prints what the old prose says.

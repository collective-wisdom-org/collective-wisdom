# CW-133: Detect tickets in flight that local Chief of Staff state doesn't know about

**Ticket:** [CW-133](https://github.com/collective-wisdom-org/collective-wisdom/issues/133)
**Status:** Draft

## Goal

When the tracker shows a team ticket in flight that `.agent-team/state.json` on this machine has never heard of, the sweep says so, the Chief of Staff tells the user, and the ticket joins state only when the user says `adopt N`.

## Today

Facts from `main` at `59c9b12`, checked 2026-11-05.

- `.agent-team/state.json` is gitignored, one copy per machine. `chief-of-staff` SKILL.md § State file calls it a cache.
- `startup.md` § State rebuild runs only when `cos_state.py show` exits 2. Take over and resume mode (`rotation.md` § Thread rotation, take-over step 4) read only tickets already in state.
- `cos_sweep.py` runs three parts: the merged check, the ready check and the parent check. All three start from `state["tickets"]`, so a ticket that was never in state is never seen.
- The GitHub adapter (`trackers/github.md`) maps `<PREFIX>-N` to issue `#N`, In Progress to label `status:in-progress`, In Review to `status:in-review`, and Done and Canceled to a closed issue.
- `cos_state.py start` needs `childThreadId`, `firstTaskId` and `parentThreadId`, so state can't hold a ticket that has no child thread.
- Seen on 2026-11-05 after a rotation: state had no record of CW-125 (open PR #132, `status:in-review`), CW-126 (`status:in-progress`, no PR yet) and probably CW-58 (open PR #131).

## Change

### New `agent-team/scripts/cos_untracked_check.py`

Read only. Usage: `cos_untracked_check.py [--file STATE] [--open-prs FILE] [--issues FILE]`. The file options read the GitHub JSON from files, for tests.

Inputs:

- State: `tickets` and `merged` keys. Missing or unreadable state is a `fail`, as in the other parts.
- Open PRs: one `./scripts/gh.sh pr list --repo <repo> --state open --limit 50 --json number,headRefName`. A PR counts when its branch starts with `<branch head><prefix lower>-N-` (the ready check's `branch_prefix` rule), which gives its ticket `<PREFIX>-N`.
- Issues, only when `project_config.tracker()` is `github`: one `./scripts/gh.sh issue list --repo <repo> --state open --label agent --limit 100 --json number,labels`.

A ticket is untracked when it is not a key of `tickets` or `merged`, and:

- GitHub tracker: its issue is in the open `agent` list, not labelled `agent-skip`, and has `status:in-progress` or `status:in-review` or an open PR on its branch. A PR whose issue is not in that list (closed, not `agent`) is ignored.
- Linear or Jira tracker: it has an open PR on its branch. The script can't read those trackers, so a ticket with no PR yet is not found (see Calls I made).

Output, one line per untracked ticket in ticket order, then a summary:

```
untracked CW-125 in-review #132
untracked CW-126 in-progress
untracked CW-58 #131
untracked-check: 3 not in state
```

The state word is `in-review` or `in-progress` from the furthest `status:` label (GitHub only; left out when the issue has neither). `#N` is the lowest open PR number on the ticket's branch, left out when there is none. A branch name that fails the `BRANCH` pattern used by the other checks is skipped. No title, body or author text is printed.

On failure (no repo row, gh failed or timed out, bad JSON, unreadable state) it prints only `cos_untracked_check: <what>` and exits 2. Otherwise exit 0 when nothing is untracked, 1 when something is.

### `agent-team/scripts/cos_sweep.py`

- A fourth part, `untracked`, after the parent check, through the existing `part()` wrapper. It reads the state as the merged check left it, so a ticket that just merged is in `merged` and is not listed.
- It reuses `--open-prs FILE` and adds `--issues FILE`.
- Its lines print like the other parts. When it lists anything, the last line gains `; untracked: CW-125 #132, CW-126, CW-58 #131` before any `; didn't run:`. With nothing untracked the last line is unchanged, so its existing readers keep working.
- Exit: untracked tickets count toward exit 1, the same as `read in full` and `merged`. A failed part still gives 2 and `didn't run: untracked`.

### `agent-team/.claude/skills/chief-of-staff/SKILL.md`

- § Sweep: name the fourth part and its line. For each `untracked` ticket, one `t3_thread_list` (`includeSubagents: true`, `titleContains: "<PREFIX>-N"`) for a child thread on this machine. Report the tickets in one Needs you line per ticket: `<PREFIX>-N in flight but not in my state (in review, PR #132; child <link>|no child thread on this machine). Another machine's Chief of Staff may own it. Say adopt <PREFIX>-N to take it here.` The line goes in any report the turn posts (full pass, take over, resume, status); untracked lines alone never make a run-finished turn post. The list call is skipped when the turn posts nothing. Nothing is written and nothing is started for an untracked ticket.
- § Sweep exit 2 fallback for `untracked`: no fallback; don't say every in-flight ticket is known.
- § Commands: new row `adopt N`, checked with `cos_user_check.py latest` like `approve N` (short words, strict check). It runs § Adopt below.
- New § Adopt:
  1. Re-run `cos_untracked_check.py`; if the ticket is not listed (state has it now, or it left flight), say so and stop.
  2. `get-ticket` with the adapter's author check. An untrusted author: say so and stop.
  3. `t3_thread_list` for its child as in § Sweep. Exactly one child thread: read it and set the stage as `startup.md` § State rebuild says (the same `SPEC READY` / `MERGE READY` / unsure-is-`blocked` rules), then write it with one `cos_state.py apply` (`start` with that thread's `parentThreadId`, then `stage`). The parent check then lists it as `old-parent` for a full read, as for any rebuilt ticket. More than one child thread: adopt the newest and say which.
  4. No child thread on this machine: write nothing. Reply that it can't be adopted here, and that the user can run the team on the machine that owns it, or `cancel` it there and move it back to Todo to restart it.
  5. Report under Moving: `<PREFIX>-N adopted at <stage>`. The turn's § Slot fill runs; the ticket's stage may put the count over the cap, which `startup.md` § State rebuild already allows.
- § Tools: add `cos_untracked_check.py` to the Bash list.

### `agent-team/.claude/skills/chief-of-staff/rotation.md` and `startup.md`

- Take-over step 4.2 and § Thread rotation: Resume mode: after the sweep, untracked lines are reported as § Sweep says, before the slot fill. Take-over step 5's line gains `<M> in flight but not in my state: <PREFIX>-125, <PREFIX>-126.` when any.
- `startup.md` § State rebuild: no change to what a rebuild does. One sentence: after a rebuild, the sweep's untracked part covers tickets the rebuild could not place.

### `agent-team/.claude/skills/chief-of-staff/status.md`

Untracked tickets get one line below the tables, like `Merged:`: `Not in my state: CW-125 (in review, #132), CW-126 (in progress).`

### Tests

- `agent-team/scripts/test_cos_untracked_check.py`: one table-driven test over state, issues and open PRs, GitHub tracker: an `agent` + `status:in-review` issue with an open PR and not in state is listed with exit 1; the same ticket in `tickets`, in `merged`, or labelled `agent-skip` prints no line and exits 0; a closed issue with an open PR is not listed; an `agent` issue with `status:in-progress` and no PR is listed without `#N`. One more row with the tracker set to `linear` through `PROJECT_MD`: an open PR on an agent branch not in state is listed.
- `test_cos_sweep.py`: one new row in the existing table, an untracked ticket gives `; untracked: …` and exit 1, and one row where the issue list is bad JSON gives `didn't run: untracked` with the other parts' lines still printed. Existing rows pass an empty issue list.

## Acceptance

From the ticket:

- A state file without a ticket that is `agent`, `status:in-review` and has an open PR: the sweep prints a line naming it and exits 1. A ticket in `tickets`, in `merged`, or labelled `agent-skip` prints nothing.
- GitHub unreadable: the part prints `cos_untracked_check: <what>`, the other parts still run, and the last line ends `didn't run: untracked`.
- SKILL.md § Sweep, the take-over and resume text say what to do with the new lines.
- One table-driven test covers the rule, in the style of `test_cos_sweep.py`.

## Non-goals

- Syncing `state.json` between machines, or moving it into git or the tracker.
- Stopping two Chief of Staff threads on different machines from running at once.
- Changing what a rebuild does when the file is missing.
- Starting a fresh child for a ticket whose branch already exists (no child thread on this machine).
- Reading Linear or Jira from a script.

## Calls I made

- **No child thread on this machine means no adopt.** The ticket allows "blocked or started per the existing rules". State can't hold a ticket without a child (`start` needs `childThreadId`), and a fresh spec child would fail on `git switch -c` because the branch exists. So the Chief of Staff writes nothing and tells the user to work it from the owning machine, or cancel it there and send it back to Todo.
- **Linear and Jira apps only get the PR half.** Scripts can't read those trackers, so the script finds only tickets with an open PR there. A Linear ticket in progress with no PR yet (like CW-126 here) is missed. Covering it would mean a `list-tickets` call by the Chief of Staff each pass; left for a follow-up if it bites.
- **The reminder repeats on every report, not once.** The ticket says once per pass. The line shows in every report that posts and in `status`, but never makes a quiet run-finished turn post. There is no "ignore this one" memory; the user stops it by adopting the ticket or labelling it `agent-skip`.
- **`adopt N` is a new strict command**, checked like `approve N`, because it writes state and can claim another machine's ticket.
- **No author trust check in the script.** It prints only IDs, states and PR numbers, never ticket text, and the `agent` label needs triage access to set. The adapter's author check runs at `adopt N`, before anything is written.
- **One extra `gh` call pair per sweep.** The part makes its own `pr list` (number and branch only) and, on GitHub, one `issue list`, rather than sharing the ready check's PR fetch, so the parts stay independent like today.
- **Last line grows only when something is untracked**, so `sweep: read in full: none; merged: none` stays exactly as written in existing docs and tests.

# Continuation children for restarts, answers, resumes and rate-limit continues (design)

**Status:** Draft
**Ticket:** [CW-14](https://github.com/dbeallor/collective-wisdom/issues/14)

## Intent

After a Chief of Staff rotation, a child started by a retired thread reports its finish to nobody when the current thread wakes it with `t3_thread_send` (T3 posts a finish notice only to the run's starter). CW-11 fixed this for approvals and `changes N` by starting a continuation child under the current thread, and left the other four relays on the old child because that child may hold unpushed work. This change lets those four relays start a continuation child too, but only after a check proves the old child's worktree holds nothing a new worktree would lose. When the check can't prove that, the relay goes to the old child exactly as today.

## What is here today

Checked on `main` at 27fdaeb.

- `chief-of-staff` SKILL.md § Send or queue "Continuation child" starts a new child only for an approval or `changes N` on a ticket in `awaiting-spec` or `awaiting-merge`, and only when the ticket's `parentThreadId` is known and is not this thread.
- The paragraph after the template list says every other relay (resume, answer, rate-limit continue) and every ticket in `spec`, `build`, `merge` or `blocked` keeps its child.
- § Full pass step 3 sends the stuck-check restart to the child with `t3_thread_send` directly; it does not go through § Send or queue.
- `t3_thread_read` returns the child thread's `worktreePath`, set by T3. The Chief of Staff reads it but never uses it. The CW-11 spec says "the Chief of Staff can't see the old worktree"; it can, read only, through that path.
- `git worktree list` in the root checkout lists every T3 child worktree of the repo (checked: this worktree and the CW-11 one are listed).

## The four relay kinds

What could be lost is the same for all four: commits not on `origin/<branch>`, and uncommitted or untracked files in the old worktree. The old child's conversation is not lost in a way that matters: a continuation child gets the spec and plan from the branch and the `HANDOFF` block from state and GitHub.

| Kind | Where it is sent from | Old child at send time | Covered? |
|---|---|---|---|
| Restart (stuck check) | § Full pass step 3 | Its run finished without a marker, failed, or was just cancelled | Yes, when the worktree check passes |
| Answer to a blocked child (`the user answered`, how to proceed) | § Send or queue, from `blocked` | Run ended with `BLOCKED:` | Yes, when the worktree check passes |
| Answer to a pending request (`t3_pending_request`) | § Send or queue, from `blocked` | Run still open, waiting on the request | **No.** The run is not over, so its worktree can still change and the request would be left hanging. Stays with the old child. |
| `resume` (stopped by the user) | § Send or queue, from `blocked` | Cancelled | Yes, when the worktree check passes |
| Rate-limit continue | § Full pass step 4, through § Send or queue | Run ended with `BLOCKED: rate limited` or a run error | Yes, when the worktree check passes |

"Covered" holds per send, not per kind: the check runs every time, and a failed check sends to the old child as today. So a build child that stopped mid-task with uncommitted edits keeps its child, and one that pushed before it stopped moves.

## Design

### 1. `scripts/cos_worktree_check.py` (new)

```
python3 scripts/cos_worktree_check.py <PREFIX>-N <worktree path> [--file STATE] [--root DIR]
```

Read only. It answers one question: would a new worktree on `origin/<branch>` have everything the old worktree has?

1. Read the ticket's `branch` from state. It must match `<branch head><prefix lower>-<N>-[a-z0-9-]+` (the same pattern `cos_handoff.py` uses; share it, don't copy it).
2. The path must be one of the worktrees `git -C <root> worktree list --porcelain` prints, compared after resolving both. A path it doesn't list is never touched further.
3. `git -C <path> symbolic-ref --quiet --short HEAD` must print `branch`. Detached HEAD or another branch is unsafe.
4. `git --no-optional-locks -C <path> status --porcelain --untracked-files=all` must print nothing. Ignored files don't count.
5. `git -C <root> ls-remote origin refs/heads/<branch>` must print exactly the sha `git -C <path> rev-parse HEAD` prints. A missing remote branch, or a remote ahead of or behind local, is unsafe.

Output, one line, values printed only after they pass a pattern (branch, sha) or as fixed words:

```
safe CW-14 feat/cw-14-continuation-children <full sha>
unsafe CW-14: not a worktree of this repo
unsafe CW-14: on another branch
unsafe CW-14: detached HEAD
unsafe CW-14: uncommitted changes (3 files)
unsafe CW-14: not pushed (local 1a2b3c4, remote none)
unsafe CW-14: no branch in state
cos_worktree_check: <what>
```

Exit 0 safe, 1 unsafe, 2 could not run (bad ticket, no state file, no such ticket, git failed, `ls-remote` failed). It runs no command that writes: `--no-optional-locks` keeps `status` from refreshing the index, and it never fetches.

### 2. `chief-of-staff` SKILL.md

Only these sections change, so CW-17 (PR #26) and CW-12 can rebase around them:

- **Intro, Tools bullet (Bash list):** add `python3 scripts/cos_worktree_check.py` (the worktree check, § Send or queue).
- **§ Full pass step 3, the restart bullet:** one sentence. When the ticket's `parentThreadId` is known and is not this thread, the restart message is a relay for § Send or queue "Continuation child" in the ticket's current lane. It already holds its slot, so there is no slot check or queue. In a continuation the first line reads `the previous child's last run ended…` instead of `Your last run ended…`. `restarts[stage]` is set to 1 either way.
- **§ Send or queue "Continuation child":** split into the two cases.
  - *Approval or `changes N`* (today's rule, unchanged).
  - *Any other relay* (restart, answer, resume, rate-limit continue) to a ticket whose `parentThreadId` is known and is not this thread. Before the send:
    1. One `t3_thread_read` on the old child (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`) for `recentRuns[0].status` and `worktreePath`, and `t3_pending_request` `list` on it. A `running` run or a pending request: send to the old child as today.
    2. `python3 scripts/cos_worktree_check.py <PREFIX>-N <worktreePath>`. Exit 0: start a continuation child exactly as for an approval (`cos_handoff.py` first with its exit rules, then `delegate_task` on the lane's model, the relay as the task's last block, the same state writes). Exit 1 or 2: send to the old child as today and add one Cleanup line, `<PREFIX>-N kept its old child: <the script's line>`.
  - Report a move under Moving as today: `<PREFIX>-N moved to a new child (old one under a retired thread)`.
- **§ Send or queue, the "keeps its child" paragraph:** rewrite to say what still stays with the old child and why: a running child (can't be moved), a pending request (its run is open), and any child whose worktree check fails (unpushed or uncommitted work, or a worktree the check can't read). The sweep's parent check still full-reads those.
- **§ Send or queue, the paragraph on T3's notice rule:** keep the rule; say the finish of a run sent to an old child is now limited to the cases above.
- **§ Send or queue, the continuation template:** `Do the stage the relay names` becomes `Do the <stage> stage` (the lane's active stage), since a restart or a resume names no stage.

`ship-loop`, `merge-pr`, § Models, § Sweep, the scripts CW-11 added and the reference file don't change. A continuation task already says the branch is pushed, which the worktree check now proves for these kinds.

### 3. Tests

Per `AGENTS.md` § Testing, one table-driven test in `test_cos_worktree_check.py` over real git repos in `tmp_path` (a bare `origin`, a root clone, one added worktree on the ticket's branch, pushed). Each row changes one thing and expects the line and exit code:

- clean and pushed → `safe`, 0
- an untracked file; a modified tracked file → `uncommitted changes`, 1
- a local commit not pushed; branch never pushed → `not pushed`, 1
- another branch checked out; detached HEAD → 1
- a path that is a git repo but not a worktree of the root → `not a worktree of this repo`, 1
- an ignored file only → `safe`, 0
- a branch in state that fails the pattern; no such ticket → exit 1 and 2

No test for the skill prose.

## Leaves out

- Answers to a pending request (`t3_pending_request`). Recorded in the skill as not safe.
- Any change to the approval and `changes N` continuation, the sweep, the idle check, or T3's notice rule.
- Moving a child that belongs to the current thread. Its runs already report here.
- Stashes. The stash stack is shared by every worktree, so the check can't tell whose entry is whose. Work a child stashed and never committed can still be lost; that risk is the same today for a continuation after an approval.
- Cleaning up the old worktree. It stays, as with every continuation.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- `cos_worktree_check.py` run by hand from the root checkout against this ticket's worktree prints `safe` after a push and `unsafe … uncommitted changes` with a scratch file present, and leaves `git status` in that worktree unchanged.
- `test_root_links.py` and `test_symlinked_root.py` still pass with the new script reached through the root `scripts` link.

## Calls I made (surprising first)

- ⚠ All four kinds are covered, but per send, not always: a check of the old worktree decides each time. When it fails, the relay goes to the old child as today and the sweep still finds its finish. The ticket allowed "covered" or "not safe" per kind; a per-send check covers more runs than either.
- ⚠ The Chief of Staff gains a read-only look into a child's worktree (git `status`, `symbolic-ref`, `rev-parse`, and one `ls-remote` network read). It still never writes there. The path comes from T3's `worktreePath`, and the script refuses any path `git worktree list` in the root checkout doesn't name.
- ⚠ Answers to a pending request stay with the old child. Its run is open, so its worktree can still change and the request would be left hanging.
- A failed check falls back to today's send, not to `blocked`. Blocking would stop work that runs fine today just to fix a notice.
- Ignored files don't count as work; counting them would flag every worktree with a `__pycache__`. Stashes are not checked (§ Leaves out).
- A remote branch ahead of the local one counts as unsafe, though nothing would be lost. Proving "behind" needs a fetch, which writes; the rare case isn't worth it.
- The stuck-check restart reaches the continuation rule from § Full pass step 3 rather than becoming a § Send or queue caller. It keeps its slot, so a queue check would only get in the way.
- In a continuation the restart message says "the previous child's last run" so the new child doesn't look for a run it never had.
- The continuation template names the stage instead of relying on the relay text.
- The check reads the worktree, not the old child's thread, for unpushed work. A child's own report is data and can be wrong.

## Left to the builder

- Exact wording of the skill lines, within the sections named in § 2.
- Whether the shared branch pattern moves to `project_config.py` or stays in `cos_handoff.py` and is imported.
- Whether `install.sh` or `test_agent_files.py` lists scripts by name and needs the new one added.

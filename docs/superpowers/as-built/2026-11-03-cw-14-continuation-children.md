# As-built: Continuation children for restarts, answers, resumes and rate-limit continues

**Shipped:** in PR #33
**Ticket:** CW-14 (#14)
**Spec:** [2026-11-03-cw-14-continuation-children-design.md](../specs/2026-11-03-cw-14-continuation-children-design.md)
**Plan:** [2026-11-03-cw-14-continuation-children.md](../plans/2026-11-03-cw-14-continuation-children.md)

## What shipped

- `scripts/cos_worktree_check.py`: read only. Given a ticket and a worktree path it prints `safe <PREFIX>-N <branch> <sha>` or `unsafe <PREFIX>-N: <reason>`. Safe means the path is a worktree of the root checkout, HEAD is the ticket's branch, `status` is clean (ignored files don't count) and `origin/<branch>` is at the same sha. It never fetches and runs no git command that writes. Exit 0 safe, 1 unsafe, 2 could not run.
- `cos_handoff.py` exposes `branch_re()` so both scripts share the branch pattern.
- `chief-of-staff` SKILL.md: a restart, an answer to a blocked child, `resume` or a rate-limit continue to a child under another Chief of Staff thread starts a continuation child when the worktree check says `safe`. A running run, a pending request, a failed thread read or request call, or no `worktreePath` keeps the old child; so does exit 1 or 2 of the check, with a Cleanup line. Sections touched: Tools (Bash bullet), Full pass step 3 (restart bullet), Send or queue ("Continuation child", the "keeps its child" and T3 notice paragraphs, the template's stage line).
- `docs/agents/chief-of-staff.md` lists the new script.

## Differs from the spec

- Step 1 of the new rule also sends to the old child when the thread read or `t3_pending_request` call fails, or the read gives no `worktreePath`. The spec named only a running run and a pending request. Added after code review, so an unreadable old child is never replaced.
- The remote sha is matched on the exact ref `refs/heads/<branch>`, because `ls-remote` also lists decoy refs such as `refs/heads/a/refs/heads/<branch>`; no exact line means remote none. Every git call runs with `core.fsmonitor=false` and `core.hooksPath=/dev/null`. The worktree path is passed after `--`.

## Verification

- `python3 -I -m pytest -q agent-team/scripts`: 339 passed. `shellcheck install.sh agent-team/scripts/*.sh`: clean.
- Run by hand against the build worktree with scratch files present: `unsafe CW-14: uncommitted changes (3 files)`, and `git status` unchanged afterwards.

## Not verified

- No live Chief of Staff thread has started a continuation child through the new rule yet.

---
name: merge-pr
description: >-
  Squash-merges an approved PR after green CI; verifies closeout docs
  shipped in the PR, updates the ticket, fast-forwards the root checkout. Use only on
  a merge approval (the Chief of Staff's relay of the user's approval of this
  PR, or of an auto-approval; or, in a hand run, the user saying merge, merge
  it, or squash merge PR N after the `MERGE READY`); never agent-initiated.
user-invocable: true
---

# Merge PR

Read **ship-loop** § Repo invariants first.

## Gate

**Require a merge approval** per `ship-loop` § Approvals (the relay, or in a hand run the user's message after the `MERGE READY`). With none, stop and report merge-ready.

- The relay is its own proof: the Chief of Staff sends it only after `~/.collective-wisdom/scripts/cos_approve_pr.py` verified the user's `approve N` (`~/.collective-wisdom/docs/agents/github-auth.md` § Merge gate), or, for `CHIEF OF STAFF: auto-approved the merge of PR #X at head <short SHA>`, after `cos_approve_pr.py <PREFIX>-N --auto` passed. Read no thread.
- **Reference head.** The head you merge is the approved one: the relay's `at head <short SHA>`, or the `Head:` of your own `MERGE READY` in a hand run (none: `ship-loop/reference.md` § Running one phase by hand). In a continuation task use the relay's head, not the handoff block's, and `BLOCKED:` if it is missing or under 7 hex characters. Pass it to `merge_pr.py` as the approved head.
- **Head moved.** After a merge approval, any other head (target merged in, conflict fix, CI fix, anything) is `BLOCKED: head moved after approval`. No review state excuses it: no re-check, no merge on the old approval. Report `MERGE READY` again; the user approves again (`ship-loop` § Approvals).
  - **One exception, setting `off`.** The approval also covers a resolved head: one merge commit whose first parent is the approved head, the only PR commit after it, with its second parent on the merge target branch and the `resolving conflicts with <target>` note (`open-pr/reference.md` § Conflict resolution). `Review after conflict resolution` is read from `origin/<target>`. `merge_pr.py` enforces this; with `on`, or any other head, the rule above holds. A conflict-resolution run ends in a `merge-pr` run with the relay's head as the approved head.

**Require phases 3 and 4 complete** (`ship-loop` § Phase gates; in `ci` mode phase 3 only). No security **PASS**: **invoke security-review** first.

## Pre-merge checks

`~/.collective-wisdom/scripts/merge_pr.py` runs the whole gate (its docstring lists the checks) and stops with one line naming the cause: act on it, don't repeat the checks by hand. A PR that isn't mergeable or has red checks: **invoke open-pr** (feedback loop) first.

**Closeout in PR** (`open-pr` § Closeout docs, § Proof): when the script says one is missing, add it on the feature branch in the worktree (or the PR body), push, wait for green CI, rerun; never on the root checkout.

## Migration heads check

If `docs/agents/project.md` § Commands gives a command (not "none"), run `git merge origin/<target>`, then that command. More than one head: renumber this branch's migration after the current head, rerun the tests, push, wait for green.

## Merge (human identity)

Run the root checkout's copy from the root checkout, so the PR can't supply its own gate:

```bash
cd <root checkout> && python3 ~/.collective-wisdom/scripts/merge_pr.py <N> <approved head SHA> --next
```

Exit 0: do what its `next:` line says. Exit 1 (a gate failed, nothing changed) or 2 (a read or the merge call failed): fix the cause and rerun, or stop with `BLOCKED: <the script's last line>`. Never fall back to `gh pr merge`.

## Done when

The PR is merged with its closeout docs, the ticket is **Done**, the root checkout is fast-forwarded to `origin/<target>`, and the report names the worktree and ends with `MERGED #N`. Never touch what `docs/agents/project.md` § Repo invariants protects on the root checkout (data directories).

## Do not

- Merge without a merge approval, without both review **PASS**es (in `ci` mode: green checks and every bot thread resolved), or with red or pending required checks.
- Submit a GitHub review.
- Force-push the merge target branch, or commit closeout docs on the root checkout after merge.
- Write `RELEASE_NOTES.md` or the `release-notes` branch: only `merge_pr.py` does.

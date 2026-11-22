#!/usr/bin/env python3
"""The Chief of Staff checks that need no thread reads, in one command.

Usage:
    ~/.collective-wisdom/scripts/cos_sweep.py --thread ID [--file STATE] [--merged-prs FILE] [--open-prs FILE] [--refs FILE] [--review-prs FILE]
                            [--issues FILE] [--login LOGIN] [--verbose] [--next]

--thread is this thread's own ID, as for cos_parent_check.py. Runs, in one process:
    1. the merged check with --apply (writes a merged op for each merged PR),
    2. the ready check, on the state as step 1 left it, so a ticket that just merged is not ready,
    3. the parent check,
    4. the untracked check, on the state as step 1 left it: tickets in flight that state doesn't know,
    5. the review check, last, on the state as step 1 left it (tickets in awaiting-review; it needs no thread read).
Prints the lines that need action, then one last line. A line needs action when its first word is one
the Chief of Staff acts on: merged, mismatch and unreadable (merged check); ready, conflict and pushed (ready
check); full (parent check); untracked; approved, changes, moved, closed and unreadable (review check).
A part's summary and its other lines (`ok`, `idle`, `building`, `no-pr`, `writing`, `waiting`,
the ready check's `unreadable`) are left out, and so is a part that printed nothing needing action.
A part that cannot run prints its own failure line whatever the flags. --verbose prints each part's own
lines and summary, as before. The last line:
    sweep: read in full: ABC-3 (ready), ABC-7 (old-parent); merged: ABC-2 #14
    sweep: read in full: none; merged: none
    sweep: read in full: none; merged: none; untracked: ABC-5 #12, ABC-6; review: ABC-7 approved
A ticket is listed once, with every reason, when the ready check prints `ready`, `conflict` or `pushed` for it
or the parent check prints `full` for it. A part that cannot run prints its own
"cos_<name>: <what>" line, the others still run, and the last line ends "; didn't run: <parts>".
The `; untracked:` list shows only when the untracked check found something. The `; review:` tail appears only when the review check printed an approved, changes, moved or closed line.
Exit 0 when nothing is listed, merged, untracked or to act on in review, 1 when something is, 2 when any part didn't run.
--merged-prs, --open-prs, --refs, --review-prs and --issues read the parts' GitHub data from files (tests do).
--login stands in for the untracked check's `gh api user` call.
--next (without it the output is exactly the lines above): after each line the Chief of Staff acts on (the ACTION words above, per part) and
after the last line, print `next: <instruction>` from the table NEXT below. The `unreadable` line means one thing from the merged check and
another from the review check, so the table is keyed by part and word. The last line's `next:` covers the full reads, the report wording and the
slot reason, and, for each part named after `didn't run:`, the fallback and the Cleanup line. Lines --verbose adds (`ok`, `idle`, `building`,
`no-pr`, `writing`, `waiting`, the ready check's `unreadable`, each part's summary) and a failing part's own `cos_<name>: <what>` line have no `next:`
text: they ask for nothing (the last line carries the failed part's fallback).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_merged_check  # noqa: E402
import cos_parent_check  # noqa: E402
import cos_ready_check  # noqa: E402
import cos_review_check  # noqa: E402
import cos_untracked_check  # noqa: E402

ROOT = root()
ACTION = {  # the first words the Chief of Staff acts on, per part
    "merged": {"merged", "mismatch", "unreadable"},
    "ready": {"ready", "pushed", "conflict"},
    "parent": {"full"},
    "untracked": {"untracked"},
    "review": {"approved", "changes", "moved", "closed", "unreadable"},
}


def show(name, lines, verbose, nxt=False):
    keep = lines if verbose else [x for x in lines if x.split()[:1] and x.split()[0] in ACTION[name]]
    if nxt:  # a `next:` line follows each action line
        keep = [y for x in keep for y in (x, *([f"next: {NEXT[name, x.split()[0]](x.split())}"] if x.split()[:1] and x.split()[0] in ACTION[name] else []))]
    if keep or verbose:
        print("\n".join(keep))


# --next: the step for each action line, keyed by (part, first word), and the pieces of the last line's step.
def untracked_facts(w):
    """`in review, PR #132` from `untracked ABC-N in-review #132`; either part may be missing (then `in flight`)."""
    facts = [x.replace("-", " ") if not x.startswith("#") else f"PR {x}" for x in w[2:]]
    return ", ".join(facts) or "in flight"


READ_FULL = "Full-read this ticket's child (it is on the `read in full:` list; skip it if this turn already did), then SKILL.md § Child path."
NEXT = {
    ("merged", "merged"): lambda w: (
        f"{w[1]} has left the team, as for `MERGED #N`: readiness.md § Unblocked after a merge. Report it under Moving as `{w[1]}: <short title>, "
        f"merged ({w[2]}), found by the merged check` (a ticket out of state takes one `get-ticket` for its title, report-format.md § Report format). "
        f"The slot fill runs with `(merged {w[2]})` as the slot reason. Later child reads this turn skip it."
    ),
    ("merged", "mismatch"): lambda w: "Nothing is written. One Cleanup line.",
    ("merged", "unreadable"): lambda w: "Nothing is written. One Cleanup line.",
    ("ready", "ready"): lambda w: READ_FULL,
    ("ready", "pushed"): lambda w: READ_FULL,
    ("ready", "conflict"): lambda w: READ_FULL.removesuffix(".") + " (Conflict), then sweep.md § Conflict relay.",
    ("parent", "full"): lambda w: READ_FULL,
    ("untracked", "untracked"): lambda w: (
        "Nothing is read in full, written or started for it. After the other lines are handled, on Linear or Jira run `get-ticket` and drop the "
        "line when the ticket is labelled `agent-skip` or is not In Progress or In Review. For each remaining line run `t3_thread_list` "
        f"(`includeSubagents: true`, `titleContains: \"{w[1]}\"`) for a child thread on this machine (the title must contain `{w[1]}` not followed by "
        f"another digit), and give it one Needs you line: `{w[1]}: <short title> in flight but not in my state ({untracked_facts(w)}; child "
        "<link>|no child thread on this machine). Another machine's Chief of Staff may own it. Say adopt "
        f"{w[1]} to take it here.` The line goes in any report the turn posts; it never makes a quiet turn post, and the `get-ticket` and list calls "
        "are skipped when the turn posts nothing."
    ),
    **{("review", word): lambda w: "Act on it as review.md § Review check says for this line (no thread read)." for word in
       ("approved", "changes", "moved", "closed", "unreadable")},
}
LAST = (
    "A marker on a full read moves the ticket as for a notice, and approvals.md § Approval requests follows. No marker and the child still running: "
    "nothing changes. No marker and the child finished: the stuck check (SKILL.md § Child path). Report a ticket found this way under Moving as "
    "`<PREFIX>-N: <short title>, merge ready, found by the sweep` (or `build ready`); the slot fill runs with `(merge ready)` or `(build ready)` as "
    "the slot reason. The full read is the only thing that moves a ticket on the list."
)
FALLBACK = {  # a part that exited 2: what to fall back to
    "merged": "no fallback (the merge lane is not known clear, so don't call it clear)",
    "ready": "the idle check",
    "parent": "full-read every active child whose `parentThreadId` isn't this thread",
    "review": "no fallback (say the `awaiting-review` tickets were not checked)",
    "untracked": "no fallback (don't say every ticket in flight is known)",
}


def last_next(failed):
    text = LAST
    if failed:
        text += (
            " A part that didn't run: add one Cleanup line, `Sweep part didn't run: <its line>`, and fall back to what it covers: "
            + "; ".join(f"{p}: {FALLBACK[p]}" for p in failed)
            + ". Don't say or imply that nothing is waiting in the lanes that part covers."
        )
    return text


def part(name, fn):
    """fn's result, or None when the part could not run (it has printed why)."""
    try:
        return fn()
    except SystemExit:  # the parts' fail() prints its line and exits 2
        return None
    except Exception:
        print(f"cos_{name}_check: crashed")
        return None


def sweep(thread, state_file, merged_prs=None, open_prs=None, refs_file=None, review_prs=None, issues=None, login=None, verbose=False, nxt=False):
    """Print every part's lines and the last line; return the exit code."""
    listed, merged, untracked, to_act, failed = {}, [], [], [], []

    def list_ticket(tid, reason):
        listed.setdefault(tid, [])
        if reason not in listed[tid]:
            listed[tid].append(reason)

    got = part("merged", lambda: cos_merged_check.run(state_file, merged_prs, apply=True))
    if got is None:
        failed.append("merged")
    else:
        show("merged", got[0], verbose, nxt)
        merged = got[1]

    def ready():
        state = cos_ready_check.load_state(state_file)
        prs = cos_ready_check.load_prs(open_prs) if open_prs else None
        refs = cos_ready_check.load_refs(refs_file) if refs_file else None
        return cos_ready_check.check(state, prs, refs)

    got = part("ready", ready)
    if got is None:
        failed.append("ready")
    else:
        show("ready", got[0], verbose, nxt)
        for tid, reason in got[1]:
            list_ticket(tid, reason)

    got = part("parent", lambda: cos_parent_check.run(thread, state_file))
    if got is None:
        failed.append("parent")
    else:
        show("parent", got[0], verbose, nxt)
        for line in got[0]:
            words = line.split()
            if words[0] == "full":
                list_ticket(words[1], words[2])

    got = part("untracked", lambda: cos_untracked_check.run(state_file, open_prs, issues, login))
    if got is None:
        failed.append("untracked")
    else:
        show("untracked", got[0], verbose, nxt)
        untracked = got[1]

    def review():
        state = cos_review_check.load_state(state_file)
        return cos_review_check.check(state, cos_review_check.load_prs(review_prs) if review_prs else None)

    got = part("review", review)
    if got is None:
        failed.append("review")
    else:
        show("review", got[0], verbose, nxt)
        to_act = got[1]

    read = ", ".join(f"{t} ({', '.join(r)})" for t, r in listed.items()) or "none"
    done = ", ".join(f"{t} #{n}" for t, n in merged) or "none"
    last = f"sweep: read in full: {read}; merged: {done}"
    if untracked:
        last += "; untracked: " + ", ".join(f"{t} #{n}" if n else t for t, n in untracked)
    if to_act:
        last += "; review: " + ", ".join(f"{t} {word}" for t, word in to_act)
    if failed:
        last += f"; didn't run: {', '.join(failed)}"
    print(last)
    if nxt:
        print(f"next: {last_next(failed)}")
    return 2 if failed else int(bool(listed or merged or untracked or to_act))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merged, ready, parent, untracked and review checks in one command.")
    ap.add_argument("--thread", required=True)
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--merged-prs", type=Path)
    ap.add_argument("--open-prs", type=Path)
    ap.add_argument("--refs", type=Path)
    ap.add_argument("--review-prs", type=Path)
    ap.add_argument("--issues", type=Path)
    ap.add_argument("--login")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--next", dest="nxt", action="store_true")
    args = ap.parse_args(argv)
    return sweep(args.thread, args.file, args.merged_prs, args.open_prs, args.refs, args.review_prs, args.issues, args.login, args.verbose, args.nxt)


if __name__ == "__main__":
    sys.exit(main())

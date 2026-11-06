#!/usr/bin/env python3
"""The Chief of Staff checks that need no thread reads, in one command.

Usage:
    scripts/cos_sweep.py --thread ID [--file STATE] [--merged-prs FILE] [--open-prs FILE] [--refs FILE] [--review-prs FILE]
                            [--issues FILE] [--login LOGIN]

--thread is this thread's own ID, as for cos_parent_check.py. Runs, in one process:
    1. the merged check with --apply (writes a merged op for each merged PR),
    2. the ready check, on the state as step 1 left it, so a ticket that just merged is not ready,
    3. the parent check without its archive lines (archiving still runs cos_parent_check.py itself),
    4. the untracked check, on the state as step 1 left it: tickets in flight that state doesn't know,
    5. the review check, last, on the state as step 1 left it (tickets in awaiting-review; it needs no thread read).
Prints each part's own lines and summary, then one last line:
    sweep: read in full: ABC-3 (ready), ABC-7 (old-parent); merged: ABC-2 #14
    sweep: read in full: none; merged: none
    sweep: read in full: none; merged: none; untracked: ABC-5 #12, ABC-6; review: ABC-7 approved
A ticket is listed once, with every reason, when the ready check prints `ready` or `pushed` for it
or the parent check prints `full` for it. A part that cannot run prints its own
"cos_<name>: <what>" line, the others still run, and the last line ends "; didn't run: <parts>".
The `; untracked:` list shows only when the untracked check found something. The `; review:` tail appears only when the review check printed an approved, changes, moved or closed line.
Exit 0 when nothing is listed, merged, untracked or to act on in review, 1 when something is, 2 when any part didn't run.
--merged-prs, --open-prs, --refs and --review-prs and --issues read the parts' GitHub data from files (tests do).
--login stands in for the untracked check's `gh api user` call.
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


def part(name, fn):
    """fn's result, or None when the part could not run (it has printed why)."""
    try:
        return fn()
    except SystemExit:  # the parts' fail() prints its line and exits 2
        return None
    except Exception:
        print(f"cos_{name}_check: crashed")
        return None


def sweep(thread, state_file, merged_prs=None, open_prs=None, refs_file=None, review_prs=None, issues=None, login=None):
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
        print("\n".join(got[0]))
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
        print("\n".join(got[0]))
        for tid, reason in got[1]:
            list_ticket(tid, reason)

    got = part("parent", lambda: cos_parent_check.run(thread, state_file, archive=False))
    if got is None:
        failed.append("parent")
    else:
        print("\n".join(got[0]))
        for line in got[0]:
            words = line.split()
            if words[0] == "full":
                list_ticket(words[1], words[2])

    got = part("untracked", lambda: cos_untracked_check.run(state_file, open_prs, issues, login))
    if got is None:
        failed.append("untracked")
    else:
        print("\n".join(got[0]))
        untracked = got[1]

    def review():
        state = cos_review_check.load_state(state_file)
        return cos_review_check.check(state, cos_review_check.load_prs(review_prs) if review_prs else None)

    got = part("review", review)
    if got is None:
        failed.append("review")
    else:
        print("\n".join(got[0]))
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
    args = ap.parse_args(argv)
    return sweep(args.thread, args.file, args.merged_prs, args.open_prs, args.refs, args.review_prs, args.issues, args.login)


if __name__ == "__main__":
    sys.exit(main())

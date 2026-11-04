#!/usr/bin/env python3
"""The Chief of Staff checks that need no thread reads, in one command.

Usage:
    scripts/cos_sweep.py --thread ID [--file STATE] [--merged-prs FILE] [--open-prs FILE] [--refs FILE]

--thread is this thread's own ID, as for cos_parent_check.py. Runs, in one process:
    1. the merged check with --apply (writes a merged op for each merged PR),
    2. the ready check, on the state as step 1 left it, so a ticket that just merged is not ready,
    3. the parent check without its archive lines (archiving still runs cos_parent_check.py itself).
Prints each part's own lines and summary, then one last line:
    sweep: read in full: ABC-3 (ready), ABC-7 (old-parent); merged: ABC-2 #14
    sweep: read in full: none; merged: none
A ticket is listed once, with every reason, when the ready check prints `ready` or `pushed` for it
or the parent check prints `full` for it. A part that cannot run prints its own
"cos_<name>: <what>" line, the others still run, and the last line ends "; didn't run: <parts>".
Exit 0 when nothing is listed or merged, 1 when something is, 2 when any part didn't run.
--merged-prs, --open-prs and --refs read the parts' GitHub data from files (tests do).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_merged_check  # noqa: E402
import cos_parent_check  # noqa: E402
import cos_ready_check  # noqa: E402

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


def sweep(thread, state_file, merged_prs=None, open_prs=None, refs_file=None):
    """Print every part's lines and the last line; return the exit code."""
    listed, merged, failed = {}, [], []

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

    read = ", ".join(f"{t} ({', '.join(r)})" for t, r in listed.items()) or "none"
    done = ", ".join(f"{t} #{n}" for t, n in merged) or "none"
    last = f"sweep: read in full: {read}; merged: {done}"
    if failed:
        last += f"; didn't run: {', '.join(failed)}"
    print(last)
    return 2 if failed else int(bool(listed or merged))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merged, ready and parent checks in one command.")
    ap.add_argument("--thread", required=True)
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--merged-prs", type=Path)
    ap.add_argument("--open-prs", type=Path)
    ap.add_argument("--refs", type=Path)
    args = ap.parse_args(argv)
    return sweep(args.thread, args.file, args.merged_prs, args.open_prs, args.refs)


if __name__ == "__main__":
    sys.exit(main())
